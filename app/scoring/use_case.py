import re
from .config import Agent
from .engine import evaluate
from app.nlp.spacy_nlp import analyze
from .subscores import (
    score_skills, score_experience, score_projects, score_certs,
    score_impact, score_semantic, score_doc_quality, score_contact, score_context
)

CERT_MAP = {  # pontos simples por certificação (MVP)
    r"\bAWS\s*(CCP|Cloud Practitioner)\b": 0.3,
    r"\bAWS\s*(SAA|Solutions Architect Associate)\b": 0.5,
    r"\bAZ-900\b": 0.3, r"\bDP-203\b": 0.5, r"\bSecurity\+\b": 0.4
}

def extract_years_total(text: str) -> float:
    if not text: return 0.0
    yrs = 0.0
    # padrão “X anos”
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(anos|years)\b", text, flags=re.I):
        yrs = max(yrs, float(m.group(1)))
    # intervalos “2019-2023”
    for m in re.finditer(r"\b(19|20)\d{2}\s*[-–—]\s*((19|20)\d{2}|presente|atual|hoje)\b", text, flags=re.I):
        a = int(text[m.start():m.start()+4])
        b = None
        if m.group(2).isdigit(): b = int(m.group(2))
        else: b = 2025
        yrs = max(yrs, max(0, b - a))
    return min(yrs, 15.0)

def extract_seniority_align(text: str, agent: Agent) -> float:
    t = text.lower() if text else ""
    has_jr  = any(w in t for w in ["estagi", "trainee", "júnior", "junior"])
    has_pl  = "pleno" in t
    has_sr  = any(w in t for w in ["sênior", "senior", "sr"])
    if agent == Agent.NOEXP:
        return 1.0 if has_jr and not (has_pl or has_sr) else 0.6
    return 1.0 if (has_pl or has_sr) else (0.6 if has_jr else 0.7)

def extract_projects_hits(text: str) -> int:
    t = text.lower() if text else ""
    return sum(1 for k in ["github.com", "gitlab.com", "kaggle.com", "portfólio", "portfolio", "projeto"] if k in t)

def extract_cert_points(text: str) -> float:
    if not text: return 0.0
    pts = 0.0
    for pat, val in CERT_MAP.items():
        if re.search(pat, text, flags=re.I): pts += val
    return min(pts, 1.0)

def extract_metrics_hits(text: str) -> int:
    if not text: return 0
    hits = 0
    hits += len(re.findall(r"\b\d+(\.\d+)?\s*%\b", text))
    hits += len(re.findall(r"\b\d{2,}\s*(ms|req/s|usuarios|usuários|r\$|\$|k)\b", text, flags=re.I))
    return hits

def tokens_count(text: str) -> int:
    return len(text.split()) if text else 0

def sections_present_count(text: str) -> int:
    t = text.lower() if text else ""
    keys = ["experiência", "experiencia", "education", "formação", "formacao", "projetos", "projects", "skills", "habilidades"]
    return min(4, sum(1 for k in ["experiência|experiencia","formação|formacao|education","projetos|projects","skills|habilidades"] if re.search(k, t)))

def dup_rate_trigram(text: str) -> float:
    if not text: return 0.0
    toks = text.lower().split()
    if len(toks) < 10: return 0.0
    tri = [" ".join(toks[i:i+3]) for i in range(len(toks)-2)]
    total = len(tri)
    uniq = len(set(tri))
    return max(0.0, (total - uniq)/total)

def build_features_from_doc(doc: dict, has_experience: bool) -> dict:
    text = (doc.get("description_clean") or "").strip()
    sp = analyze(text)  # ← usa spaCy aqui

    skills = sorted(set((doc.get("skills") or []) + sp["skills"]))
    tokens = sp["tokens"]
    years  = extract_years_total(text)  # pode manter regex por enquanto

    return {
        "text": text,
        "skills": skills,
        "years_total": years,
        "seniority_align": extract_seniority_align(text, Agent.EXPERIENCED if has_experience else Agent.NOEXP),
        "project_hits": extract_projects_hits(text),
        "cert_points": max(extract_cert_points(text), 0.2 if sp["certs"] else 0.0),  # pequeno boost
        "metrics_hits": extract_metrics_hits(text),
        "tokens": tokens,
        "sections_present": sections_present_count(text),
        "dup_rate": dup_rate_trigram(text),
        "has_email": bool(doc.get("contact_email")),
        "has_phone": bool(doc.get("contact_phone")),
        "cosine": 0.0, "remote_align": 0.5, "comp_score": None,
        "career_progression": any(w in text.lower() for w in ["jr","júnior","junior"]) and any(w in text.lower() for w in ["pleno","sênior","senior"]),
    }

def build_subscores(features: dict, agent: Agent) -> dict:
    return {
        "skills":      score_skills(features.get("skills"), None, None, features.get("text","")),
        "experience":  score_experience(features.get("years_total",0), features.get("seniority_align",0)),
        "projects":    score_projects(features.get("project_hits",0)),
        "certs":       score_certs(features.get("cert_points",0)),
        "impact":      score_impact(features.get("metrics_hits",0)),
        "semantic":    score_semantic(features.get("cosine",0)),
        "doc_quality": score_doc_quality(features.get("tokens",0), features.get("sections_present",0), features.get("dup_rate",0)),
        "contact":     score_contact(features.get("has_email",False), features.get("has_phone",False)),
        "context":     score_context(features.get("remote_align",0), features.get("comp_score"))
    }

def evaluate_resume_from_doc(doc: dict, has_experience: bool) -> dict:
    agent = Agent.EXPERIENCED if has_experience else Agent.NOEXP
    feats = build_features_from_doc(doc, has_experience)
    subs  = build_subscores(feats, agent)
    result = evaluate(agent, subs)
    return { "features": feats, **result }
