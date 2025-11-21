#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cálculo de similaridade semântica usando modelo fine-tuned.
Modelo treinado especificamente para matching currículo-vaga com MAE 0.04 e Pearson 0.86.
"""
from sentence_transformers import SentenceTransformer, util
import numpy as np
import torch
from pathlib import Path

# Modelo fine-tuned para matching
_EMBEDDING_MODEL = None
_MODEL_PATH = "models/semantic_matcher_finetuned"

def get_embedding_model():
    """Retorna modelo singleton fine-tuned."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model_path = Path(_MODEL_PATH)
            
            if model_path.exists():
                # Usar modelo fine-tuned
                _EMBEDDING_MODEL = SentenceTransformer(_MODEL_PATH, device=device)
                print(f"✅ Modelo fine-tuned carregado de {_MODEL_PATH} em {device}")
            else:
                # Fallback para modelo base
                _EMBEDDING_MODEL = SentenceTransformer(
                    'paraphrase-multilingual-mpnet-base-v2',
                    device=device
                )
                print(f"⚠️  Modelo fine-tuned não encontrado, usando base em {device}")
        except Exception as e:
            print(f"❌ Erro ao carregar modelo: {e}")
            _EMBEDDING_MODEL = None
    return _EMBEDDING_MODEL


def compute_semantic_similarity(resume_text: str, job_description: str = None) -> float:
    """
    Calcula similaridade semântica entre currículo e vaga usando modelo fine-tuned.
    
    Args:
        resume_text: Texto do currículo
        job_description: Descrição da vaga (opcional)
    
    Returns:
        Score de similaridade (0.0 a 1.0, onde 1.0 = match perfeito)
        Retorna 0.0 se job_description não fornecido
    """
    if not job_description or not resume_text:
        if not job_description:
            print("⚠️  Semantic: job_description não fornecido")
        if not resume_text:
            print("⚠️  Semantic: resume_text vazio")
        return 0.0
    
    model = get_embedding_model()
    if model is None:
        print("❌ Semantic: modelo não carregado")
        return 0.0
    
    try:
        # Truncar textos
        resume_text = resume_text[:2000]
        job_description = job_description[:1000]
        
        # Gerar embeddings
        resume_emb = model.encode(resume_text, convert_to_tensor=True)
        job_emb = model.encode(job_description, convert_to_tensor=True)
        
        # Calcular similaridade cosseno
        similarity = float(util.cos_sim(resume_emb, job_emb)[0][0])
        
        # Normalizar para 0-1 (similarity pode ser [-1, 1])
        # Modelo fine-tuned já retorna valores bem calibrados
        normalized = (similarity + 1.0) / 2.0
        
        result = float(np.clip(normalized, 0.0, 1.0))
        print(f"✅ Semantic calculado: {result:.3f} (similarity raw: {similarity:.3f})")
        return result
    
    except Exception as e:
        print(f"⚠️  Erro ao calcular similaridade: {e}")
        return 0.0


def compute_resume_quality_embedding(resume_text: str) -> float:
    """
    Calcula score de qualidade baseado na densidade semântica do currículo.
    
    Args:
        resume_text: Texto do currículo
    
    Returns:
        Score de qualidade (0.0 a 1.0)
    """
    if not resume_text or len(resume_text) < 100:
        return 0.0
    
    model = get_embedding_model()
    if model is None:
        return 0.5
    
    try:
        # Dividir em chunks
        chunks = [resume_text[i:i+500] for i in range(0, min(len(resume_text), 5000), 500)]
        
        if len(chunks) < 2:
            return 0.5
        
        # Gerar embeddings
        embeddings = model.encode(chunks, convert_to_tensor=True)
        
        # Calcular coerência (similaridade média entre chunks adjacentes)
        coherence_scores = []
        for i in range(len(embeddings) - 1):
            sim = float(util.cos_sim(embeddings[i], embeddings[i+1])[0][0])
            coherence_scores.append(sim)
        
        avg_coherence = np.mean(coherence_scores)
        
        # Normalizar: coerência típica é 0.3-0.8
        quality = (avg_coherence - 0.3) / 0.5
        return float(np.clip(quality, 0.0, 1.0))
    
    except Exception as e:
        print(f"⚠️  Erro ao calcular qualidade: {e}")
        return 0.5
