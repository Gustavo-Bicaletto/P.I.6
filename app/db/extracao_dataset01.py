from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    MongoClient = None  # type: ignore

# Carrega variáveis do .env (se python-dotenv estiver instalado)
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

DEFAULT_MONGO_DB = "resumAI"
DEFAULT_MONGO_COLL = "curriculos"


def project_root() -> Path:
    # este arquivo está em app/db; subir 1 nível -> app
    return Path(__file__).resolve().parents[1]


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler])


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, int]:
    """
    Extrai texto de todas as páginas de um PDF.
    Retorna (texto_completo, numero_de_paginas).
    """
    with pdf_path.open("rb") as f:
        reader = PdfReader(f)
        try:
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")  # tenta senha em branco
                except Exception:
                    pass
        except Exception:
            pass

        num_pages = len(reader.pages)
        texts: List[str] = []
        for i in range(num_pages):
            try:
                page = reader.pages[i]
                txt = page.extract_text() or ""
            except Exception as e:
                logging.warning(f"Falha ao extrair texto da página {i+1} de '{pdf_path.name}': {e}")
                txt = ""
            texts.append(txt)
        full_text = "\n".join(texts).strip()
        return full_text, num_pages


def build_record(pdf_path: Path, category: str, extracted_at: str) -> Optional[Dict]:
    try:
        text, pages = extract_text_from_pdf(pdf_path)
    except (PdfReadError, Exception) as e:
        logging.error(f"PDF corrompido/ilegível ignorado: '{pdf_path}' | erro: {e}")
        return None

    if not text:
        logging.warning(f"Nenhum texto extraído (possível PDF escaneado): '{pdf_path}'")

    record = {
        "_id": f"{category}/{pdf_path.name}",
        "filename": pdf_path.name,
        "category": category,
        "resume_text": text,
        "metadata": {
            "pages": pages,
            "extracted_at": extracted_at,
            "source_path": str(pdf_path),
        },
    }
    return record


def process_dataset(
    input_dir: Path,
    output_json: Path,
    mongo_uri: Optional[str],
    mongo_db: str,
    mongo_coll: str,
) -> None:
    # MongoDB agora é obrigatório
    if MongoClient is None:
        logging.error("pymongo não instalado. Execute: pip install pymongo")
        raise SystemExit(2)

    uri = mongo_uri or os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not uri:
        logging.error("MongoDB obrigatório. Defina --mongo-uri ou MONGO_URI/MONGODB_URI no .env.")
        raise SystemExit(2)

    extracted_at = datetime.now(timezone.utc).isoformat()

    client = MongoClient(uri)
    db = client[mongo_db]
    col = db[mongo_coll]
    safe_host = uri.split("@")[-1] if "@" in uri else uri
    logging.info(f"Conectado ao MongoDB -> host: {safe_host} | db: {mongo_db} | coleção: {mongo_coll}")

    categories = [d for d in input_dir.iterdir() if d.is_dir()]
    if not categories:
        logging.warning(f"Nenhuma pasta de categoria encontrada em: {input_dir}")

    all_records: List[Dict] = []
    corrupted_count = 0
    total_pdfs = 0

    for cat_dir in sorted(categories):
        category = cat_dir.name
        pdf_files = list(cat_dir.rglob("*.pdf"))
        if not pdf_files:
            logging.info(f"[{category}] Nenhum PDF encontrado.")
            continue

        logging.info(f"[{category}] Encontrados {len(pdf_files)} PDF(s). Iniciando extração...")
        for pdf in pdf_files:
            total_pdfs += 1
            rec = build_record(pdf, category, extracted_at)
            if rec is None:
                corrupted_count += 1
                continue
            all_records.append(rec)

        logging.info(f"[{category}] Extração concluída. Válidos acumulados: {len(all_records)}.")

    # Salvar JSON (array) em disco
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    logging.info(f"Dataset salvo em: {output_json}")
    logging.info(f"Total de PDFs processados: {total_pdfs} | Registros válidos: {len(all_records)} | Corrompidos: {corrupted_count}")

    # Inserção obrigatória no MongoDB (upsert em lote, 1 doc por PDF)
    ops = [UpdateOne({"_id": rec["_id"]}, {"$set": rec}, upsert=True) for rec in all_records]
    if ops:
        result = col.bulk_write(ops, ordered=False)
        upserts = getattr(result, "upserted_count", 0)
        modified = getattr(result, "modified_count", 0)
        logging.info(f"MongoDB concluído. Upserts: {upserts}, Modificados: {modified}")
    else:
        logging.info("Nenhum registro para inserir no MongoDB.")

def parse_args() -> argparse.Namespace:
    # carrega .env antes de ler defaults
    if load_dotenv:
        load_dotenv()

    root = project_root()

    # Defaults vindos do .env; se não houver, cair em paths organizados na pasta data/outputs/resumes
    env_input = os.getenv("DATASET_BASE_DIR")
    env_output = os.getenv("OUTPUT_JSON")
    if env_output:
        # se for relativo, torna relativo à raiz do projeto
        if not os.path.isabs(env_output):
            env_output = str((root / env_output).resolve())
    else:
        env_output = str(root / "data" / "outputs" / "resumes" / "resumes_dataset.json")

    env_log = os.getenv("LOG_FILE")
    if env_log:
        if not os.path.isabs(env_log):
            env_log = str((root / env_log).resolve())
    else:
        env_log = str(root / "data" / "outputs" / "resumes" / "logs" / "extraction.log")

    parser = argparse.ArgumentParser(
        description="Extrai textos de currículos em PDF organizados por categorias, salva JSON e insere no MongoDB."
    )
    parser.add_argument(
        "--input-dir",
        default=env_input,
        help="Pasta base do dataset (cada subpasta é uma categoria). Pode ser definido via .env: DATASET_BASE_DIR",
    )
    parser.add_argument(
        "--output",
        default=env_output,
        help="Arquivo JSON de saída (padrão do .env OUTPUT_JSON ou data/outputs/resumes/resumes_dataset.json).",
    )
    # Mongo agora é obrigatório; defaults vindos do .env
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"),
        help="URI do MongoDB (env: MONGO_URI ou MONGODB_URI).",
    )
    parser.add_argument(
        "--mongo-db",
        default=os.getenv("MONGO_DB", DEFAULT_MONGO_DB),
        help=f"Nome do banco no MongoDB (env: MONGO_DB, default: {DEFAULT_MONGO_DB}).",
    )
    parser.add_argument(
        "--mongo-coll",
        default=os.getenv("MONGO_COLLECTION", DEFAULT_MONGO_COLL),
        help=f"Coleção no MongoDB (env: MONGO_COLLECTION, default: {DEFAULT_MONGO_COLL}).",
    )
    parser.add_argument(
        "--log-file",
        default=env_log,
        help="Arquivo de log (padrão do .env LOG_FILE ou data/outputs/resumes/logs/extraction.log).",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    setup_logging(Path(args.log_file))

    if not args.input_dir:
        logging.error("Defina --input-dir ou a variável DATASET_BASE_DIR no .env.")
        raise SystemExit(2)

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        logging.error(f"Pasta de entrada inválida: {input_dir}")
        raise SystemExit(1)

    output_json = Path(args.output)
    process_dataset(
        input_dir=input_dir,
        output_json=output_json,
        mongo_uri=args.mongo_uri,
        mongo_db=args.mongo_db,
        mongo_coll=args.mongo_coll,
    )

if __name__ == "__main__":
    main()