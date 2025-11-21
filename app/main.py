# app/main.py
import argparse
from datetime import datetime
from bson import ObjectId
from app.db.mongo import get_db
from app.scoring.config import RUBRIC_VERSION
from app.scoring.use_case import (
    evaluate_resume_from_doc,
    extract_years_total,  # usado para heurística de experiência no backfill
)
from app.scoring.hybrid_scorer import HybridScorer

# Inicializar scorer híbrido (ML + Rule-Based)
_hybrid_scorer = None

def get_hybrid_scorer():
    """Singleton para scorer híbrido"""
    global _hybrid_scorer
    if _hybrid_scorer is None:
        _hybrid_scorer = HybridScorer()
    return _hybrid_scorer

def cmd_evaluate_one(args):
    db = get_db()
    doc = db["dados_processados"].find_one({"_id": ObjectId(args.id)})
    if not doc:
        raise SystemExit("Documento não encontrado em resumAI.dados_processados.")

    # Usar sistema híbrido por padrão (a menos que --rule-based-only)
    use_hybrid = args.use_hybrid and not args.rule_based_only
    
    if use_hybrid:
        scorer = get_hybrid_scorer()
        res = scorer.score(doc)
        
        # Adaptar formato para compatibilidade
        agent = "experienced" if res['features'].get('is_experienced') else "noexp"
        eval_result = {
            "agent": agent,
            "features": res['features'],
            "scores": {
                "version": RUBRIC_VERSION,
                "by_block": res['rb_subscores'],
                "final": res['score'],
                "label": res['label'],
            },
            "explain": {
                "method": "hybrid",
                "components": res['components'],
                "ml_metadata": res['ml_metadata'],
                "description": res['explanation']
            }
        }
    else:
        # Sistema rule-based tradicional
        has_exp = bool(args.has_experience)
        rb_result = evaluate_resume_from_doc(doc, has_experience=has_exp)
        eval_result = {
            "agent": rb_result["agent"],
            "features": rb_result["features"],
            "scores": rb_result["scores"],
            "explain": rb_result["explain"]
        }

    # cache simples (evita duplicar mesma versão/agent/sem vaga)
    exists = db["evaluations"].find_one({
        "source_doc_id": doc["_id"],
        "agent": eval_result["agent"],
        "input.target_role": None,
        "input.job_id": None,
        "scores.version": RUBRIC_VERSION
    })
    if exists and not args.force:
        print(f"Já existe avaliação (cache). final={exists['scores']['final']} label={exists['scores']['label']}")
        return

    eval_doc = {
        "created_at": datetime.utcnow(),
        "source_doc_id": doc["_id"],
        "agent": eval_result["agent"],
        "input": {
            "has_experience": eval_result['features'].get('is_experienced', False),
            "target_role": None,
            "job_id": None,
            "scoring_method": "hybrid" if args.use_hybrid else "rule_based"
        },
        "extractions_snapshot": {
            "skills": eval_result["features"].get("skills", []),
            "tokens": eval_result["features"].get("tokens", 0),
            "years_total": eval_result["features"].get("years_total", 0),
            "sections": eval_result["features"].get("sections_present", 0),
        },
        "scores": eval_result["scores"],
        "explain": eval_result["explain"],
    }
    inserted_id = db["evaluations"].insert_one(eval_doc).inserted_id
    
    # Mostrar resultado detalhado
    if use_hybrid:
        print(f"OK - evaluation {inserted_id} (HÍBRIDO)")
        print(f"   Score final: {eval_result['scores']['final']:.1f}/100 ({eval_result['scores']['label']})")
        print(f"   • ML: {eval_result['explain']['components']['ml_score']:.1f} ({eval_result['explain']['components']['ml_label']}) × {eval_result['explain']['components']['ml_weight']}")
        print(f"   • RB: {eval_result['explain']['components']['rb_score']:.1f} ({eval_result['explain']['components']['rb_label']}) × {eval_result['explain']['components']['rb_weight']}")
        if eval_result['explain']['ml_metadata']['is_outlier']:
            print(f"   ⭐ Outlier excepcional detectado!")
    else:
        print(f"OK - evaluation {inserted_id} | final={eval_result['scores']['final']} | label={eval_result['scores']['label']}")

