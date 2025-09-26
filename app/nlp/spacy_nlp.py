import spacy
from spacy.matcher import PhraseMatcher

# Carrega o modelo (precisa ter baixado: python -m spacy download pt_core_news_sm)
_nlp = spacy.load("pt_core_news_sm")

# --- Skills via PhraseMatcher (exemplo simples; ajuste a lista depois) ---
_SKILLS = ["python", "docker", "kubernetes", "aws", "pandas", "fastapi"]
_phrase = PhraseMatcher(_nlp.vocab, attr="LOWER")
_phrase.add("SKILL", [_nlp.make_doc(s) for s in _SKILLS])

# --- EntityRuler no spaCy v3: use o NOME do componente ---
# se já existir 'entity_ruler' (alguém adicionou antes), reusa; senão cria
if "entity_ruler" in _nlp.pipe_names:
    ruler = _nlp.get_pipe("entity_ruler")
else:
    # 'before="ner"' insere antes do reconhecedor de entidades
    ruler = _nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})

ruler.add_patterns([
    {"label": "CERT", "pattern": [{"LOWER": "az-900"}]},
    {"label": "CERT", "pattern": [{"LOWER": "dp-203"}]},
    {"label": "CERT", "pattern": [{"LOWER": "security+"}]},
])

def analyze(text: str) -> dict:
    """Analisa o texto e retorna features básicas para o scoring."""
    doc = _nlp(text or "")
    skills = sorted(set(doc[s:e].text.lower() for _, s, e in _phrase(doc)))
    certs  = [ent.text for ent in doc.ents if ent.label_ == "CERT"]
    dates  = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    lemmas = [t.lemma_.lower() for t in doc if not t.is_space]
    return {"tokens": len(doc), "skills": skills, "certs": certs, "dates": dates, "lemmas": lemmas}
