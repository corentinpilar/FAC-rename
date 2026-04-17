import streamlit as st
import pdfplumber
import re
import os
from io import BytesIO
import zipfile

def extract_invoice_data(pdf_file):
    """
    Extrait les informations clés du PDF.
    À adapter selon la structure de vos factures.
    """
    with pdfplumber.open(pdf_file) as pdf:
        # On extrait le texte de la première page
        first_page_text = pdf.pages[0].extract_text()
        
    # --- LOGIQUE D'EXTRACTION (Exemples de Regex) ---
    # Ces patterns sont à ajuster selon vos fournisseurs réels
    
    # 1. Recherche du numéro de facture (souvent après "Facture n°" ou "N° ")
    invoice_no_match = re.search(r"(?:Facture|N°)\s*[:\-\s]*([A-Z0-9\-_]+)", first_page_text, re.IGNORECASE)
    invoice_no = invoice_no_match.group(1) if invoice_no_match else "INCONNU"

    # 2. Recherche du fournisseur (souvent la première ligne ou un mot clé spécifique)
    # Ici, on prend arbitrairement la première ligne de texte non vide
    lines = [l.strip() for l in first_page_text.split('\n') if l.strip()]
    vendor = lines[0] if lines else "FOURNISSEUR"

    # Nettoyage des caractères spéciaux pour le nom de fichier
    vendor = re.sub(r'[^\w\s-]', '', vendor).replace(' ', '_').upper()
    
    return f"{vendor}_FAC_{invoice_no}.pdf"

# --- INTERFACE STREAMLIT ---
st.title("📂 Assistant Renommage Factures")
st.write("Glissez vos PDF ici pour les renommer selon la nomenclature : **NOM_FAC_NUMERO.pdf**")

uploaded_files = st.file_uploader("Choisir des fichiers PDF", type="pdf", accept_multiple_files=True)

if uploaded_files:
    processed_files = []
    
    with st.status("Analyse des fichiers...") as status:
        for uploaded_file in uploaded_files:
            try:
                new_name = extract_invoice_data(uploaded_file)
                processed_files.append((new_name, uploaded_file.getvalue()))
            except Exception as e:
                st.error(f"Erreur sur {uploaded_file.name}: {e}")
        status.update(label="Analyse terminée !", state="complete")

    if processed_files:
        st.success(f"{len(processed_files)} fichiers prêts.")
        
        # Création du fichier ZIP en mémoire
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for new_name, data in processed_files:
                zf.writestr(new_name, data)
        
        st.download_button(
            label="📥 Télécharger tout en .ZIP",
            data=zip_buffer.getvalue(),
            file_name="factures_renommees.zip",
            mime="application/zip"
        )