def cmd_backfill(args):
    db = get_db()
    cur = db["dados_processados"].find(
        {"resume_text_clean": {"$exists": True, "$ne": ""}},
        projection={"resume_text_clean": 1, "skills": 1, "years_experience": 1, "experiences": 1}
    ).limit(args.limit)

    inserted = 0
    use_hybrid = args.use_hybrid and not args.rule_based_only
    scorer = get_hybrid_scorer() if use_hybrid else None
    
    for doc in cur:
        if use_hybrid:
            # Sistema híbrido
            res = scorer.score(doc)
            agent = "experienced" if res['features'].get('is_experienced') else "noexp"
            eval_result = {
                "agent": agent,
                "features": res['features'],
                "scores": {
                    "version": RUBRIC_VERSION,
                    "by_block": res['rb_subscores'],
                    "final": res['score'],
                    "label": res['label'],
                },
                "explain": {
                    "method": "hybrid",
                    "components": res['components'],
                    "ml_metadata": res['ml_metadata'],
                    "description": res['explanation']
                }
            }
        else:
            # Sistema rule-based tradicional
            text = (doc.get("resume_text_clean") or "")
            has_exp = extract_years_total(text) >= 1.0 if args.agent == "auto" else (args.agent == "experienced")
            rb_result = evaluate_resume_from_doc(doc, has_experience=has_exp)
            eval_result = {
                "agent": rb_result["agent"],
                "features": rb_result["features"],
                "scores": rb_result["scores"],
                "explain": rb_result["explain"]
            }

        exists = db["evaluations"].find_one({
            "source_doc_id": doc["_id"],
            "agent": eval_result["agent"],
            "input.target_role": None,
            "input.job_id": None,
            "scores.version": RUBRIC_VERSION
        })
        if exists and not args.force:
            continue

        eval_doc = {
            "created_at": datetime.utcnow(),
            "source_doc_id": doc["_id"],
            "agent": eval_result["agent"],
            "input": {
                "has_experience": eval_result['features'].get('is_experienced', False),
                "target_role": None,
                "job_id": None,
                "scoring_method": "hybrid" if use_hybrid else "rule_based"
            },
            "extractions_snapshot": {
                "skills": eval_result["features"].get("skills", []),
                "tokens": eval_result["features"].get("tokens", 0),
                "years_total": eval_result["features"].get("years_total", 0),
                "sections": eval_result["features"].get("sections_present", 0),
            },
            "scores": eval_result["scores"],
            "explain": eval_result["explain"],
        }
        db["evaluations"].insert_one(eval_doc)
        inserted += 1
        
        if inserted % 100 == 0:
            print(f"Processados: {inserted}...")

    method = "híbrido (ML + Rule-Based)" if use_hybrid else "rule-based"
    print(f"Backfill concluído usando {method}. Inseridos: {inserted}")

def build_parser():
    ap = argparse.ArgumentParser(prog="resumAI", description="Runner de scoring/labels.")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p1 = sp.add_parser("evaluate-one", help="Avalia 1 documento por _id")
    p1.add_argument("--id", required=True, help="ObjectId em resumAI.dados_processados")
    p1.add_argument("--has-experience", action="store_true", help="Marque se tem experiência (apenas para rule-based)")
    p1.add_argument("--force", action="store_true", help="Ignora cache e regrava")
    p1.add_argument("--use-hybrid", action="store_true", default=True, 
                    help="Usa sistema híbrido (ML + Rule-Based). Padrão: True")
    p1.add_argument("--rule-based-only", action="store_true",
                    help="Usa apenas sistema rule-based tradicional")
    p1.set_defaults(func=cmd_evaluate_one)

    p2 = sp.add_parser("backfill", help="Gera avaliações em lote")
    p2.add_argument("--limit", type=int, default=1000)
    p2.add_argument("--agent", choices=["auto","experienced","noexp"], default="auto",
                    help="Apenas para rule-based. Ignorado se --use-hybrid")
    p2.add_argument("--force", action="store_true")
    p2.add_argument("--use-hybrid", action="store_true", default=True,
                    help="Usa sistema híbrido (ML + Rule-Based). Padrão: True")
    p2.add_argument("--rule-based-only", action="store_true",
                    help="Usa apenas sistema rule-based tradicional")
    p2.set_defaults(func=cmd_backfill)

    return ap

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
