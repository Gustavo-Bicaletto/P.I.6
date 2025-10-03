# scoring/engine.py
from typing import Dict, Any
from .config import Agent, WEIGHTS, CUTOFFS, RUBRIC_VERSION

def combine(agent: Agent, subs: Dict[str, float]) -> float:
    w = WEIGHTS[agent]
    return round(100 * sum(w.get(k, 0)*subs.get(k, 0) for k in w), 1)

def label_from(score: float) -> str:
    if score < CUTOFFS["ruim"]: return "Ruim"
    if score < CUTOFFS["bom"]: return "Regular"
    return "Bom"

def explain_top(subs: Dict[str,float], agent: Agent, k=3):
    w = WEIGHTS[agent]
    contrib = {name: w.get(name,0)*val for name,val in subs.items()}
    up = sorted(contrib.items(), key=lambda x: x[1], reverse=True)[:k]
    down = sorted(contrib.items(), key=lambda x: x[1])[:k]
    return [n for n,_ in up], [n for n,_ in down]

def evaluate(agent: Agent, subscores: Dict[str,float]) -> Dict[str, Any]:
    final = combine(agent, subscores)
    top_up, top_down = explain_top(subscores, agent)
    return {
        "scores": {
            "version": RUBRIC_VERSION,
            "by_block": subscores,
            "final": final,
            "label": label_from(final)
        },
        "explain": { "top_up": top_up, "top_down": top_down },
        "agent": agent.value
    }
