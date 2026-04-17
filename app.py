import streamlit as st
import pdfplumber
import google.generativeai as genai
import json
import re
from io import BytesIO
import zipfile

st.set_page_config(page_title="Renommage Factures", page_icon="📄")

# --- CONNEXION ---
def init_ai():
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Clé API manquante dans les Secrets.")
        return None
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # On utilise le modèle Flash qui est le plus rapide et robuste
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Erreur d'initialisation : {e}")
        return None

model = init_ai()

def get_data_with_ai(text):
    if not model: return "CONFIG", "ERROR"
    
    prompt = (
        "Tu es un robot qui extrait des données. Analyse ce texte et réponds "
        "UNIQUEMENT avec un JSON : {'fournisseur': 'NOM_COURT', 'numero': 'NUMERO'}. "
        f"Texte : {text[:2500]}"
    )
    
    try:
        response = model.generate_content(prompt)
        # Nettoyage pour isoler le JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            # On s'assure que les guillemets sont corrects pour le JSON
            clean_json = match.group().replace("'", '"')
            data = json.loads(clean_json)
            return data.get('fournisseur', 'INCONNU'), data.get('numero', 'NUM')
        return "FORMAT", "ERROR"
    except Exception as e:
        # On affiche le code d'erreur dans le nom pour comprendre (ex: 403, 429)
        return "ERREUR_IA", str(e)[:10]

# --- INTERFACE ---
st.title("📂 Renommage de Factures")

if model:
    files = st.file_uploader("Déposez vos PDF", type="pdf", accept_multiple_files=True)

    if files:
        final_files = {}
        for f in files:
            with st.spinner(f"Analyse de {f.name}..."):
                try:
                    with pdfplumber.open(f) as pdf:
                        txt = pdf.pages[0].extract_text() or ""
                    
                    vendor, num = get_data_with_ai(txt)
                    
                    # Nettoyage strict des caractères
                    v = re.sub(r'[^\w]', '_', str(vendor)).upper().strip('_')
                    n = re.sub(r'[^\w\-]', '_', str(num)).upper().strip('_')
                    new_name = f"{v}_FAC_{n}.pdf"
                    
                    # Doublons
                    base = new_name.replace(".pdf", "")
                    count = 1
                    while new_name in final_files:
                        new_name = f"{base}_{count}.pdf"
                        count += 1
                        
                    final_files[new_name] = f.getvalue()
                    st.write(f"✅ {new_name}")
                except Exception as e:
                    st.error(f"Erreur : {e}")

        if final_files:
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                for name, data in final_files.items():
                    zf.writestr(name, data)
            st.download_button("📥 Télécharger ZIP", buf.getvalue(), "factures.zip")
