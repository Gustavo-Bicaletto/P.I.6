"""
Script para diagnosticar problemas com extração de experiências.
"""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from collections import Counter


def diagnosticar_experiencias():
    load_dotenv()
    
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "resumAI")
    TARGET_COLLECTION = os.getenv("TARGET_COLLECTION", "dados_processados")
    
    if not MONGO_URI:
        print("❌ MONGO_URI não configurado. Verifique seu arquivo .env")
        sys.exit(1)
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[TARGET_COLLECTION]
    
    total_docs = collection.count_documents({})
    
    # Contar documentos por situação
    com_experiences = collection.count_documents({"experiences": {"$exists": True, "$ne": []}})
    sem_experiences = collection.count_documents({"experiences": {"$exists": True, "$eq": []}})
    sem_campo = collection.count_documents({"experiences": {"$exists": False}})
    
    print(f"📊 Diagnóstico de Experiências")
    print(f"=" * 60)
    print(f"Total de documentos: {total_docs}")
    print(f"Com experiências extraídas: {com_experiences} ({com_experiences/total_docs*100:.1f}%)")
    print(f"Com campo vazio []: {sem_experiences} ({sem_experiences/total_docs*100:.1f}%)")
    print(f"Sem campo 'experiences': {sem_campo} ({sem_campo/total_docs*100:.1f}%)")
    print()
    
    # Analisar alguns documentos sem experiências
    print(f"🔍 Analisando 5 documentos SEM experiências extraídas...")
    print(f"=" * 60)
    
    docs_sem_exp = collection.find(
        {"$or": [
            {"experiences": {"$eq": []}},
            {"experiences": {"$exists": False}}
        ]},
        {"_id": 1, "category": 1, "resume_text_clean": 1, "years_experience": 1}
    ).limit(5)
    
    for i, doc in enumerate(docs_sem_exp, 1):
        text = doc.get("resume_text_clean", "")
        print(f"\n📄 Documento {i}: {doc['_id']}")
        print(f"   Categoria: {doc.get('category', 'N/A')}")
        print(f"   Years exp atual: {doc.get('years_experience', 0)}")
        print(f"   Tamanho do texto: {len(text)} caracteres")
        
        # Mostrar trecho do texto que pode conter experiências
        lines = text.split('\n')
        exp_keywords = ['experience', 'work history', 'employment', 'professional', 'career']
        
        for j, line in enumerate(lines[:50]):  # primeiras 50 linhas
            line_lower = line.lower()
            if any(kw in line_lower for kw in exp_keywords):
                print(f"\n   Linha {j}: {line[:100]}")
                # Mostrar próximas 3 linhas
                for k in range(j+1, min(j+4, len(lines))):
                    print(f"   Linha {k}: {lines[k][:100]}")
                break
    
    # Verificar anos de experiência zerados ou muito baixos
    years_zero = collection.count_documents({"years_experience": {"$lte": 0}})
    years_baixo = collection.count_documents({"years_experience": {"$gt": 0, "$lt": 1}})
    
    print(f"\n" + "=" * 60)
    print(f"📉 Anos de experiência:")
    print(f"   Zero ou negativo: {years_zero}")
    print(f"   Entre 0 e 1 ano: {years_baixo}")
    
    # Distribuição de anos de experiência
    pipeline = [
        {"$bucket": {
            "groupBy": "$years_experience",
            "boundaries": [0, 1, 3, 5, 10, 20, 50],
            "default": "50+",
            "output": {"count": {"$sum": 1}}
        }}
    ]
    
    print(f"\n📊 Distribuição de anos de experiência:")
    for bucket in collection.aggregate(pipeline):
        print(f"   {bucket['_id']}: {bucket['count']} documentos")
    
    client.close()


if __name__ == "__main__":
    diagnosticar_experiencias()
