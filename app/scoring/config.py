#define as políticas do scoring

import os
from enum import Enum

RUBRIC_VERSION = os.getenv("RUBRIC_VERSION", "rubric-v1.0.0")

class Agent(str, Enum):
    EXPERIENCED = "experienced"
    NOEXP = "noexp"

# Cutoffs para 2 categorias: RUIM ou BOM
# Critérios ajustados por perfil (estagiário vs experiente)
CUTOFFS = {
    "noexp": 40.0,     # SEM EXPERIÊNCIA: >= 40 = BOM, < 40 = RUIM
    "experienced": 50.0  # COM EXPERIÊNCIA: >= 50 = BOM, < 50 = RUIM
}

# Pesos ajustados para AVALIAÇÃO DE QUALIDADE (sem vaga de emprego)
# Foco: completude, clareza, estrutura e experiência
WEIGHTS = {
    Agent.EXPERIENCED: {
        "skills": 0.25,       # Diversidade e profundidade técnica
        "experience": 0.25,   # Anos e relevância da experiência
        "doc_quality": 0.20,  # Estrutura, clareza, seções completas
        "impact": 0.12,       # Métricas e resultados quantificáveis
        "contact": 0.08,      # Email e telefone presentes
        "projects": 0.05,     # Projetos relevantes mencionados
        "certs": 0.05,        # Certificações e cursos
        "semantic": 0.00,     # Não usado (sem vaga)
        "context": 0.00       # Não usado (sem vaga)
    },
    Agent.NOEXP: {
        "skills": 0.22,       # Skills são importantes mesmo sem experiência
        "projects": 0.20,     # Projetos acadêmicos/pessoais ganham peso
        "doc_quality": 0.20,  # Estrutura e clareza muito importantes
        "certs": 0.15,        # Certificações compensam falta de exp
        "contact": 0.10,      # Informações de contato essenciais
        "experience": 0.08,   # Pouca experiência, mas conta
        "impact": 0.05,       # Qualquer métrica ajuda
        "semantic": 0.00,     # Não usado (sem vaga)
        "context": 0.00       # Não usado (sem vaga)
    }
}
