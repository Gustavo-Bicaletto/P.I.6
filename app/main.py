from fastapi import FastAPI, File, UploadFile  # Corrigido: importa File e UploadFile
from app.nlp import spacy_doc, split_sections, parse_contacts, count_metrics
from app.extract import extract_text_from_pdf
from app.scoring import calculate_score
from app.feedback import generate_feedback

app = FastAPI(title="CV Reviewer (pt-BR)")

@app.get("/")
def read_root():
    return {"message": "CV Reviewer API is running!"}

@app.post("/evaluate")
async def evaluate(file: UploadFile = File(...)):
    """
    Endpoint para avaliar o currículo em formato PDF.
    Retorna uma nota (0 a 5) e sugestões de melhoria.
    """
    # Extrair texto do PDF
    text = extract_text_from_pdf(file)

    # Processamento de NLP
    doc = spacy_doc(text)
    sections = split_sections(doc)
    contacts = parse_contacts(doc)

    # Cálculo do score
    score_0_5, score_0_100 = calculate_score(sections)

    # Geração de feedback
    feedback = generate_feedback(sections, score_0_100)

    return {
        "score_0_5": score_0_5,
        "score_0_100": score_0_100,
        "breakdown": feedback['breakdown'],
        "suggestions": feedback['suggestions'],
    }