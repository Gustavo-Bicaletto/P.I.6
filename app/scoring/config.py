#define as políticas do scoring

import os
from enum import Enum

RUBRIC_VERSION = os.getenv("RUBRIC_VERSION", "rubric-v1.0.0")

class Agent(str, Enum):
    EXPERIENCED = "experienced"
    NOEXP = "noexp"

CUTOFFS = {"ruim": 40.0, "regular": 50.0, "bom": 70.0}

WEIGHTS = {
    Agent.EXPERIENCED: {
        "skills": 0.30, "experience": 0.20, "impact": 0.15, "semantic": 0.10,
        "projects": 0.05, "certs": 0.08, "doc_quality": 0.08, "contact": 0.02, "context": 0.02
    },
    Agent.NOEXP: {
        "skills": 0.28, "projects": 0.20, "certs": 0.15, "semantic": 0.12,
        "doc_quality": 0.12, "experience": 0.06, "impact": 0.05, "contact": 0.01, "context": 0.01
    }
}
