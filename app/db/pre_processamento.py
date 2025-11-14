from __future__ import annotations

import argparse
import json as _json
import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

try:
    from pymongo import MongoClient, UpdateOne
except ImportError:
    MongoClient = None  # type: ignore

try:
    from datasketch import MinHash, MinHashLSH
except ImportError:
    MinHash = None  # type: ignore
    MinHashLSH = None  # type: ignore

try:
    import nltk
    from nltk.stem import PorterStemmer
    # baixar dados necessários (rodar uma vez): nltk.download('punkt')
except ImportError:
    nltk = None  # type: ignore
    PorterStemmer = None  # type: ignore


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ======================== NORMALIZAÇÃO DE TEXTO ========================

def normalize_text(s: str) -> str:
    """Normaliza bullets, espaços, case e caracteres especiais."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[•·●■▪◦▶►✓✔→]", "-", s)  # bullets
    s = re.sub(r"\t+", " ", s)
    s = re.sub(r"[ \u00A0\u2009\u200A]+", " ", s)  # espaços variados
    s = re.sub(r"\n{3,}", "\n\n", s)
    # remove caracteres unicode problemáticos (ex: ï¼​)
    s = re.sub(r"[^\x00-\x7F]+", " ", s)
    return s.strip()


def tokenize_and_stem(text: str, stemmer) -> List[str]:
    """Tokeniza e aplica stemming para normalizar plurais."""
    if not stemmer or not text:
        return text.lower().split()
    tokens = re.findall(r"\b[a-z]+\b", text.lower())
    return [stemmer.stem(t) for t in tokens if len(t) > 2]


def signature(p: str, stemmer=None) -> str:
    """Assinatura canônica (stemmed, sem pontuação)."""
    if stemmer:
        return " ".join(tokenize_and_stem(p, stemmer))
    t = p.casefold()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# ======================== SEGMENTAÇÃO ========================

def segment_paragraphs(s: str) -> List[str]:
    """Divide por linhas em branco duplas."""
    paras = [p.strip() for p in s.split("\n\n")]
    return [p for p in paras if p]


def dedupe_consecutive_lines(s: str, stemmer=None) -> str:
    """Remove linhas consecutivas idênticas (após stemming)."""
    lines = s.split("\n")
    out: List[str] = []
    last_sig = None
    for ln in lines:
        cur = ln.strip()
        if not cur:
            out.append(ln)
            continue
        sig = signature(cur, stemmer)
        if last_sig and sig == last_sig:
            continue  # skip duplicata
        out.append(ln)
        last_sig = sig
    return "\n".join(out)


# ======================== DEDUPLICAÇÃO DE PARÁGRAFOS ========================

def build_minhash(text: str, num_perm: int = 128) -> Optional[MinHash]:
    """Cria MinHash para detecção rápida de near-duplicates."""
    if MinHash is None:
        return None
    m = MinHash(num_perm=num_perm)
    tokens = text.lower().split()
    for tok in tokens:
        m.update(tok.encode("utf-8"))
    return m


def dedupe_paragraphs_minhash(
    paragraphs: List[str], threshold: float, num_perm: int = 128
) -> Dict[str, List[str]]:
    """Remove duplicatas exatas e near-duplicates usando MinHash LSH."""
    if MinHashLSH is None:
        # fallback para método SequenceMatcher
        return dedupe_paragraphs_fallback(paragraphs, threshold)

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    kept: List[str] = []
    removed_exact: List[str] = []
    removed_near: List[str] = []
    seen_sigs: Set[str] = set()

    for i, p in enumerate(paragraphs):
        sig = signature(p)
        if sig in seen_sigs:
            removed_exact.append(p)
            continue

        mh = build_minhash(p, num_perm)
        if mh is None:
            kept.append(p)
            seen_sigs.add(sig)
            continue

        # query LSH para near-duplicates
        result = lsh.query(mh)
        if result:
            removed_near.append(p)
            continue

        # adiciona ao índice e à lista de mantidos
        lsh.insert(f"p{i}", mh)
        kept.append(p)
        seen_sigs.add(sig)

    return {
        "kept": kept,
        "removed_exact": removed_exact,
        "removed_near": removed_near,
    }


def dedupe_paragraphs_fallback(paragraphs: List[str], threshold: float) -> Dict[str, List[str]]:
    """Fallback usando SequenceMatcher (O(n²), para datasets pequenos)."""
    kept: List[str] = []
    removed_exact: List[str] = []
    removed_near: List[str] = []
    seen: Set[str] = set()

    for p in paragraphs:
        sig = signature(p)
        if sig in seen:
            removed_exact.append(p)
            continue
        is_dup = False
        for q in kept:
            ratio = SequenceMatcher(None, sig, signature(q)).ratio()
            if ratio >= threshold:
                removed_near.append(p)
                is_dup = True
                break
        if not is_dup:
            kept.append(p)
            seen.add(sig)

    return {
        "kept": kept,
        "removed_exact": removed_exact,
        "removed_near": removed_near,
    }


# ======================== EXTRAÇÃO DE SKILLS ========================

def extract_skills(text: str) -> List[str]:
    """
    Extrai skills de seções como 'Skills:', 'Core Qualifications:', etc.
    Retorna lista normalizada (stemmed, sem duplicatas).
    """
    # regex para encontrar seção de skills
    match = re.search(
        r"(?:Skills?|Core Qualifications?|Highlights?|Technical Skills?)\s*[:\n](.*?)(?=\n[A-Z][a-z]+\s*[:\n]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    skills_text = match.group(1)
    # separa por vírgula, ponto-vírgula ou quebra de linha
    raw_skills = re.split(r"[,;\n]+", skills_text)
    stemmer = PorterStemmer() if PorterStemmer else None

    unique: Set[str] = set()
    for s in raw_skills:
        s = s.strip()
        if not s or len(s) < 3:
            continue
        # normaliza (stem se possível)
        canonical = signature(s, stemmer)
        unique.add(canonical)

    return sorted(unique)


# ======================== EXTRAÇÃO DE EXPERIÊNCIAS ========================

def extract_experiences(text: str) -> List[Dict[str, str]]:
    """
    Extrai blocos de experiência (cargo, empresa, período).
    Retorna lista de dicts: {title, company, dates, description}.
    """
    # regex simplificado para detectar blocos de cargo
    # formato comum: "Job Title\nMonth Year to Month Year\nCompany Name\n- bullet..."
    pattern = re.compile(
        r"^([A-Z][A-Za-z\s&]+)\s*\n"  # título do cargo
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s+to\s+(?:Present|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}))\s*\n"  # datas
        r"(Company Name.*?)\s*\n"  # empresa
        r"((?:.*\n)*?)"  # descrição (até próximo cargo ou fim)
        r"(?=^[A-Z][A-Za-z\s&]+\s*\n(?:January|February|March|April|May|June|July|August|September|October|November|December)|\Z)",
        re.MULTILINE,
    )

    experiences = []
    for m in pattern.finditer(text):
        experiences.append({
            "title": m.group(1).strip(),
            "dates": m.group(2).strip(),
            "company": m.group(3).strip(),
            "description": m.group(4).strip(),
        })
    return experiences


def dedupe_experiences(experiences: List[Dict[str, str]], threshold: float) -> List[Dict[str, str]]:
    """Remove experiências duplicadas por título+empresa+datas ou descrição similar."""
    unique = []
    seen_keys: Set[str] = set()

    for exp in experiences:
        key = f"{exp['title'].lower()}|{exp['company'].lower()}|{exp['dates']}"
        if key in seen_keys:
            continue
        # checa similaridade de descrição com experiências já aceitas
        is_dup = False
        for u in unique:
            if u["title"].lower() == exp["title"].lower() and u["company"].lower() == exp["company"].lower():
                ratio = SequenceMatcher(None, exp["description"], u["description"]).ratio()
                if ratio >= threshold:
                    is_dup = True
                    break
        if not is_dup:
            unique.append(exp)
            seen_keys.add(key)

    return unique


def calculate_years_experience(dates_str: str) -> float:
    """
    Calcula anos de experiência a partir de string de datas (ex: "January 2010 to December 2015").
    Retorna float (anos completos + fração).
    """
    pattern = r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+to\s+(Present|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4}))"
    match = re.search(pattern, dates_str, re.IGNORECASE)
    if not match:
        return 0.0

    month_map = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
    start_month = month_map.get(match.group(1), 1)
    start_year = int(match.group(2))
    end_str = match.group(3)

    if end_str.lower() == "present":
        end_year = datetime.now().year
        end_month = datetime.now().month
    else:
        end_month = month_map.get(match.group(3).split()[0], 12)
        end_year = int(match.group(4))

    months = (end_year - start_year) * 12 + (end_month - start_month)
    return round(months / 12.0, 1)


# ======================== PRÉ-PROCESSAMENTO PRINCIPAL ========================

def preprocess_text(raw: str, min_similarity: float) -> Dict[str, object]:
    """
    Pipeline completo de pré-processamento:
    - Normaliza texto
    - Remove linhas consecutivas duplicadas
    - Deduplica parágrafos (MinHash ou fallback)
    - Extrai e deduplica skills
    - Extrai e deduplica experiências
    - Calcula anos totais de experiência
    """
    stemmer = PorterStemmer() if PorterStemmer else None

    # 1. Normalização
    norm = normalize_text(raw)
    no_dup_lines = dedupe_consecutive_lines(norm, stemmer)

    # 2. Deduplicação de parágrafos
    paragraphs = segment_paragraphs(no_dup_lines)
    de = dedupe_paragraphs_minhash(paragraphs, threshold=min_similarity)
    clean_text = "\n\n".join(de["kept"])

    # 3. Extração de skills
    skills = extract_skills(clean_text)

    # 4. Extração de experiências
    experiences = extract_experiences(clean_text)
    experiences_deduped = dedupe_experiences(experiences, threshold=0.90)

    # 5. Cálculo de anos de experiência
    total_years = sum(calculate_years_experience(exp["dates"]) for exp in experiences_deduped)

    stats = {
        "paragraphs_input": len(paragraphs),
        "paragraphs_kept": len(de["kept"]),
        "paragraphs_removed_exact": len(de["removed_exact"]),
        "paragraphs_removed_near": len(de["removed_near"]),
        "skills_unique": len(skills),
        "experiences_total": len(experiences),
        "experiences_deduped": len(experiences_deduped),
        "years_experience": total_years,
    }

    return {
        "text": clean_text,
        "skills": skills,
        "experiences": experiences_deduped,
        "years_experience": total_years,
        "stats": stats,
    }


# ======================== MAIN ========================

def load_env() -> None:
    if load_dotenv:
        load_dotenv()


def main() -> None:
    load_env()
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Pré-processa currículos: remove duplicatas, extrai skills/experiências, calcula anos de experiência."
    )
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"), help="URI do MongoDB.")
    parser.add_argument("--mongo-db", default=os.getenv("MONGO_DB", "resumAI"), help="Banco de dados.")
    parser.add_argument("--source-coll", default=os.getenv("SOURCE_COLLECTION", "curriculos"), help="Coleção de origem.")
    parser.add_argument("--target-coll", default=os.getenv("TARGET_COLLECTION", "dados_processados"), help="Coleção de destino.")
    parser.add_argument("--min-similarity", type=float, default=float(os.getenv("PREPROC_MIN_SIM", "0.96")), help="Limite para near-duplicate [0-1].")
    parser.add_argument("--query", default=os.getenv("PREPROC_QUERY", "{}"), help="Filtro JSON para subset.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("PREPROC_LIMIT", "0")), help="Limite de documentos (0 = todos).")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("PREPROC_BATCH", "200")), help="Lote de upserts.")
    args = parser.parse_args()

    if MongoClient is None:
        logging.error("pymongo não instalado. Execute: py -m pip install pymongo")
        raise SystemExit(2)
    if not args.mongo_uri:
        logging.error("Defina MONGO_URI no .env ou via --mongo-uri.")
        raise SystemExit(2)

    # Avisos sobre dependências opcionais
    if MinHash is None:
        logging.warning("datasketch não instalado. Usando fallback SequenceMatcher (mais lento). Instale: py -m pip install datasketch")
    if PorterStemmer is None:
        logging.warning("nltk não instalado. Stemming desabilitado. Instale: py -m pip install nltk")

    client = MongoClient(args.mongo_uri)
    src = client[args.mongo_db][args.source_coll]
    dst = client[args.mongo_db][args.target_coll]

    try:
        q: Dict[str, object] = _json.loads(args.query)
    except Exception:
        logging.warning("Filtro --query inválido. Usando {}.")
        q = {}

    logging.info(f"Origem: db={args.mongo_db}, coll={args.source_coll} | Destino: coll={args.target_coll}")
    logging.info(f"Filtro: {q} | min_similarity={args.min_similarity} | limit={args.limit or 'todos'}")

    cursor = src.find(
        q,
        {"_id": 1, "filename": 1, "category": 1, "resume_text": 1, "metadata": 1}
    )
    
    processed = 0
    batch: List[UpdateOne] = []
    now = datetime.now(timezone.utc).isoformat()

    try:
        for doc in cursor:
            text = (doc.get("resume_text") or "").strip()
            if not text:
                continue

            pp = preprocess_text(text, min_similarity=args.min_similarity)

            out_doc: Dict[str, object] = {
                "_id": doc["_id"],
                "filename": doc.get("filename"),
                "category": doc.get("category"),
                "resume_text_clean": pp["text"],
                "skills": pp["skills"],
                "experiences": pp["experiences"],
                "years_experience": pp["years_experience"],
                "metadata": {
                    "pages": (doc.get("metadata") or {}).get("pages"),
                    "extracted_at": (doc.get("metadata") or {}).get("extracted_at"),
                },
                "preproc": {
                    "created_at": now,
                    "stats": pp["stats"],
                    "min_similarity": args.min_similarity,
                },
            }

            batch.append(UpdateOne({"_id": out_doc["_id"]}, {"$set": out_doc}, upsert=True))
            processed += 1

            if len(batch) >= args.batch_size:
                res = dst.bulk_write(batch, ordered=False)
                logging.info(f"Lote salvo: {len(batch)} | upserts={getattr(res, 'upserted_count', 0)} | modified={getattr(res, 'modified_count', 0)}")
                batch = []

            if args.limit and processed >= args.limit:
                break
    finally:
        cursor.close()

    if batch:
        res = dst.bulk_write(batch, ordered=False)
        logging.info(f"Lote final salvo: {len(batch)} | upserts={getattr(res, 'upserted_count', 0)} | modified={getattr(res, 'modified_count', 0)}")

    total_dst = dst.count_documents({})
    logging.info(f"Concluído. Processados={processed} | Total na coleção destino={total_dst}")


if __name__ == "__main__":
    main()