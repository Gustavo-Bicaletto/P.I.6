# Este arquivo é responsável por extrair o texto do PDF usando a biblioteca pdfplumber
import pdfplumber

def extract_text_from_pdf(file):
    with pdfplumber.open(file.file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text