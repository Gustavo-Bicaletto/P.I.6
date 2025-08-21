# Este arquivo gera o feedback detalhado sobre o currículo, incluindo sugestões de melhoria.
def generate_feedback(sections, score_0_100):
    """Gera o feedback e sugestões para o currículo"""

    suggestions = []
    breakdown = {}

    # Feedback sobre a estrutura
    if not sections['experiencia']:
        suggestions.append("Adicione uma seção de Experiência Profissional.")
    if not sections['educacao']:
        suggestions.append("Adicione sua formação acadêmica.")

    # Avaliar métricas
    if score_0_100 < 60:
        suggestions.append("Tente adicionar métricas nos bullets de experiência (ex.: %, R$, tempo).")
    
    breakdown = {
        "estrutura": 80,  # Exemplo fixo
        "clareza": 70,    # Exemplo fixo
        "skills": 90,     # Exemplo fixo
    }

    return {"breakdown": breakdown, "suggestions": suggestions}
