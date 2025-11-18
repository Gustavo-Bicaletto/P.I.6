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

def normalize_fragmented_dates(text: str) -> str:
    """
    Normaliza datas fragmentadas que aparecem em linhas separadas.
    Exemplos: 
    - "July 2011\n \nto \nNovember 2012" -> "July 2011 to November 2012"
    - "10/2012\n \nto \n11/2015" -> "10/2012 to 11/2015"
    """
    lines = text.split('\n')
    result = []
    skip_until = -1
    
    for i in range(len(lines)):
        if i < skip_until:
            continue
            
        line = lines[i].strip()
        
        # Padrões: "Month Year" OU "MM/YYYY"
        month_year = re.match(r'^((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})$', line, re.IGNORECASE)
        mm_yyyy = re.match(r'^((?:0?[1-9]|1[0-2])/\d{4})$', line)
        
        if month_year or mm_yyyy:
            start_date = (month_year or mm_yyyy).group(1)
            
            # Procurar "to" nas próximas linhas (até 10 linhas à frente)
            found_to = False
            end_date = None
            
            for j in range(i + 1, min(i + 11, len(lines))):
                check_line = lines[j].strip()
                
                # Linha vazia, ignorar
                if not check_line:
                    continue
                
                # Encontrou "to"
                if check_line.lower() == 'to':
                    found_to = True
                    # Procurar data final após o "to"
                    for k in range(j + 1, min(j + 6, len(lines))):
                        end_line = lines[k].strip()
                        if not end_line:
                            continue
                        
                        # Verificar se é uma data válida (Month Year, MM/YYYY, ou Present)
                        end_match = re.match(r'^((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|Present|Current|Now)$', end_line, re.IGNORECASE)
                        
                        if end_match:
                            end_date = end_match.group(1)
                            # Consolidar data completa
                            result.append(f"{start_date} to {end_date}")
                            skip_until = k + 1
                            break
                        else:
                            # Não é data válida, parar busca
                            break
                    
                    if end_date:
                        break
                    else:
                        # Tinha "to" mas não encontrou data válida
                        break
                
                # Se a linha não é vazia nem "to", parar busca
                if check_line.lower() != 'to':
                    break
            
            # Se não consolidou, adicionar linha original
            if not end_date:
                result.append(line)
        else:
            result.append(line)
    
    return '\n'.join(result)


def extract_experiences(text: str) -> List[Dict[str, str]]:
    """
    Extrai blocos de experiência (cargo, empresa, período) de múltiplos formatos.
    Versão robusta que lida com diversos layouts de currículos, incluindo datas fragmentadas.
    Retorna lista de dicts: {title, company, dates, description}.
    """
    # PRIMEIRO: Normalizar datas fragmentadas
    text = normalize_fragmented_dates(text)
    
    experiences = []
    
    # Padrões de data
    date_full_range = r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4})\s*(?:[-–]|to)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4}|Present|Current|Now)'
    date_single = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4}'
    
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Buscar data completa
        date_match = re.search(date_full_range, line, re.IGNORECASE)
        
        if date_match:
            dates = date_match.group(0)
            title = ""
            company = "Company Name"
            
            # Buscar título antes da data
            text_before = line[:date_match.start()].strip()
            if text_before and len(text_before) > 3 and text_before.lower() not in ['experience', 'work', 'history', 'company name']:
                title = text_before
            
            # Buscar título nas linhas anteriores (pulando vazias)
            if not title:
                for k in range(i - 1, max(i - 5, -1), -1):
                    prev_line = lines[k].strip()
                    if prev_line and len(prev_line) > 3:
                        if not re.match(r'^(Experience|Work History|Employment|Professional|Career|Company Name)$', prev_line, re.IGNORECASE):
                            if not re.search(date_single, prev_line, re.IGNORECASE):
                                title = prev_line
                                break
            
            # Buscar empresa/título depois da data
            text_after = line[date_match.end():].strip()
            if text_after and len(text_after) > 2:
                if not title:
                    title = text_after
                else:
                    company = text_after
            
            # Buscar nas próximas linhas (pulando vazias)
            if not title or company == "Company Name":
                for k in range(i + 1, min(i + 6, len(lines))):
                    next_line = lines[k].strip()
                    if next_line and len(next_line) > 2:
                        if not re.search(date_single, next_line, re.IGNORECASE):
                            if not re.match(r'^(Education|Skills|Certifications|Summary|City|State)$', next_line, re.IGNORECASE):
                                if not title:
                                    title = next_line
                                    break
                                elif company == "Company Name":
                                    company = next_line
                                    break
            
            # Coletar descrição
            description_lines = []
            j = i + 1
            
            # Pular linhas já identificadas (empresa/título) e vazias
            skip_lines = {title.lower(), company.lower(), 'company name', 'city', 'state', ','}
            while j < len(lines):
                check = lines[j].strip().lower()
                if check and check not in skip_lines:
                    break
                j += 1
            
            collected = 0
            while j < len(lines) and collected < 10:
                desc_line = lines[j].strip()
                
                if re.search(date_full_range, desc_line, re.IGNORECASE):
                    break
                if re.match(r'^(Education|Skills|Certifications|Summary|Objective|Interests?|Awards?|Company Name)$', desc_line, re.IGNORECASE):
                    break
                
                if desc_line and len(desc_line) > 5:
                    description_lines.append(desc_line)
                    collected += 1
                
                j += 1
            
            description = ' '.join(description_lines[:5])
            
            # Adicionar mesmo se não tiver título (usar "Professional Experience")
            if not title or len(title) < 3:
                title = "Professional Experience"
            
            if title.lower() != 'company name':
                experiences.append({
                    "title": title[:150],
                    "dates": dates[:100],
                    "company": company[:150],
                    "description": description[:600],
                })
            
            i = j
        else:
            i += 1
    
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


