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

def cmd_evaluate_one(args):
    db = get_db()
    doc = db["dados_processados"].find_one({"_id": ObjectId(args.id)})
    if not doc:
        raise SystemExit("Documento não encontrado em resumAI.dados_processados.")

    has_exp = bool(args.has_experience)
    res = evaluate_resume_from_doc(doc, has_experience=has_exp)

    # cache simples (evita duplicar mesma versão/agent/sem vaga)
    exists = db["evaluations"].find_one({
        "source_doc_id": doc["_id"],
        "agent": res["agent"],
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
        "agent": res["agent"],
        "input": {"has_experience": has_exp, "target_role": None, "job_id": None},
        "extractions_snapshot": {
            "skills": res["features"]["skills"],
            "tokens": res["features"]["tokens"],
            "years_total": res["features"]["years_total"],
            "sections": res["features"]["sections_present"],
        },
        "scores": {
            "version": RUBRIC_VERSION,
            "by_block": res["scores"]["by_block"],
            "final": res["scores"]["final"],
            "label": res["scores"]["label"],
        },
        "explain": res["explain"],
    }
    inserted_id = db["evaluations"].insert_one(eval_doc).inserted_id
    print(f"OK - evaluation {inserted_id} | final={res['scores']['final']} | label={res['scores']['label']}")

def cmd_backfill(args):
    db = get_db()
    cur = db["dados_processados"].find(
        {"description_clean": {"$exists": True, "$ne": ""}},
        projection={"description_clean": 1, "skills": 1, "contact_email": 1, "contact_phone": 1}
    ).limit(args.limit)

    inserted = 0
    for doc in cur:
        text = (doc.get("description_clean") or "")
        # heurística simples: >=1 ano => experienced
        has_exp = extract_years_total(text) >= 1.0 if args.agent == "auto" else (args.agent == "experienced")
        res = evaluate_resume_from_doc(doc, has_experience=has_exp)

        exists = db["evaluations"].find_one({
            "source_doc_id": doc["_id"],
            "agent": res["agent"],
            "input.target_role": None,
            "input.job_id": None,
            "scores.version": RUBRIC_VERSION
        })
        if exists and not args.force:
            continue

        eval_doc = {
            "created_at": datetime.utcnow(),
            "source_doc_id": doc["_id"],
            "agent": res["agent"],
            "input": {"has_experience": has_exp, "target_role": None, "job_id": None},
            "extractions_snapshot": {
                "skills": res["features"]["skills"],
                "tokens": res["features"]["tokens"],
                "years_total": res["features"]["years_total"],
                "sections": res["features"]["sections_present"],
            },
            "scores": {
                "version": RUBRIC_VERSION,
                "by_block": res["scores"]["by_block"],
                "final": res["scores"]["final"],
                "label": res["scores"]["label"],
            },
            "explain": res["explain"],
        }
        db["evaluations"].insert_one(eval_doc)
        inserted += 1

    print(f"Backfill concluído. Inseridos: {inserted}")

def build_parser():
    ap = argparse.ArgumentParser(prog="resumAI", description="Runner de scoring/labels.")
    sp = ap.add_subparsers(dest="cmd", required=True)

    p1 = sp.add_parser("evaluate-one", help="Avalia 1 documento por _id")
    p1.add_argument("--id", required=True, help="ObjectId em resumAI.dados_processados")
    p1.add_argument("--has-experience", action="store_true", help="Marque se tem experiência")
    p1.add_argument("--force", action="store_true", help="Ignora cache e regrava")
    p1.set_defaults(func=cmd_evaluate_one)

    p2 = sp.add_parser("backfill", help="Gera avaliações em lote (labels fracas)")
    p2.add_argument("--limit", type=int, default=1000)
    p2.add_argument("--agent", choices=["auto","experienced","noexp"], default="auto")
    p2.add_argument("--force", action="store_true")
    p2.set_defaults(func=cmd_backfill)

    return ap

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
