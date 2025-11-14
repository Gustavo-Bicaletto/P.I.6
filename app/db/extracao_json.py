from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    MongoClient = None  # type: ignore

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def iter_batches(items: List[Dict], batch_size: int) -> Iterable[List[Dict]]:
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


def clean_record(rec: Dict) -> Optional[Dict]:
    if not isinstance(rec, dict) or not rec:
        return None
    if "_id" not in rec:
        # tenta construir um _id mínimo se possível
        cat = rec.get("category")
        fn = rec.get("filename")
        if cat and fn:
            rec["_id"] = f"{cat}/{fn}"
        else:
            return None
    # remove metadata.source_path se existir
    md = rec.get("metadata")
    if isinstance(md, dict) and "source_path" in md:
        md.pop("source_path", None)
    return rec


def load_json(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("O JSON esperado deve ser um array de objetos.")
    cleaned: List[Dict] = []
    dropped = 0
    for rec in data:
        good = clean_record(rec)
        if good is None:
            dropped += 1
            continue
        cleaned.append(good)
    logging.info(f"Registros carregados: {len(cleaned)} | Descartados/Inválidos: {dropped}")
    total = len(cleaned) + dropped
    if total > 0 and cleaned == []:
        logging.warning("Nenhum registro válido após limpeza. Verifique se o JSON master contém objetos com _id/filename/category.")
    return cleaned


def main() -> None:
    if load_dotenv:
        load_dotenv()

    root = project_root()
    env_json = os.getenv("OUTPUT_JSON")
    if env_json:
        json_default = Path(env_json)
        if not json_default.is_absolute():
            json_default = (root / json_default).resolve()
    else:
        json_default = (root / "app" / "resumes_dataset.json").resolve()

    parser = argparse.ArgumentParser(
        description="Carrega o JSON master (array) e faz upsert de 1 documento por PDF no MongoDB, removendo metadata.source_path."
    )
    parser.add_argument(
        "--json",
        default=os.getenv("OUTPUT_JSON")
        or str(Path(__file__).resolve().parents[1] / "resumes_dataset.json"),
        help="Caminho para o JSON master (env: OUTPUT_JSON).",
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"),
        help="URI do MongoDB (env: MONGO_URI/MONGODB_URI).",
    )
    parser.add_argument(
        "--mongo-db",
        default=os.getenv("MONGO_DB", "resumAI"),
        help="Nome do banco (env: MONGO_DB).",
    )
    parser.add_argument(
        "--mongo-coll",
        default=os.getenv("MONGO_COLLECTION", "curriculos"),
        help="Nome da coleção (env: MONGO_COLLECTION).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("BATCH_SIZE", "1000")),
        help="Tamanho do lote para bulk_write.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Não escreve no Mongo; só valida e exibe contagem.",
    )
    args = parser.parse_args()

    setup_logging()

    if MongoClient is None:
        logging.error("pymongo não instalado. Execute: py -m pip install pymongo")
        raise SystemExit(2)

    json_path = Path(args.json).resolve()
    logging.info(f"JSON master: {json_path}")
    if not json_path.exists():
        logging.error(f"JSON não encontrado: {json_path}")
        raise SystemExit(1)

    records = load_json(json_path)
    if args.dry_run:
        logging.info("Dry-run: finalizado sem escrita no MongoDB.")
        return

    if not args.mongo_uri:
        logging.error("Defina MONGO_URI/MONGODB_URI no .env ou passe --mongo-uri.")
        raise SystemExit(2)

    client = MongoClient(args.mongo_uri)
    col = client[args.mongo_db][args.mongo_coll]

    total = 0
    for batch in iter_batches(records, args.batch_size):
        ops = [UpdateOne({"_id": r["_id"]}, {"$set": r}, upsert=True) for r in batch]
        res = col.bulk_write(ops, ordered=False)
        upserts = getattr(res, "upserted_count", 0)
        modified = getattr(res, "modified_count", 0)
        total += len(batch)
        logging.info(f"Lote: {len(batch)} | Upserts: {upserts} | Modificados: {modified}")

    try:
        total_in_db = col.count_documents({})
        logging.info(f"Concluído. Processados: {total} | Total atual na coleção: {total_in_db}")
    except Exception:
        logging.info(f"Concluído. Processados: {total}")

if __name__ == "__main__":
    main()