import streamlit as st
import pdfplumber
import re
from io import BytesIO
import zipfile
from huggingface_hub import InferenceClient

st.set_page_config(page_title="Renommage Final", page_icon="📄")

# Utilisation d'un modèle d'IA gratuit et public (Mistral)
# Pas besoin de configuration complexe de projet Google ici
client = InferenceClient("mistralai/Mistral-7B-Instruct-v0.3")

def get_info_ia(text):
    prompt = f"Extract from this invoice text: 1. Vendor name (short) 2. Invoice number. Answer ONLY in JSON: {{\"vendor\": \"...\", \"number\": \"...\"}}. Text: {text[:1500]}"
    try:
        response = client.text_generation(prompt, max_new_tokens=100)
        # Extraction du JSON
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            import json
            data = json.loads(match.group().replace("'", '"'))
            return data.get('vendor', 'INCONNU'), data.get('number', 'NUM')
    except:
        return None, None
    return "INCONNU", "NUM"

st.title("📂 Renommage de Factures (Version Stable)")

files = st.file_uploader("Déposez vos PDF", type="pdf", accept_multiple_files=True)

if files:
    final_files = {}
    for f in files:
        with st.spinner(f"Analyse de {f.name}..."):
            with pdfplumber.open(f) as pdf:
                txt = pdf.pages[0].extract_text() or ""
            
            # Si l'IA échoue, on utilise une méthode de secours par texte
            vendor, num = get_info_ia(txt)
            
            if not vendor or vendor == "INCONNU":
                # Secours : on prend la première ligne du texte si l'IA rate
                lines = [l for l in txt.split('\n') if len(l.strip()) > 2]
                vendor = lines[0][:15] if lines else "FOURNISSEUR"

            v = re.sub(r'[^\w]', '_', str(vendor)).upper().strip('_')
            n = re.sub(r'[^\w\-]', '_', str(num)).upper().strip('_')
            new_name = f"{v}_FAC_{n}.pdf"
            
            final_files[new_name] = f.getvalue()
            st.write(f"✅ {new_name}")

    if final_files:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, data in final_files.items():
                zf.writestr(name, data)
        st.download_button("📥 Télécharger ZIP", buf.getvalue(), "factures.zip")
