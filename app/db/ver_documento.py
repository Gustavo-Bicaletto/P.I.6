#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visualiza um documento específico do banco para análise
"""
import os
import sys
from dotenv import load_dotenv
import pymongo

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
db_name = 'resumAI'
target_coll = 'dados_processados'

client = pymongo.MongoClient(MONGO_URI)
db = client[db_name]
collection = db[target_coll]

# Pegar um documento COM experiências
doc_com = collection.find_one({'experiences': {'$exists': True, '$ne': []}})
print("=" * 80)
print("DOCUMENTO COM EXPERIÊNCIAS:")
print("=" * 80)
if doc_com:
    print(f"Filename: {doc_com.get('filename')}")
    print(f"Anos: {doc_com.get('years_experience', 0)}")
    print(f"Experiências: {len(doc_com.get('experiences', []))}")
    print("\nPrimeiras 2 experiências:")
    for i, exp in enumerate(doc_com.get('experiences', [])[:2], 1):
        print(f"\n  {i}. {exp.get('title')}")
        print(f"     Empresa: {exp.get('company')}")
        print(f"     Datas: {exp.get('dates')}")
        print(f"     Descrição: {exp.get('description', '')[:100]}...")
    
    print("\n\nTrecho do texto limpo (primeiras 2000 chars):")
    print("-" * 80)
    print(doc_com.get('resume_text_clean', '')[:2000])

# Pegar um documento SEM experiências
print("\n\n")
print("=" * 80)
print("DOCUMENTO SEM EXPERIÊNCIAS:")
print("=" * 80)
doc_sem = collection.find_one({'$or': [
    {'experiences': []},
    {'experiences': {'$exists': False}}
]})
if doc_sem:
    print(f"Filename: {doc_sem.get('filename')}")
    print(f"Anos: {doc_sem.get('years_experience', 0)}")
    print(f"Experiências: {len(doc_sem.get('experiences', []))}")
    
    print("\n\nTrecho do texto limpo (primeiras 3000 chars):")
    print("-" * 80)
    print(doc_sem.get('resume_text_clean', '')[:3000])

client.close()
