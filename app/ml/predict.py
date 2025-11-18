#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usa modelo treinado para fazer predições em novos currículos.
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
from pymongo import MongoClient
from dotenv import load_dotenv


class ResumeClassifier:
    def __init__(self, model_path: str, device: str = None):
        """
        Carrega modelo treinado.
        
        Args:
            model_path: Caminho para o modelo salvo
            device: 'cuda' ou 'cpu' (None = auto)
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        print(f"📥 Carregando modelo de {model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        print(f"✅ Modelo carregado (device={self.device})")
    
    def predict(self, text: str, return_probs: bool = False):
        """
        Prediz se currículo é de pessoa experiente.
        
        Args:
            text: Texto do currículo
            return_probs: Se True, retorna probabilidades
            
        Returns:
            Se return_probs=False: 0 ou 1 (not experienced / experienced)
            Se return_probs=True: (label, prob_noexp, prob_exp)
        """
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            pred = torch.argmax(logits, dim=-1).item()
        
        if return_probs:
            prob_noexp = probs[0][0].item()
            prob_exp = probs[0][1].item()
            return pred, prob_noexp, prob_exp
        
        return pred
    
    def predict_batch(self, texts: list, batch_size: int = 16):
        """
        Prediz em lote.
        
        Args:
            texts: Lista de textos de currículos
            batch_size: Tamanho do batch
            
        Returns:
            Lista de predições (0 ou 1)
        """
        predictions = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                preds = torch.argmax(logits, dim=-1).cpu().numpy()
                predictions.extend(preds.tolist())
        
        return predictions


def predict_from_mongodb(model_path: str, doc_id: str = None, limit: int = 10):
    """
    Testa modelo em documentos do MongoDB.
    
    Args:
        model_path: Caminho do modelo treinado
        doc_id: ID específico do documento (opcional)
        limit: Quantidade de documentos para testar (se doc_id não fornecido)
    """
    load_dotenv()
    
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "resumAI")
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db["dados_processados"]
    
    # Carregar modelo
    classifier = ResumeClassifier(model_path)
    
    # Buscar documentos
    if doc_id:
        from bson import ObjectId
        docs = [collection.find_one({"_id": ObjectId(doc_id)})]
        if not docs[0]:
            print(f"❌ Documento {doc_id} não encontrado")
            return
    else:
        docs = list(collection.find(
            {"resume_text_clean": {"$exists": True, "$ne": ""}},
            {"_id": 1, "resume_text_clean": 1, "years_experience": 1, "filename": 1}
        ).limit(limit))
    
    print(f"\n🔍 Testando modelo em {len(docs)} documento(s)...\n")
    print("=" * 100)
    
    for doc in docs:
        text = doc.get("resume_text_clean", "")
        years_real = doc.get("years_experience", 0.0)
        filename = doc.get("filename", "N/A")
        
        pred, prob_noexp, prob_exp = classifier.predict(text, return_probs=True)
        
        label = "EXPERIENCED" if pred == 1 else "NOT EXPERIENCED"
        real_label = "EXPERIENCED" if years_real >= 2.0 else "NOT EXPERIENCED"
        
        match = "✅" if label == real_label else "❌"
        
        print(f"{match} Arquivo: {filename}")
        print(f"   Anos reais: {years_real:.1f} anos → {real_label}")
        print(f"   Predição: {label}")
        print(f"   Confiança: Not Exp={prob_noexp:.3f} | Exp={prob_exp:.3f}")
        print("-" * 100)
    
    client.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Faz predições com modelo treinado")
    parser.add_argument("--model", required=True, help="Caminho do modelo")
    parser.add_argument("--text", help="Texto para classificar")
    parser.add_argument("--file", help="Arquivo com texto")
    parser.add_argument("--from-db", action="store_true", help="Testar com docs do MongoDB")
    parser.add_argument("--doc-id", help="ID específico do documento no MongoDB")
    parser.add_argument("--limit", type=int, default=10, help="Limite de docs do MongoDB")
    
    args = parser.parse_args()
    
    if args.from_db:
        predict_from_mongodb(args.model, doc_id=args.doc_id, limit=args.limit)
    else:
        classifier = ResumeClassifier(args.model)
        
        if args.text:
            text = args.text
        elif args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            raise ValueError("Forneça --text, --file ou --from-db")
        
        pred, prob_noexp, prob_exp = classifier.predict(text, return_probs=True)
        
        label = "EXPERIENCED" if pred == 1 else "NOT EXPERIENCED"
        print(f"\n🎯 Predição: {label}")
        print(f"   Probabilidade Not Experienced: {prob_noexp:.4f}")
        print(f"   Probabilidade Experienced: {prob_exp:.4f}")
