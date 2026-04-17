import streamlit as st
import pdfplumber
import re
from io import BytesIO
import zipfile

def clean_text(text):
    """Nettoie le texte pour enlever les espaces superflus."""
    return " ".join(text.split())

def extract_invoice_data(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        # On extrait le texte des deux premières pages pour être sûr
        full_text = ""
        for page in pdf.pages[:2]:
            full_text += page.extract_text() + " "
    
    text = clean_text(full_text)

    # --- 1. EXTRACTION DU NUMÉRO (Priorité aux formats classiques) ---
    # On cherche "Facture n°", "N° de facture", "Invoice No", etc.
    no_patterns = [
        r"(?:Facture|Invoice|N°|Nr|Numéro)\s*[:\-\s]*([A-Z0-9\-_/]{4,})",
        r"(?:Référence|Ref)\s*[:\-\s]*([A-Z0-9\-_/]{4,})"
    ]
    
    invoice_no = "INCONNU"
    for pattern in no_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_no = match.group(1).replace('/', '-')
            break

    # --- 2. EXTRACTION DU FOURNISSEUR (Méthode plus fine) ---
    # On évite de prendre la première ligne si elle contient "Page" ou des dates
    lines = [l.strip() for l in full_text.split('\n') if len(l.strip()) > 2]
    
    vendor = "FOURNISSEUR"
    for line in lines[:5]: # On regarde les 5 premières lignes
        # On ignore les lignes qui ressemblent à des titres de documents ou dates
        if not re.search(r'(Facture|Date|Page|Note|TVA|SIRET|BCE)', line, re.IGNORECASE):
            vendor = line
            break
    
    # On tronque le nom du fournisseur pour qu'il soit court (ex: 15 caractères max)
    vendor = re.sub(r'[^\w\s]', '', vendor) # Enlève la ponctuation
    vendor = vendor.split()[0:3] # Prend les 3 premiers mots max
    vendor = "_".join(vendor).upper()[:20] # Limite à 20 caractères
    
    return f"{vendor}_FAC_{invoice_no}.pdf"

# --- L'INTERFACE RESTE LA MÊME ---
