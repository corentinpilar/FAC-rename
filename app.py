import streamlit as st
import pdfplumber
import google.generativeai as genai
import json
import re
from io import BytesIO
import zipfile

# --- CONFIGURATION IA ---
# On récupère la clé depuis les "Secrets" de Streamlit
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("⚠️ La clé API Gemini n'est pas configurée dans les Secrets de Streamlit.")

def get_info_with_ai(text):
    """Demande à l'IA d'analyser le texte de la facture."""
    prompt = f"""
    Analyse ce texte de facture et extrait uniquement :
    1. Le nom du fournisseur (court, max 2 mots).
    2. Le numéro de la facture.
    
    Réponds UNIQUEMENT sous forme de JSON :
    {{"fournisseur": "NOM", "numero": "NUMERO"}}
    
    Texte de la facture :
    {text[:3000]}
    """
    try:
        response = model.generate_content(prompt)
        # On nettoie la réponse au cas où l'IA ajoute du texte autour du JSON
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        data = json.loads(json_match.group())
        return data.get('fournisseur', 'INCONNU'), data.get('numero', 'NUM')
    except:
        return "ERREUR_IA", "NUM"

# --- INTERFACE ---
st.set_page_config(page_title="Renommage IA", page_icon="🤖")
st.title("🤖 Renommage de Factures par IA")
st.info("L'intelligence artificielle analyse vos documents pour extraire le vendeur et le numéro.")

uploaded_files = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_files:
    final_files = {}
    
    for uploaded_file in uploaded_files:
        with st.spinner(f"Analyse de {uploaded_file.name}..."):
            with pdfplumber.open(uploaded_file) as pdf:
                full_text = pdf.pages[0].extract_text() or ""
            
            vendor, num = get_info_with_ai(full_text)
            
            # Nettoyage des caractères interdits pour Windows/Mac
            vendor = re.sub(r'[^\w]', '_', vendor).upper()
            num = re.sub(r'[^\w\-]', '_', num).upper()
            
            new_name = f"{vendor}_FAC_{num}.pdf"
            
            # Gestion des doublons
            base = new_name.replace(".pdf", "")
            idx = 1
            while new_name in final_files:
                new_name = f"{base}_{idx}.pdf"
                idx += 1
                
            final_files[new_name] = uploaded_file.getvalue()
            st.write(f"✅ {uploaded_file.name}  ➜  **{new_name}**")

    # Bouton de téléchargement
    if final_files:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for name, data in final_files.items():
                zf.writestr(name, data)
        
        st.download_button(
            label="📥 Télécharger tout en .ZIP",
            data=zip_buffer.getvalue(),
            file_name="factures_renommees_IA.zip",
            mime="application/zip"
        )
