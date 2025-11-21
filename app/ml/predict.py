#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usa modelo treinado para fazer predições em novos currículos.
Suporta classificação híbrida (regras + ML) e ML puro.
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
from pymongo import MongoClient
from dotenv import load_dotenv


class ResumeClassifier:
    def __init__(self, model_path: str, device: str = None, use_hybrid: bool = True, 
                 years_threshold: float = 2.0, confidence_threshold: float = 0.85):
        """
        Carrega modelo treinado.
        
        Args:
            model_path: Caminho para o modelo salvo
            device: 'cuda' ou 'cpu' (None = auto)
            use_hybrid: Se True, usa estratégia híbrida (regras + ML)
            years_threshold: Limite de anos para considerar experiente (padrão: 2.0)
            confidence_threshold: Confiança mínima para usar só a regra (padrão: 0.85)
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.use_hybrid = use_hybrid
        self.years_threshold = years_threshold
        self.confidence_threshold = confidence_threshold
        
        print(f"📥 Carregando modelo de {model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
        
        mode = "HÍBRIDO (regras + ML)" if use_hybrid else "ML puro"
        print(f"✅ Modelo carregado (device={self.device}, modo={mode})")
        if use_hybrid:
            print(f"   Threshold de anos: {years_threshold}")
            print(f"   Threshold de confiança: {confidence_threshold}")
    
    def _predict_ml(self, text: str, return_probs: bool = False):
        """Predição usando apenas ML."""
    def _predict_ml(self, text: str, return_probs: bool = False):
        """Predição usando apenas ML."""
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
    
    def predict(self, text: str, years_experience: float = None, return_probs: bool = False, 
                return_details: bool = False):
        """
        Prediz se currículo é de pessoa experiente.
        
        Args:
            text: Texto do currículo
            years_experience: Anos de experiência (opcional, para modo híbrido)
            return_probs: Se True, retorna probabilidades
            return_details: Se True, retorna dict com detalhes (método usado, confiança, etc)
            
        Returns:
            Se return_probs=False e return_details=False: 0 ou 1 (not experienced / experienced)
            Se return_probs=True: (label, prob_noexp, prob_exp)
            Se return_details=True: dict completo com método, confiança, etc
        """
        # Obter predição ML
        ml_pred, ml_prob_noexp, ml_prob_exp = self._predict_ml(text, return_probs=True)
        ml_confidence = max(ml_prob_noexp, ml_prob_exp)
        
        # Se não está usando modo híbrido ou não tem years_experience, usar só ML
        if not self.use_hybrid or years_experience is None:
            if return_details:
                return {
                    "prediction": ml_pred,
                    "method": "ml_only",
                    "confidence": ml_confidence,
                    "prob_not_exp": ml_prob_noexp,
                    "prob_exp": ml_prob_exp,
                    "years_experience": years_experience,
                    "reason": "hybrid disabled" if not self.use_hybrid else "no years_experience data"
                }
            elif return_probs:
                return ml_pred, ml_prob_noexp, ml_prob_exp
            else:
                return ml_pred
        
        # Modo híbrido: usar regras + ML
        threshold = self.years_threshold
        
        # Casos claros (longe do threshold)
        if years_experience < threshold - 0.5:
            # Claramente não experiente
            result = {
                "prediction": 0,
                "method": "rule_based",
                "confidence": 1.0,
                "prob_not_exp": 1.0,
                "prob_exp": 0.0,
                "years_experience": years_experience,
                "ml_prediction": ml_pred,
                "ml_confidence": ml_confidence,
                "reason": f"years < {threshold - 0.5}"
            }
        elif years_experience >= threshold + 0.5:
            # Claramente experiente
            result = {
                "prediction": 1,
                "method": "rule_based",
                "confidence": 1.0,
                "prob_not_exp": 0.0,
                "prob_exp": 1.0,
                "years_experience": years_experience,
                "ml_prediction": ml_pred,
                "ml_confidence": ml_confidence,
                "reason": f"years >= {threshold + 0.5}"
            }
        else:
            # Caso borderline (entre 1.5 e 2.5 anos)
            rule_pred = 1 if years_experience >= threshold else 0
            
            if ml_confidence < self.confidence_threshold:
                # ML incerto, usar regra
                result = {
                    "prediction": rule_pred,
                    "method": "rule_based_borderline",
                    "confidence": 0.90,
                    "prob_not_exp": 1.0 - 0.90 if rule_pred == 0 else 0.10,
                    "prob_exp": 0.90 if rule_pred == 1 else 0.10,
                    "years_experience": years_experience,
                    "ml_prediction": ml_pred,
                    "ml_confidence": ml_confidence,
                    "reason": f"borderline, ML uncertain (conf={ml_confidence:.3f})"
                }
            else:
                # ML confiante
                if rule_pred == ml_pred:
                    # Acordo entre regra e ML
                    result = {
                        "prediction": rule_pred,
                        "method": "consensus",
                        "confidence": 0.95,
                        "prob_not_exp": ml_prob_noexp if rule_pred == 0 else 1.0 - 0.95,
                        "prob_exp": ml_prob_exp if rule_pred == 1 else 1.0 - 0.95,
                        "years_experience": years_experience,
                        "ml_prediction": ml_pred,
                        "ml_confidence": ml_confidence,
                        "reason": "rule and ML agree"
                    }
                else:
                    # Discordância - usar regra (mais confiável)
                    result = {
                        "prediction": rule_pred,
                        "method": "rule_override",
                        "confidence": 0.85,
                        "prob_not_exp": 0.85 if rule_pred == 0 else 0.15,
                        "prob_exp": 0.85 if rule_pred == 1 else 0.15,
                        "years_experience": years_experience,
                        "ml_prediction": ml_pred,
                        "ml_confidence": ml_confidence,
                        "reason": "rule overrides ML disagreement"
                    }
        
        if return_details:
            return result
        elif return_probs:
            return result["prediction"], result["prob_not_exp"], result["prob_exp"]
        else:
            return result["prediction"]
    
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


def predict_from_mongodb(model_path: str, doc_id: str = None, limit: int = 10, use_hybrid: bool = True):
    """
    Testa modelo em documentos do MongoDB.
    
    Args:
        model_path: Caminho do modelo treinado
        doc_id: ID específico do documento (opcional)
        limit: Quantidade de documentos para testar (se doc_id não fornecido)
        use_hybrid: Se True, usa classificação híbrida (regras + ML)
    """
    load_dotenv()
    
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "resumAI")
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    collection = db["dados_processados"]
    
    # Carregar modelo
    classifier = ResumeClassifier(model_path, use_hybrid=use_hybrid)
    
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
    
    mode = "HÍBRIDO" if use_hybrid else "ML PURO"
    print(f"\n🔍 Testando modelo ({mode}) em {len(docs)} documento(s)...\n")
    print("=" * 120)
    
    correct = 0
    total = 0
    
    for doc in docs:
        text = doc.get("resume_text_clean", "")
        years_real = doc.get("years_experience", 0.0)
        filename = doc.get("filename", "N/A")
        
        result = classifier.predict(text, years_experience=years_real, return_details=True)
        
        pred = result["prediction"]
        method = result["method"]
        confidence = result["confidence"]
        prob_noexp = result["prob_not_exp"]
        prob_exp = result["prob_exp"]
        
        label = "EXPERIENCED" if pred == 1 else "NOT EXPERIENCED"
        real_label = "EXPERIENCED" if years_real >= 2.0 else "NOT EXPERIENCED"
        
        match = "✅" if label == real_label else "❌"
        
        if label == real_label:
            correct += 1
        total += 1
        
        print(f"{match} Arquivo: {filename}")
        print(f"   Anos reais: {years_real:.1f} anos → {real_label}")
        print(f"   Predição: {label} (método: {method})")
        print(f"   Confiança: {confidence:.3f} | Not Exp={prob_noexp:.3f} | Exp={prob_exp:.3f}")
        print("-" * 120)
    
    accuracy = (correct / total * 100) if total > 0 else 0
    print(f"\n📊 Accuracy: {correct}/{total} = {accuracy:.1f}%")
    print("=" * 120)
    
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
    parser.add_argument("--no-hybrid", action="store_true", help="Desabilitar modo híbrido (usar só ML)")
    parser.add_argument("--years", type=float, help="Anos de experiência (para modo híbrido)")
    
    args = parser.parse_args()
    
    use_hybrid = not args.no_hybrid
    
    if args.from_db:
        predict_from_mongodb(args.model, doc_id=args.doc_id, limit=args.limit, use_hybrid=use_hybrid)
    else:
        classifier = ResumeClassifier(args.model, use_hybrid=use_hybrid)
        
        if args.text:
            text = args.text
        elif args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            raise ValueError("Forneça --text, --file ou --from-db")
        
        result = classifier.predict(text, years_experience=args.years, return_details=True)
        
        label = "EXPERIENCED" if result["prediction"] == 1 else "NOT EXPERIENCED"
        print(f"\n🎯 Predição: {label}")
        print(f"   Método: {result['method']}")
        print(f"   Confiança: {result['confidence']:.4f}")
        print(f"   Probabilidade Not Experienced: {result['prob_not_exp']:.4f}")
        print(f"   Probabilidade Experienced: {result['prob_exp']:.4f}")
        if result.get('years_experience') is not None:
            print(f"   Anos de experiência: {result['years_experience']:.1f}")
        if result.get('ml_prediction') is not None:
            ml_label = "EXPERIENCED" if result['ml_prediction'] == 1 else "NOT EXPERIENCED"
            print(f"   Predição ML: {ml_label} (conf={result['ml_confidence']:.4f})")
        print(f"   Razão: {result['reason']}")
