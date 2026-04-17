import streamlit as st
import pdfplumber
import re
from io import BytesIO
import zipfile

def extract_smart_vendor(page):
    """
    Explore le coin supérieur gauche du PDF pour isoler le fournisseur.
    """
    # On définit une zone de recherche (en points PDF)
    # x0, y0 (haut gauche) -> x1, y1 (bas droite)
    # On prend les 30% du haut de la page
    width = page.width
    height = page.height
    
    # Zone probable du fournisseur (Haut Gauche)
    bbox = (0, 0, width * 0.5, height * 0.25) 
    crop = page.within_bbox(bbox)
    text = crop.extract_text()
    
    if not text:
        # Si rien à gauche, on tente le haut centré/droit
        bbox = (0, 0, width, height * 0.15)
        crop = page.within_bbox(bbox)
        text = crop.extract_text()

    if text:
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 2]
        for line in lines:
            # On ignore les mots purement techniques
            if not re.search(r'(Facture|Invoice|Date|N°|TVA|SIRET|Page)', line, re.IGNORECASE):
                # Nettoyage : on garde les 2-3 premiers mots
                clean = re.sub(r'[^\w\s]', '', line)
                return "_".join(clean.split()[:3]).upper()
    return "FOURNISSEUR"

def extract_invoice_no(full_text):
    """Recherche plus agressive du numéro de facture."""
    patterns = [
        r"(?:Facture|Invoice|N°|Nr|Ref|Doc)\s*[:\-\s]*([A-Z0-9\-_/]{4,})",
        r"(?:n°)\s*([A-Z0-9\-_/]{4,})"
    ]
    for p in patterns:
        m = re.search(p, full_text, re.IGNORECASE)
        if m:
            return m.group(1).replace('/', '-').strip()
    return "NUM"

def process_pdf(pdf_file):
    try:
        with pdfplumber.open(pdf_file) as pdf:
            first_page = pdf.pages[0]
            full_text = first_page.extract_text() or ""
            
            vendor = extract_smart_vendor(first_page)
            inv_num = extract_invoice_no(full_text)
            
            return f"{vendor}_FAC_{inv_num}.pdf"
    except:
        return f"ERREUR_{pdf_file.name}"

# --- Interface Streamlit ---
st.title("📂 Renommage Précis (Zone En-tête)")

files = st.file_uploader("Factures PDF", type="pdf", accept_multiple_files=True)

if files:
    final_results = {}
    st.write("### Aperçu des noms générés :")
    
    for f in files:
        new_name = process_pdf(f)
        
        # Gestion doublons
        base = new_name.replace(".pdf", "")
        count = 1
        while new_name in final_results:
            new_name = f"{base}_{count}.pdf"
            count += 1
            
        final_results[new_name] = f.getvalue()
        st.code(f"{f.name} -> {new_name}")

    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for name, data in final_results.items():
            zf.writestr(name, data)

    st.download_button("📥 Télécharger ZIP", zip_buf.getvalue(), "factures.zip")
