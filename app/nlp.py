# Este arquivo vai realizar o processamento de linguagem natural (NLP) utilizando o modelo spaCy pt-BR.
import spacy

# Carregar o modelo spaCy pt-BR
_nlp = spacy.load("pt_core_news_lg")

def spacy_doc(text):
    """Converte o texto para um objeto spaCy Document"""
    return _nlp(text)

def split_sections(doc):
    """Divide o currículo em seções principais (ex: experiência, educação, skills)"""
    sections = {"experiencia": "", "educacao": "", "skills": ""}
    for sent in doc.sents:
        if "experiência" in sent.text.lower():
            sections["experiencia"] += sent.text
        elif "educação" in sent.text.lower():
            sections["educacao"] += sent.text
        elif "skills" in sent.text.lower() or "habilidades" in sent.text.lower():
            sections["skills"] += sent.text
    return sections

def parse_contacts(doc):
    """Extrai informações de contato (email, telefone, etc.)"""
    contacts = {"email": "", "telefone": "", "linkedin": ""}
    for ent in doc.ents:
        if ent.label_ == "EMAIL":
            contacts["email"] = ent.text
        elif ent.label_ == "PHONE":
            contacts["telefone"] = ent.text
        elif "linkedin" in ent.text.lower():
            contacts["linkedin"] = ent.text
    return contacts

def count_metrics(sections):
    """Conta o número de métricas (ex.: R$, %, etc.) em cada seção do currículo."""
    metrics = {"experiencia": 0, "educacao": 0, "skills": 0}
    
    # Contar métricas em cada seção (por exemplo, números, porcentagens, R$)
    for section_name, section_text in sections.items():
        metrics_in_section = [word for word in section_text.split() if '%' in word or 'R$' in word]
        metrics[section_name] = len(metrics_in_section)
        
    return metrics
