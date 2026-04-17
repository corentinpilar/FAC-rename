import streamlit as st
import pdfplumber
import google.generativeai as genai
import json
import re
from io import BytesIO
import zipfile

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Renommage IA Factures", page_icon="🤖", layout="centered")

# --- INITIALISATION DE L'IA ---
def init_gemini():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Clé API manquante. Ajoutez GEMINI_API_KEY dans les Secrets de Streamlit.")
        return None
    
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"❌ Erreur de configuration IA : {e}")
        return None

model = init_gemini()

def get_info_with_ai(text, filename):
    """Demande à l'IA d'analyser le texte avec une consigne stricte."""
    if not text or len(text.strip()) < 10:
        return "DOCUMENT_ILLISIBLE", "NUM"

    prompt = f"""
    Tu es un assistant comptable expert. Analyse ce texte extrait d'un PDF (Nom original: {filename}).
    Trouve :
    1. Le nom du FOURNISSEUR (l'émetteur de la facture). Sois court (ex: 'COOLBLUE', 'AMAZON', 'UCM'). 
       Ignore le destinataire (le client).
    2. Le NUMÉRO de facture.
    
    Réponds UNIQUEMENT au format JSON strict :
    {{"fournisseur": "NOM", "numero": "NUMERO"}}
    
    Texte :
    {text[:3000]}
    """
    
    try:
        response = model.generate_content(prompt)
        # Nettoyage pour isoler le JSON si l'IA ajoute du texte inutile
        clean_response = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(clean_response)
        return data.get('fournisseur', 'INCONNU'), data.get('numero', 'NUM')
    except Exception as e:
        # En cas d'erreur, on affiche l'erreur technique pour debugger
        st.warning(f"Détail technique pour {filename}: {str(e)}")
        return "ERREUR_IA", "NUM"

# --- INTERFACE UTILISATEUR ---
st.title("📄 Renommage Intelligent")
st.markdown("### Nomenclature : `FOURNISSEUR_FAC_NUMERO.pdf`")

uploaded_files = st.file_uploader("Déposez vos factures PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_files and model:
    final_files = {}
    
    st.write("---")
    st.write("### ⚙️ Traitement en cours...")
    
    for uploaded_file in uploaded_files:
        with st.status(f"Analyse de {uploaded_file.name}...", expanded=False) as status:
            try:
                # 1. Extraction du texte
                with pdfplumber.open(uploaded_file) as pdf:
                    first_page_text = pdf.pages[0].extract_text() or ""
                
                # 2. Appel à l'IA
                vendor, num = get_info_with_ai(first_page_text, uploaded_file.name)
                
                # 3. Nettoyage du nom de fichier
                vendor_clean = re.sub(r'[^\w]', '_', vendor).strip('_').upper()
                num_clean = re.sub(r'[^\w\-]', '_', num).strip('_').upper()
                
                new_name = f"{vendor_clean}_FAC_{num_clean}.pdf"
                
                # Gestion des doublons
                base_name = new_name.replace(".pdf", "")
                counter = 1
                while new_name in final_files:
                    new_name = f"{base_name}_{counter}.pdf"
                    counter += 1
                
                final_files[new_name] = uploaded_file.getvalue()
                status.update(label=f"✅ {new_name}", state="complete")
                st.write(f"**Ancien nom:** {uploaded_file.name}  \n**Nouveau nom:** `{new_name}`")
                
            except Exception as e:
                status.update(label=f"❌ Erreur sur {uploaded_file.name}", state="error")
                st.error(e)

    if final_files:
        st.write("---")
        # Création du ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for name, data in final_files.items():
                zf.writestr(name, data)
        
        st.download_button(
            label="📥 Télécharger tous les fichiers (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name="factures_renommees.zip",
            mime="application/zip",
            use_container_width=True
        )
