import streamlit as st
import pdfplumber
from google import genai
import json
import re
from io import BytesIO
import zipfile

st.set_page_config(page_title="Renommage IA", page_icon="🤖")

# --- INITIALISATION CLIENT ---
def get_ai_client():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ La clé 'GEMINI_API_KEY' est manquante dans les Secrets Streamlit.")
        return None
    try:
        # Utilisation de la nouvelle bibliothèque google-genai
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        return client
    except Exception as e:
        st.error(f"❌ Erreur d'initialisation : {e}")
        return None

client = get_ai_client()

def get_info_with_ai(text):
    if not client: return "ERREUR", "CONFIG"
    
    prompt = f"""
    Extrait de cette facture :
    1. Le nom du fournisseur (court, ex: COOLBLUE).
    2. Le numéro de facture.
    Réponds en JSON : {{"fournisseur": "NOM", "numero": "NUM"}}
    Texte : {text[:2000]}
    """
    
    try:
        # Nouvelle syntaxe pour Gemini 1.5 Flash
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        # Extraction du JSON
        json_txt = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(json_txt)
        return data.get('fournisseur', 'INCONNU'), data.get('numero', 'NUM')
    except Exception as e:
        return f"ERREUR_IA", str(e)[:15]

# --- INTERFACE ---
st.title("📄 Renommage Automatique")

if client:
    uploaded_files = st.file_uploader("Déposez les PDF", type="pdf", accept_multiple_files=True)

    if uploaded_files:
        final_files = {}
        for uploaded_file in uploaded_files:
            with st.spinner(f"Analyse de {uploaded_file.name}..."):
                with pdfplumber.open(uploaded_file) as pdf:
                    raw_text = pdf.pages[0].extract_text() or ""
                
                vendor, num = get_info_with_ai(raw_text)
                
                # Nettoyage nom de fichier
                v_clean = re.sub(r'[^\w]', '_', vendor).upper()
                n_clean = re.sub(r'[^\w\-]', '_', num).upper()
                new_name = f"{v_clean}_FAC_{n_clean}.pdf"
                
                # Doublons
                base = new_name.replace(".pdf", "")
                count = 1
                while new_name in final_files:
                    new_name = f"{base}_{count}.pdf"
                    count += 1
                
                final_files[new_name] = uploaded_file.getvalue()
                st.write(f"✅ {new_name}")

        if final_files:
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for name, data in final_files.items():
                    zf.writestr(name, data)
            st.download_button("📥 Télécharger le ZIP", zip_buf.getvalue(), "factures.zip")
else:
    st.warning("En attente de la configuration de la clé API dans les Secrets...")
