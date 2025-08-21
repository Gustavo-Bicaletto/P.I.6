# Este arquivo vai calcular a nota do currículo com base nas seções encontradas e na qualidade das mesmas.
def calculate_score(sections):
    """Calcula a pontuação do currículo de acordo com as seções e conteúdo"""

    score_0_100 = 0
    total_criterios = 5

    # Avaliar estrutura
    score_estrutura = sum(1 for section in sections.values() if section.strip()) / total_criterios * 100

    # Avaliar clareza e métricas
    score_clareza = 75  # Exemplo de fixo (podemos melhorar com mais análise)

    # Skills e experiência quantificadas
    score_skills = 80  # Exemplo de fixo (podemos melhorar com mais análise)

    score_0_100 = (score_estrutura + score_clareza + score_skills) / 3
    score_0_5 = round(score_0_100 / 20, 1)

    return score_0_5, score_0_100
