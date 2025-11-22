import re
from .config import Agent
from .engine import evaluate
from app.nlp.spacy_nlp import analyze
from app.ml.predict import ResumeClassifier
from app.ml.semantic_similarity import compute_semantic_similarity
from .subscores import (
    score_skills, score_experience, score_projects, score_certs,
    score_impact, score_semantic, score_doc_quality, score_contact, score_context
)

# Classificador híbrido global (carregado uma vez)
_CLASSIFIER = None

def get_classifier() -> ResumeClassifier:
    """Retorna instância singleton do classificador híbrido."""
    global _CLASSIFIER
    if _CLASSIFIER is None:
        try:
            _CLASSIFIER = ResumeClassifier(
                model_path="models/resume_classifier/run-2025-11-18-balanced",
                use_hybrid=True,
                years_threshold=2.0,
                confidence_threshold=0.85
            )
            print("✅ Classificador híbrido carregado com sucesso")
        except Exception as e:
            print(f"⚠️  Erro ao carregar classificador: {e}")
            print("   Sistema continuará usando detecção baseada em regras")
            _CLASSIFIER = None
    return _CLASSIFIER

CERT_MAP = {  # pontos simples por certificação (MVP)
    r"\bAWS\s*(CCP|Cloud Practitioner)\b": 0.3,
    r"\bAWS\s*(SAA|Solutions Architect Associate)\b": 0.5,
    r"\bAZ-900\b": 0.3, r"\bDP-203\b": 0.5, r"\bSecurity\+\b": 0.4
}

def extract_years_total(text: str) -> float:
    """Extrai anos de experiência com suporte a padrões PT-BR e EN."""
    if not text: return 0.0
    yrs = 0.0
    
    # Padrão explícito: "X anos" ou "X years"
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(anos?|years?)\b", text, flags=re.I):
        yrs = max(yrs, float(m.group(1)))
    
    # Intervalos: "2019-2023", "2019 - 2023", "2019 – atual"
    for m in re.finditer(r"\b(19|20)\d{2}\s*[-–—]\s*((19|20)\d{2}|presente|atual|hoje|current|present)\b", text, flags=re.I):
        start_year = int(text[m.start():m.start()+4])
        end_text = m.group(2).lower()
        
        if end_text in ["presente", "atual", "hoje", "current", "present"]:
            end_year = 2025
        else:
            end_year = int(end_text[:4])
        
        years_diff = max(0, end_year - start_year)
        yrs = max(yrs, years_diff)
    
    # Padrões brasileiros: "desde 2019", "a partir de 2020"
    for m in re.finditer(r"\b(desde|a partir de|from)\s+(19|20)\d{2}\b", text, flags=re.I):
        year_match = re.search(r"(19|20)\d{2}", m.group())
        if year_match:
            start_year = int(year_match.group())
            years_diff = max(0, 2025 - start_year)
            yrs = max(yrs, years_diff)
    
    # Padrão de período: "jan/2020 a dez/2023", "03/2019 - 05/2022"
    for m in re.finditer(r"\b\d{1,2}/(\d{4})\s*[-–—a]\s*\d{1,2}/(\d{4})\b", text):
        start_year = int(m.group(1))
        end_year = int(m.group(2))
        years_diff = max(0, end_year - start_year)
        yrs = max(yrs, years_diff)
    
    return min(yrs, 20.0)  # Cap em 20 anos para evitar outliers

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
    """Detecção melhorada de métricas de impacto."""
    if not text: return 0
    hits = 0
    
    # Percentuais
    hits += len(re.findall(r"\b\d+(\.\d+)?\s*%\b", text))
    
    # Valores monetários com contexto
    hits += len(re.findall(r"(R\$|US\$|USD|\$)\s*\d+[\d,\.]*[kKmMbB]?", text, flags=re.I))
    
    # Números de impacto com contexto
    impact_patterns = [
        r"(reduzi[ur]|aumentou|melhorou|otimizou|economizou).*?\b\d+(\.\d+)?\s*%",
        r"\b\d+[kKmM]?\s*(usuários|users|clientes|customers|pessoas)",
        r"\b\d+\s*(requests?|req/s|ms|segundos?|minutos?)",
        r"(tempo|latência|performance|velocidade).*?\b\d+\s*%",
        r"(economia|redução|aumento|crescimento).*?(R\$|US\$|\$)\s*\d+",
        r"\b\d+x\s*(mais rápido|faster|maior|melhor)",
        r"(crescimento|growth).*?\b\d+(\.\d+)?\s*%",
    ]
    
    for pattern in impact_patterns:
        matches = re.findall(pattern, text, flags=re.I)
        hits += len(matches)
    
    return min(hits, 12)  # Cap para evitar inflação

