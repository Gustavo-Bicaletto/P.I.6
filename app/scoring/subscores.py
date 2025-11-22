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
    
    Não penaliza falta de experiência (estagiários/júniors).
    Foca na qualidade da descrição do que foi feito.
    """
    years = years_total or 0.0
    
    # Curva MUITO mais generosa para iniciantes
    # 0 anos = 50% base (não penaliza estagiários!)
    # 1-2 anos = 60-80%
    # 3+ anos = 90-100%
    if years == 0.0:
        years_norm = 0.5  # Score base para estagiários/sem experiência
    elif years < 1.0:
        years_norm = 0.5 + (years * 0.1)  # 0-1 ano = 50-60%
    elif years < 3.0:
        years_norm = 0.6 + ((years - 1.0) * 0.15)  # 1-3 anos = 60-90%
    else:
        years_norm = min(0.9 + ((years - 3.0) * 0.02), 1.0)  # 3+ anos = 90-100%
    
    # Seniority_align mede qualidade da descrição (projetos acadêmicos, estágios, etc.)
    quality = seniority_align or 0.0
    
    # Para quem tem 0 anos, qualidade da descrição pesa mais (projetos acadêmicos)
    if years == 0.0:
        return clamp(0.4*years_norm + 0.6*quality)  # Foca na qualidade
    else:
        return clamp(0.7*years_norm + 0.3*quality)

def score_projects(hits: int):
    """Score de projetos mencionados.
    
    0 projetos = 40% base (não penaliza tanto)
    1 projeto = 60%
    2 projetos = 80%
    3+ projetos = 100%
    """
    if hits == 0:
        return 0.4  # Score base - não ter projetos explícitos não é crítico
    return clamp(0.4 + (hits / 3.0) * 0.6)  # 1-3 projetos = 60-100%

def score_certs(points: float):
    """Score de certificações.
    
    0 certs = 30% base (não obrigatório para júnior)
    """
    if points == 0:
        return 0.3  # Score base - certificações não são obrigatórias
    return clamp(0.3 + points * 0.7)  # Certificações são bonus

def score_impact(hits: int):
    """Score de métricas e resultados quantificáveis.
    
    Métricas NÃO são obrigatórias para júnior/estagiário.
    0 métricas = 60% base (ok não ter)
    1+ métrica = bonus
    """
    if hits == 0:
        return 0.6  # Score base - métricas são desejáveis mas não obrigatórias
    return clamp(0.6 + (hits / 5.0) * 0.4)  # Cada métrica adiciona até 40%

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
