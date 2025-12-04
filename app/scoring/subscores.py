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
    """Score de experiência focado em qualidade (não em match com vaga).
    
    Diferencia claramente júniors de experientes através dos anos de experiência.
    """
    years = years_total or 0.0
    
    # Curva mais realista com maior diferenciação
    # 0 anos = 20% base (júnior/estagiário sem experiência)
    # 1 ano = 40%
    # 2 anos = 60%
    # 3 anos = 75%
    # 5+ anos = 90-100%
    if years == 0.0:
        years_norm = 0.20  # Base baixo para forçar diferenciação
    elif years < 1.0:
        years_norm = 0.20 + (years * 0.20)  # 0-1 ano = 20-40%
    elif years < 2.0:
        years_norm = 0.40 + ((years - 1.0) * 0.20)  # 1-2 anos = 40-60%
    elif years < 3.0:
        years_norm = 0.60 + ((years - 2.0) * 0.15)  # 2-3 anos = 60-75%
    elif years < 5.0:
        years_norm = 0.75 + ((years - 3.0) * 0.075)  # 3-5 anos = 75-90%
    else:
        years_norm = min(0.90 + ((years - 5.0) * 0.02), 1.0)  # 5+ anos = 90-100%
    
    # Seniority_align mede qualidade da descrição
    quality = seniority_align or 0.0
    
    # Balancear anos + qualidade
    return clamp(0.75*years_norm + 0.25*quality)

def score_projects(hits: int):
    """Score de projetos mencionados.
    
    0 projetos = 10% (penaliza falta de projetos)
    1 projeto = 50%
    2 projetos = 75%
    3+ projetos = 100%
    """
    if hits == 0:
        return 0.10  # Penalizar falta de projetos
    elif hits == 1:
        return 0.50
    elif hits == 2:
        return 0.75
    else:
        return min(0.75 + (hits - 2) * 0.10, 1.0)

def score_certs(points: float):
    """Score de certificações.
    
    0 certs = 0% (sem certificações)
    1 cert (0.2 points) = 30%
    3 certs (0.6 points) = 70%
    5+ certs (1.0 points) = 100%
    """
    if points == 0:
        return 0.0  # Sem certificações = 0%
    return clamp(points * 1.0)  # Escala linear: 0.2 = 20%, 1.0 = 100%

def score_impact(hits: int):
    """Score de métricas e resultados quantificáveis.
    
    0 métricas = 20% (falta de quantificação)
    1 métrica = 50%
    2 métricas = 75%
    3+ métricas = 100%
    """
    if hits == 0:
        return 0.20  # Penalizar falta de métricas
    elif hits == 1:
        return 0.50
    elif hits == 2:
        return 0.75
    else:
        return min(0.75 + (hits - 2) * 0.10, 1.0)

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
    """Avalia qualidade do documento: tamanho, estrutura e clareza."""
    # Curva ajustada: 500-1500 tokens é o ideal
    if tokens < 300:
        len_score = tokens / 300.0  # Muito curto penaliza
    elif tokens <= 1500:
        len_score = 1.0  # Range ideal
    else:
        len_score = max(0.7, 1.0 - (tokens - 1500) / 3000.0)  # Muito longo penaliza levemente
    
    # Seções importantes: esperamos pelo menos 5-6 (contato, resumo, experiência, formação, skills, projetos)
    structure_score = min(sections_present / 6.0, 1.0)
    
    # Clareza (sem duplicações excessivas)
    clarity_score = 1.0 - (dup_rate or 0.0)
    
    return clamp(0.4*len_score + 0.4*structure_score + 0.2*clarity_score)

def score_contact(has_email: bool, has_phone: bool):
    return clamp((0.6 if has_email else 0.0) + (0.4 if has_phone else 0.0))

def score_context(remote_align: float, comp_score: float | None = None):
    if comp_score is None: return clamp(remote_align or 0.0)
    return clamp(0.7*(remote_align or 0.0) + 0.3*comp_score)