def parse_single_date_range(dates_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Extrai data de início e fim de uma string de datas.
    Retorna tupla (start_date, end_date) ou (None, None) se falhar.
    """
    try:
        from dateutil import parser as date_parser
    except ImportError:
        date_parser = None
    
    if not dates_str:
        return (None, None)
    
    # Remove "to", "-", "–" e substitui por separador comum
    dates_str = re.sub(r'\s+to\s+|\s*-\s*|\s*–\s*', ' | ', dates_str, flags=re.IGNORECASE)
    
    parts = [p.strip() for p in dates_str.split('|') if p.strip()]
    
    if len(parts) != 2:
        # Tentar outro formato: "2010 - 2015" ou "Jan 2010 - Dec 2015"
        match = re.search(r'(\w+\s+\d{4}|\d{4})\s*[-–|]\s*(\w+\s+\d{4}|\d{4}|present|current)', dates_str, re.IGNORECASE)
        if match:
            parts = [match.group(1), match.group(2)]
        else:
            return (None, None)
    
    start_str, end_str = parts
    
    try:
        # Parse com dateutil se disponível
        if date_parser:
            start_date = date_parser.parse(start_str, fuzzy=True)
            
            if re.search(r'present|current|now', end_str, re.IGNORECASE):
                end_date = datetime.now()
            else:
                end_date = date_parser.parse(end_str, fuzzy=True)
        else:
            # Fallback manual se dateutil não estiver instalado
            month_map = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", 
                                                       "july", "august", "september", "october", "november", "december"], 1)}
            
            # Extrair ano e mês do início
            start_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', start_str, re.IGNORECASE)
            if start_match:
                start_month = month_map.get(start_match.group(1).lower(), 1)
                start_year = int(start_match.group(2))
                start_date = datetime(start_year, start_month, 1)
            else:
                # Apenas ano
                year_match = re.search(r'\b(19|20)\d{2}\b', start_str)
                if year_match:
                    start_date = datetime(int(year_match.group(0)), 1, 1)
                else:
                    return (None, None)
            
            # Extrair ano e mês do fim
            if re.search(r'present|current|now', end_str, re.IGNORECASE):
                end_date = datetime.now()
            else:
                end_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', end_str, re.IGNORECASE)
                if end_match:
                    end_month = month_map.get(end_match.group(1).lower(), 12)
                    end_year = int(end_match.group(2))
                    end_date = datetime(end_year, end_month, 28)
                else:
                    year_match = re.search(r'\b(19|20)\d{2}\b', end_str)
                    if year_match:
                        end_date = datetime(int(year_match.group(0)), 12, 31)
                    else:
                        return (None, None)
        
        # Validar que end_date >= start_date
        if end_date >= start_date:
            return (start_date, end_date)
        else:
            return (None, None)
    
    except (ValueError, TypeError, AttributeError):
        return (None, None)


def calculate_years_experience(input_data) -> float:
    """
    Calcula anos totais de experiência.
    
    Args:
        input_data: pode ser:
            - str: string de datas (ex: "January 2010 to December 2015")
            - list[dict]: lista de experiências com campo 'dates'
    
    Retorna:
        float: anos totais de experiência (lida com sobreposições)
    """
    date_ranges = []
    
    # Se for string, converter para lista de 1 elemento
    if isinstance(input_data, str):
        start, end = parse_single_date_range(input_data)
        if start and end:
            date_ranges.append((start, end))
    
    # Se for lista de experiências
    elif isinstance(input_data, list):
        for exp in input_data:
            if isinstance(exp, dict):
                dates_str = exp.get("dates", "").strip()
            else:
                dates_str = str(exp).strip()
            
            if dates_str:
                start, end = parse_single_date_range(dates_str)
                if start and end:
                    date_ranges.append((start, end))
    
    if not date_ranges:
        return 0.0
    
    # Ordenar por data de início
    date_ranges.sort(key=lambda x: x[0])
    
    # Mesclar períodos sobrepostos
    merged_ranges = []
    current_start, current_end = date_ranges[0]
    
    for start, end in date_ranges[1:]:
        if start <= current_end:
            # Sobreposição - estender o período atual
            current_end = max(current_end, end)
        else:
            # Sem sobreposição - salvar período atual e começar novo
            merged_ranges.append((current_start, current_end))
            current_start, current_end = start, end
    
    # Adicionar o último período
    merged_ranges.append((current_start, current_end))
    
    # Calcular total de anos
    total_days = sum((end - start).days for start, end in merged_ranges)
    total_years = round(total_days / 365.25, 1)
    
    return total_years


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

    # 5. Cálculo de anos de experiência (passa lista completa para lidar com sobreposições)
    total_years = calculate_years_experience(experiences_deduped)

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