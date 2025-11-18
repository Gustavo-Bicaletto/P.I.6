#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prepara dados de treinamento a partir do MongoDB.
Cria datasets balanceados para classificação de currículos.
"""
import os
import json
from datetime import datetime
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv
from pymongo import MongoClient
from tqdm import tqdm


def prepare_training_data(
    output_dir: str = "data/training",
    min_years_experienced: float = 2.0,
    test_size: float = 0.2,
    val_size: float = 0.1,
    balance: bool = True,
    max_samples_per_class: int = None
):
    """
    Prepara dados de treinamento do MongoDB.
    
    Args:
        output_dir: Diretório de saída
        min_years_experienced: Anos mínimos para classificar como "experienced"
        test_size: % para teste
        val_size: % para validação
        balance: Se True, balanceia classes
        max_samples_per_class: Limite por classe (None = sem limite)
    """
    load_dotenv()
    
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "resumAI")
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db["dados_processados"]
    
    # Criar diretório de saída
    os.makedirs(output_dir, exist_ok=True)
    
    print("📊 Coletando dados do MongoDB...")
    
    # Query: documentos com texto limpo e experiências
    query = {
        "resume_text_clean": {"$exists": True, "$ne": ""},
        "experiences": {"$exists": True}
    }
    
    cursor = collection.find(query, {
        "_id": 1,
        "resume_text_clean": 1,
        "skills": 1,
        "experiences": 1,
        "years_experience": 1,
        "category": 1,
        "filename": 1
    })
    
    total = collection.count_documents(query)
    
    # Classificar em experienced (1) ou not experienced (0)
    data_experienced = []
    data_not_experienced = []
    
    for doc in tqdm(cursor, total=total, desc="Processando"):
        years = doc.get("years_experience", 0.0)
        text = doc.get("resume_text_clean", "").strip()
        
        if not text or len(text) < 100:  # Filtrar textos muito curtos
            continue
        
        sample = {
            "_id": str(doc["_id"]),
            "text": text,
            "skills": doc.get("skills", []),
            "years_experience": years,
            "category": doc.get("category", "UNKNOWN"),
            "num_experiences": len(doc.get("experiences", [])),
            "filename": doc.get("filename", "")
        }
        
        # Classificação binária
        if years >= min_years_experienced:
            sample["label"] = 1  # Experienced
            data_experienced.append(sample)
        else:
            sample["label"] = 0  # Not experienced
            data_not_experienced.append(sample)
    
    print(f"\n✅ Dados coletados:")
    print(f"   Experienced (label=1): {len(data_experienced)}")
    print(f"   Not experienced (label=0): {len(data_not_experienced)}")
    
    # Balancear dataset
    if balance:
        min_size = min(len(data_experienced), len(data_not_experienced))
        if max_samples_per_class:
            min_size = min(min_size, max_samples_per_class)
        
        data_experienced = data_experienced[:min_size]
        data_not_experienced = data_not_experienced[:min_size]
        
        print(f"\n⚖️  Dataset balanceado: {min_size} amostras por classe")
    
    # Combinar dados
    all_data = data_experienced + data_not_experienced
    
    print(f"\n📦 Total de amostras: {len(all_data)}")
    
    # Separar em treino, validação e teste
    train_data, temp_data = train_test_split(
        all_data, 
        test_size=(test_size + val_size),
        stratify=[d["label"] for d in all_data],
        random_state=42
    )
    
    val_data, test_data = train_test_split(
        temp_data,
        test_size=test_size / (test_size + val_size),
        stratify=[d["label"] for d in temp_data],
        random_state=42
    )
    
    print(f"\n📦 Split realizado:")
    print(f"   Treino: {len(train_data)} ({len([d for d in train_data if d['label']==1])} exp, {len([d for d in train_data if d['label']==0])} noexp)")
    print(f"   Validação: {len(val_data)} ({len([d for d in val_data if d['label']==1])} exp, {len([d for d in val_data if d['label']==0])} noexp)")
    print(f"   Teste: {len(test_data)} ({len([d for d in test_data if d['label']==1])} exp, {len([d for d in test_data if d['label']==0])} noexp)")
    
    # Salvar arquivos
    datasets = {
        "train": train_data,
        "validation": val_data,
        "test": test_data
    }
    
    for split_name, split_data in datasets.items():
        filepath = os.path.join(output_dir, f"{split_name}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(split_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ Salvo: {filepath}")
    
    # Salvar metadados
    metadata = {
        "created_at": datetime.utcnow().isoformat(),
        "min_years_experienced": min_years_experienced,
        "balanced": balance,
        "total_samples": len(all_data),
        "train_size": len(train_data),
        "val_size": len(val_data),
        "test_size": len(test_data),
        "class_distribution": {
            "experienced": len(data_experienced),
            "not_experienced": len(data_not_experienced)
        }
    }
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"   ✅ Metadados: {metadata_path}")
    
    client.close()
    
    print(f"\n🎉 Preparação concluída! Dados salvos em: {output_dir}")
    return metadata


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepara dados de treinamento")
    parser.add_argument("--output-dir", default="data/training", help="Diretório de saída")
    parser.add_argument("--min-years", type=float, default=2.0, help="Anos mínimos para 'experienced'")
    parser.add_argument("--test-size", type=float, default=0.2, help="% para teste")
    parser.add_argument("--val-size", type=float, default=0.1, help="% para validação")
    parser.add_argument("--no-balance", action="store_true", help="Não balancear classes")
    parser.add_argument("--max-per-class", type=int, default=None, help="Máximo de amostras por classe")
    
    args = parser.parse_args()
    
    prepare_training_data(
        output_dir=args.output_dir,
        min_years_experienced=args.min_years,
        test_size=args.test_size,
        val_size=args.val_size,
        balance=not args.no_balance,
        max_samples_per_class=args.max_per_class
    )
