import streamlit as st
import pdfplumber
import re
from io import BytesIO
import zipfile

def clean_vendor_name(text):
    """Nettoie le nom pour garder un format court et propre."""
    # Supprime les mentions légales courantes
    discards = r'\b(ASBL|SA|SPRL|NV|SARL|SAS|EURL|ASSOCIATION|SOCIETE|SERVICE|SECRÉTARIAT|SOCIAL)\b'
    text = re.sub(discards, '', text, flags=re.IGNORECASE)
    
    # Garde uniquement les caractères alphanumériques
    text = re.sub(r'[^\w\s]', '', text)
    
    # Prend les 2 ou 3 premiers mots max
    words = text.split()
    short_name = "_".join(words[:2]).upper()
    return short_name if short_name else "FOURNISSEUR"

def extract_invoice_data(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            # Extraction du texte de la page 1
            content = pdf.pages[0].extract_text() or ""
            
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # --- TROUVER LE NUMÉRO ---
        # On cherche un pattern de numéro après des mots clés
        num_pattern = r"(?:Facture|N°|Invoice|Nr|Ref)\s*[:\-\s]*([A-Z0-9\-_]{3,})"
        match_num = re.search(num_pattern, content, re.IGNORECASE)
        invoice_no = match_num.group(1).replace('/', '-') if match_num else "NUM"

        # --- TROUVER LE FOURNISSEUR ---
        # On cherche dans les 3 premières lignes, en ignorant les lignes qui contiennent 'Facture'
        vendor = "INCONNU"
        for line in lines[:5]:
            if not re.search(r'(Facture|Date|Page|Compte|TVA|N°)', line, re.IGNORECASE):
                vendor = clean_vendor_name(line)
                break
        
        return f"{vendor}_FAC_{invoice_no}.pdf"
    except Exception:
        return f"ERREUR_LECTURE_{pdf_file.name}"

# --- INTERFACE ---
st.set_page_config(page_title="Renommer Factures", page_icon="📄")
st.title("📂 Assistant Renommage Cinéma")

uploaded_files = st.file_uploader("Déposez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_files:
    final_files = {} # Pour gérer les doublons
    results = []

    for uploaded_file in uploaded_files:
        new_name = extract_invoice_data(uploaded_file)
        
        # Gestion des doublons de noms
        base_name = new_name.replace(".pdf", "")
        counter = 1
        temp_name = new_name
        while temp_name in final_files:
            temp_name = f"{base_name}_{counter}.pdf"
            counter += 1
        
        final_files[temp_name] = uploaded_file.getvalue()
        results.append((uploaded_file.name, temp_name))

    # Affichage des résultats
    st.write("### Aperçu du renommage :")
    for old, new in results:
        st.code(f"{old}  ➡️  {new}")

    # Bouton de téléchargement
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for name, data in final_files.items():
            zf.writestr(name, data)
    
    st.download_button(
        label="📥 Télécharger les fichiers renommés (.ZIP)",
        data=zip_buffer.getvalue(),
        file_name="factures_renommees.zip",
        mime="application/zip"
    )
