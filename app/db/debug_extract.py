#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug detalhado de extract_experiences
"""
import sys
sys.path.insert(0, 'd:/PI 6/P.I.6-1')

import re
from app.db.pre_processamento import normalize_fragmented_dates
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

# Pegar documento
client = pymongo.MongoClient(os.getenv('MONGO_URI'))
db = client['resumAI']
doc = db['curriculos'].find_one({'filename': {'$regex': '10554236'}})

if doc:
    texto_original = doc.get('resume_text', '')
    texto_norm = normalize_fragmented_dates(texto_original)
    
    # Regex
    date_full_range = r'(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4})\s*(?:[-–]|to)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:0?[1-9]|1[0-2])/\d{4}|\d{4}|Present|Current|Now)'
    
    lines = texto_norm.split('\n')
    
    print("=" * 80)
    print("DEBUG: Processando linhas do texto normalizado")
    print("=" * 80)
    
    found_dates = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.search(date_full_range, stripped, re.IGNORECASE)
        
        if match:
            found_dates += 1
            print(f"\n[LINHA {i}] MATCH ENCONTRADO:")
            print(f"  Linha completa: {repr(stripped[:100])}")
            print(f"  Data extraída: '{match.group(0)}'")
            
            # Contexto
            if i > 0:
                print(f"  Linha anterior: {repr(lines[i-1].strip()[:80])}")
            if i < len(lines) - 1:
                print(f"  Próxima linha: {repr(lines[i+1].strip()[:80])}")
    
    print("\n" + "=" * 80)
    print(f"TOTAL DE DATAS ENCONTRADAS: {found_dates}")
    print("=" * 80)

client.close()
