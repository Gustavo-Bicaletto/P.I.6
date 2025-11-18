"""
Script para recalcular anos de experiência nos documentos já processados.
"""
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from pymongo import MongoClient
except ImportError:
    print("❌ pymongo não instalado. Execute: pip install pymongo")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    # Fallback se tqdm não estiver instalado
    def tqdm(iterable, total=None, desc=""):
        return iterable

# Importar a função de cálculo atualizada
from app.db.pre_processamento import calculate_years_experience


def recalcular_anos_experiencia(limite: int = 0):
    """
    Recalcula o campo years_experience para todos os documentos em dados_processados.
    """
    if load_dotenv:
        load_dotenv()
    
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "resumAI")
    TARGET_COLLECTION = os.getenv("TARGET_COLLECTION", "dados_processados")
    
    if not MONGO_URI:
        print("❌ MONGO_URI não configurado. Verifique seu arquivo .env")
        sys.exit(1)
    
    print(f"🔗 Conectando ao MongoDB...")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db[TARGET_COLLECTION]
    
    # Query para buscar documentos com experiências
    query = {"experiences": {"$exists": True, "$ne": []}}
    
    if limite > 0:
        cursor = collection.find(query).limit(limite)
        total = min(limite, collection.count_documents(query))
    else:
        total = collection.count_documents(query)
        cursor = collection.find(query)
    
    print(f"🔄 Recalculando anos de experiência para {total} documentos...")
    
    atualizados = 0
    erros = 0
    erros_detalhes = []
    
    for doc in tqdm(cursor, total=total, desc="Processando"):
        try:
            experiences = doc.get("experiences", [])
            
            # Recalcular anos de experiência usando a nova função
            years_exp = calculate_years_experience(experiences)
            
            # Atualizar no MongoDB
            collection.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "years_experience": years_exp,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            atualizados += 1
            
        except Exception as e:
            erros += 1
            erros_detalhes.append({
                "_id": doc.get("_id"),
                "erro": str(e)
            })
            if erros <= 5:  # Mostrar apenas os primeiros 5 erros
                print(f"\n❌ Erro no documento {doc.get('_id')}: {e}")
    
    print(f"\n✅ Recálculo concluído!")
    print(f"   📊 Atualizados: {atualizados}")
    print(f"   ❌ Erros: {erros}")
    
    if erros > 5:
        print(f"   ⚠️  (Mostrando apenas os primeiros 5 erros)")
    
    client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Recalcula anos de experiência nos documentos processados"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limitar número de documentos (0 = todos)"
    )
    
    args = parser.parse_args()
    
    recalcular_anos_experiencia(limite=args.limit)
