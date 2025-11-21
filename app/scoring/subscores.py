#calcula o valor de cada subscore a partir das features extraídas

import re, numpy as np

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))

def score_skills(cv_skills, must=None, nice=None, text="", use_depth=True):
    cv = set(map(str.lower, cv_skills or []))
    m = set(map(str.lower, must or []))
    n = set(map(str.lower, nice or []))

    # Caso não exista vaga/role (must/nice vazios), usar fallback por quantidade de skills.
    if not m and not n:
        count_norm = min(len(cv)/12.0, 1.0)
        depth = 0.0
        
        if use_depth and text:
            # Bonus por mencionar anos com skills
            for s in cv:
                if re.search(rf"{re.escape(s)}.*\b(\d+)\s*(anos|years)\b", text, flags=re.I):
                    depth += 0.03
                
                # Bonus por contexto avançado
                skill_pos = text.lower().find(s.lower())
                if skill_pos >= 0:
                    skill_context = text[max(0, skill_pos-50):skill_pos+50]
                    if any(kw in skill_context.lower() for kw in ["avançado", "expert", "sênior", "senior"]):
                        depth += 0.02
        
        return clamp(count_norm + depth)

    hard = len(cv & m) / len(m) if m else 0.0
    soft = len(cv & n) / len(n) if n else 0.0
    depth = 0.0
    
    if use_depth and text:
        for s in cv & (m | n):
            if re.search(rf"{re.escape(s)}.*\b(\d+)\s*(anos|years)\b", text, flags=re.I):
                depth += 0.05
    
    return clamp(2*hard + soft + depth)

def score_experience(years_total: float, seniority_align: float):
    years_norm = min((years_total or 0)/10.0, 1.0)
    return clamp(0.6*years_norm + 0.4*(seniority_align or 0.0))

def score_projects(hits: int): return clamp((hits or 0)/3.0)
def score_certs(points: float): return clamp(points)
def score_impact(hits: int):   return clamp((hits or 0)/3.0)

def score_semantic(similarity: float):
    """
    Score de similaridade semântica usando modelo fine-tuned.
    
    Args:
        similarity: Score de similaridade do modelo (já normalizado 0-1)
    
    Returns:
        Score normalizado 0.0-1.0
    """
    # Modelo fine-tuned já retorna valores bem calibrados (0-1)
    # Não precisa mais do ajuste (cosine + 1)/2
    return clamp(similarity or 0.0)

def score_doc_quality(tokens: int, sections_present: int, dup_rate: float):
    center, scale = 950, 240
    len_curve = 1/(1+np.exp(-((tokens-center)/scale))) if tokens else 0.0
    return clamp(0.5*len_curve + 0.4*(sections_present/4.0) + 0.1*(1.0-(dup_rate or 0.0)))

def score_contact(has_email: bool, has_phone: bool):
    return clamp((0.6 if has_email else 0.0) + (0.4 if has_phone else 0.0))

def score_context(remote_align: float, comp_score: float | None = None):
    if comp_score is None: return clamp(remote_align or 0.0)
    return clamp(0.7*(remote_align or 0.0) + 0.3*comp_score)