def score_skills_with_depth(cv_skills: list, text: str, skill_weights: dict = None) -> float:
    """
    Score de skills ponderado por relevância e profundidade.
    
    Args:
        cv_skills: Lista de skills identificadas
        text: Texto do currículo
        skill_weights: Dict com peso de cada skill (opcional)
    
    Returns:
        Score normalizado (0.0 a 1.0)
    """
    if not cv_skills:
        return 0.0
    
    total_score = 0.0
    skill_weights = skill_weights or {}
    
    for skill in cv_skills:
        # Peso base da skill (padrão: 1.0)
        weight = skill_weights.get(skill.lower(), 1.0)
        
        # Bonus por mencionar anos de experiência com a skill
        years_match = re.search(
            rf"{re.escape(skill)}.*?(\d+)\s*(anos?|years?)",
            text,
            flags=re.I
        )
        years_bonus = 0.3 if years_match else 0.0
        
        # Bonus por contexto avançado
        skill_context = text[max(0, text.lower().find(skill.lower())-50):text.lower().find(skill.lower())+50]
        advanced_keywords = ["avançado", "expert", "especialista", "sênior", "senior", "proficiente"]
        context_bonus = 0.2 if any(kw in skill_context.lower() for kw in advanced_keywords) else 0.0
        
        skill_score = weight * (1.0 + years_bonus + context_bonus)
        total_score += skill_score
    
    # Normalizar por número ideal de skills (12)
    return min(total_score / 12.0, 1.0)

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

def extract_email(text: str) -> bool:
    """Detecta se há email no texto."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.search(email_pattern, text))

def extract_phone(text: str) -> bool:
    """Detecta se há telefone no texto (formatos brasileiros)."""
    phone_patterns = [
        r'\(\d{2}\)\s*\d{4,5}-?\d{4}',  # (11) 98765-4321 ou (11) 8765-4321
        r'\d{2}\s*\d{4,5}-?\d{4}',       # 11 98765-4321
        r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}', # +55 11 98765-4321
    ]
    return any(re.search(pattern, text) for pattern in phone_patterns)

def build_features_from_doc(doc: dict, has_experience: bool = None) -> dict:
    """
    Extrai features do documento. Se has_experience=None, usa classificador ML.
    
    Args:
        doc: Documento do currículo
        has_experience: True/False para forçar classificação, None para usar ML
    
    Returns:
        Dict com features extraídas + classificação de experiência
    """
    text = (doc.get("description_clean") or doc.get("resume_text_clean") or "").strip()
    sp = analyze(text)  # ← usa spaCy aqui

    skills = sorted(set((doc.get("skills") or []) + sp["skills"]))
    tokens = sp["tokens"]
    years  = doc.get("years_experience") or extract_years_total(text)
    
    # Extrair contatos
    has_email = extract_email(text)
    has_phone = extract_phone(text)
    
    # Classificação de experiência
    if has_experience is None:
        # Usar classificador híbrido ML
        classifier = get_classifier()
        if classifier:
            try:
                result = classifier.predict(
                    text=text,
                    years_experience=years,
                    return_details=True
                )
                has_experience = result["prediction"] == 1
                classification_info = {
                    "ml_used": True,
                    "method": result["method"],
                    "confidence": result["confidence"],
                    "reason": result.get("reason", "")
                }
            except Exception as e:
                print(f"⚠️  Erro na classificação ML: {e}")
                # Fallback: regra simples
                has_experience = years >= 2.0
                classification_info = {
                    "ml_used": False,
                    "method": "rule_fallback",
                    "confidence": 1.0,
                    "reason": f"ML error, using years >= 2.0"
                }
        else:
            # Fallback: regra simples se ML não disponível
            has_experience = years >= 2.0
            classification_info = {
                "ml_used": False,
                "method": "rule_only",
                "confidence": 1.0,
                "reason": "ML classifier not available"
            }
    else:
        # Classificação manual fornecida
        classification_info = {
            "ml_used": False,
            "method": "manual",
            "confidence": 1.0,
            "reason": "manually specified"
        }

    return {
        "text": text,
        "skills": skills,
        "years_total": years,
        "has_experience": has_experience,
        "classification": classification_info,
        "seniority_align": extract_seniority_align(text, Agent.EXPERIENCED if has_experience else Agent.NOEXP),
        "project_hits": sp.get("project_hits", 0),  # ✅ Usar detecção do spaCy
        "cert_points": max(extract_cert_points(text), 0.2 if sp["certs"] else 0.0),  # pequeno boost
        "metrics_hits": extract_metrics_hits(text),
        "tokens": tokens,
        "sections_present": sp.get("sections_count", 0),  # ✅ Usar detecção melhorada do spaCy
        "dup_rate": dup_rate_trigram(text),
        "has_email": sp.get("has_email", False),  # ✅ Usar detecção do spaCy
        "has_phone": sp.get("has_phone", False),  # ✅ Usar detecção do spaCy
        "cosine": compute_semantic_similarity(text, doc.get("job_description")),  # MODELO FINE-TUNED
        "remote_align": 0.5, 
        "comp_score": None,
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

def evaluate_resume_from_doc(doc: dict, has_experience: bool = None) -> dict:
    """
    Avalia currículo completo.
    
    Args:
        doc: Documento do currículo
        has_experience: True/False para forçar classificação, None para usar ML automático
    
    Returns:
        Dict com features, subscores, score final e explicação
    """
    feats = build_features_from_doc(doc, has_experience)
    
    # Usar classificação automática se disponível
    detected_experience = feats.get("has_experience", False)
    agent = Agent.EXPERIENCED if detected_experience else Agent.NOEXP
    
    subs  = build_subscores(feats, agent)
    result = evaluate(agent, subs)
    
    return { 
        "features": feats, 
        **result,
        "experience_classification": {
            "is_experienced": detected_experience,
            "agent_used": agent.value,
            **feats.get("classification", {})
        }
    }
