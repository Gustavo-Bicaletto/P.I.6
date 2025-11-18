#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug: verifica se normalize_fragmented_dates está sendo chamada
"""
import sys
sys.path.insert(0, 'd:/PI 6/P.I.6-1')

from app.db.pre_processamento import normalize_fragmented_dates, extract_experiences
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

# Pegar documento original
client = pymongo.MongoClient(os.getenv('MONGO_URI'))
db = client['resumAI']
doc = db['curriculos'].find_one({'filename': {'$regex': '10554236'}})

if doc:
    texto_original = doc.get('resume_text', '')
    
    print("=" * 80)
    print("TESTE: normalize_fragmented_dates()")
    print("=" * 80)
    
    # Procurar trecho com "July 2011"
    idx = texto_original.find('July 2011')
    if idx > 0:
        trecho_antes = texto_original[max(0, idx-50):idx+200]
        print("\nTRECHO ANTES DA NORMALIZAÇÃO:")
        print("-" * 80)
        print(repr(trecho_antes))
        
        # Aplicar normalização
        texto_norm = normalize_fragmented_dates(texto_original)
        
        # Procurar mesmo trecho após normalização
        idx2 = texto_norm.find('July 2011')
        if idx2 > 0:
            trecho_depois = texto_norm[max(0, idx2-50):idx2+200]
            print("\nTRECHO DEPOIS DA NORMALIZAÇÃO:")
            print("-" * 80)
            print(repr(trecho_depois))
            
            if 'July 2011 to November 2012' in texto_norm:
                print("\n✅ SUCESSO: Data foi consolidada!")
            else:
                print("\n❌ FALHA: Data NÃO foi consolidada")
                print("\nVerificando linhas individuais ao redor de 'July 2011':")
                lines = texto_original.split('\n')
                for i, line in enumerate(lines):
                    if 'July 2011' in line:
                        print(f"\nLinha {i}: {repr(line)}")
                        for j in range(max(0, i-2), min(len(lines), i+6)):
                            if j != i:
                                print(f"  {j}: {repr(lines[j])}")
                        break
    
    print("\n" + "=" * 80)
    print("TESTE: extract_experiences()")
    print("=" * 80)
    
    experiences = extract_experiences(texto_original)
    print(f"\nTotal de experiências extraídas: {len(experiences)}")
    
    for i, exp in enumerate(experiences[:3], 1):
        print(f"\n{i}. {exp.get('title')}")
        print(f"   Datas: {exp.get('dates')}")
        print(f"   Empresa: {exp.get('company')}")

client.close()
