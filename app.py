import streamlit as st
import pdfplumber
from google import genai
import json
import re
from io import BytesIO
import zipfile

# Configuration de l'interface
st.set_page_config(page_title="Renommer Factures IA", page_icon="🤖")

# --- CONNEXION À L'IA ---
def get_ai_client():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Clé 'GEMINI_API_KEY' manquante dans les Secrets de Streamlit.")
        return None
    try:
        # Initialisation avec la nouvelle méthode
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"❌ Erreur de connexion : {e}")
        return None

client = get_ai_client()

def get_info_with_ai(text):
    if not client: return "ERREUR", "CONFIG"
    
    # Consigne ultra-simple pour l'IA
    prompt = (
        "Analyse ce texte de facture. Donne-moi le nom du fournisseur (court) "
        "et le numéro de facture au format JSON : {'fournisseur': '...', 'numero': '...'}. "
        f"Texte : {text[:2500]}"
    )
    
    try:
        # Utilisation du nom de modèle complet pour éviter l'erreur 404
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt
        )
        
        # On extrait le JSON de la réponse
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            # On remplace les apostrophes simples par des doubles pour le formatage JSON
            clean_json = json_match.group().replace("'", '"')
            data = json.loads(clean_json)
            return data.get('fournisseur', 'INCONNU'), data.get('numero', 'NUM')
        return "FORMAT_IA", "ERREUR"
    except Exception as e:
        # On renvoie l'erreur pour la voir dans le nom du fichier si ça rate
        return "ERREUR_IA", str(e)[:10]

# --- INTERFACE UTILISATEUR ---
st.title("📄 Renommage de Factures par IA")
st.write("Glissez vos PDF pour les renommer automatiquement au format : **FOURNISSEUR_FAC_NUMERO.pdf**")

if client:
    uploaded_files = st.file_uploader("Choisir les fichiers PDF", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        final_files = {}
        st.write("### ⚙️ Analyse en cours...")
        
        for uploaded_file in uploaded_files:
            try:
                with pdfplumber.open(uploaded_file) as pdf:
                    # On prend le texte de la première page
                    raw_text = pdf.pages[0].extract_text() or ""
                
                vendor, num = get_info_with_ai(raw_text)
                
                # Nettoyage pour les noms de fichiers (pas d'espaces ni caractères spéciaux)
                v_clean = re.sub(r'[^\w]', '_', str(vendor)).upper().strip('_')
                n_clean = re.sub(r'[^\w\-]', '_', str(num)).upper().strip('_')
                
                new_name = f"{v_clean}_FAC_{n_clean}.pdf"
                
                # Gestion des doublons
                base = new_name.replace(".pdf", "")
                count = 1
                while new_name in final_files:
                    new_name = f"{base}_{count}.pdf"
                    count += 1
                
                final_files[new_name] = uploaded_file.getvalue()
                st.write(f"✅ `{new_name}`")
                
            except Exception as e:
                st.error(f"Erreur sur {uploaded_file.name} : {e}")

        # Si on a des fichiers prêts, on propose le téléchargement
        if final_files:
            st.write("---")
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for name, data in final_files.items():
                    zf.writestr(name, data)
            
            st.download_button(
                label="📥 Télécharger tous les fichiers (.ZIP)",
                data=zip_buf.getvalue(),
                file_name="factures_renommees.zip",
                mime="application/zip",
                use_container_width=True
            )
else:
    st.info("Veuillez configurer votre clé API dans les réglages de Streamlit Cloud.")
