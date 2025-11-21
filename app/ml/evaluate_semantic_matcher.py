#!/usr/bin/env python3
"""
Avalia modelo de matching semântico com métricas detalhadas
"""
import sys
import json
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import pearsonr, spearmanr

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sentence_transformers import SentenceTransformer, util


def evaluate_model(model_path: str, test_data_path: str):
    """Avalia modelo com métricas detalhadas"""
    
    print("=" * 80)
    print("📊 AVALIAÇÃO DE MODELO DE MATCHING SEMÂNTICO")
    print("=" * 80)
    
    # Carrega modelo
    print(f"\n📥 Carregando modelo de {model_path}...")
    model = SentenceTransformer(model_path)
    print("✅ Modelo carregado")
    
    # Carrega dados de teste
    print(f"\n📂 Carregando dados de teste...")
    with open(test_data_path, 'r', encoding='utf-8') as f:
        test_pairs = json.load(f)
    
    # Filtra apenas pares com anotação
    test_pairs = [p for p in test_pairs if p.get('match_score') is not None]
    print(f"✅ {len(test_pairs)} pares anotados")
    
    # Calcula predições
    print(f"\n🔮 Calculando predições...")
    true_scores = []
    pred_scores = []
    
    for i, pair in enumerate(test_pairs):
        if (i + 1) % 100 == 0:
            print(f"   Processado {i+1}/{len(test_pairs)}...")
        
        resume_emb = model.encode(pair['resume_text'], convert_to_tensor=True)
        job_emb = model.encode(pair['job_description'], convert_to_tensor=True)
        
        similarity = float(util.cos_sim(resume_emb, job_emb)[0][0])
        
        true_scores.append(pair['match_score'])
        pred_scores.append(similarity)
    
    true_scores = np.array(true_scores)
    pred_scores = np.array(pred_scores)
    
    # Métricas de regressão
    print(f"\n📈 MÉTRICAS DE REGRESSÃO:")
    mae = mean_absolute_error(true_scores, pred_scores)
    mse = mean_squared_error(true_scores, pred_scores)
    rmse = np.sqrt(mse)
    r2 = r2_score(true_scores, pred_scores)
    
    print(f"   MAE (Mean Absolute Error): {mae:.4f}")
    print(f"   RMSE (Root Mean Squared Error): {rmse:.4f}")
    print(f"   R² Score: {r2:.4f}")
    
    # Correlações
    print(f"\n🔗 CORRELAÇÕES:")
    pearson_corr, pearson_p = pearsonr(true_scores, pred_scores)
    spearman_corr, spearman_p = spearmanr(true_scores, pred_scores)
    
    print(f"   Pearson: {pearson_corr:.4f} (p-value: {pearson_p:.4e})")
    print(f"   Spearman: {spearman_corr:.4f} (p-value: {spearman_p:.4e})")
    
    # Análise por faixas de score
    print(f"\n📊 ANÁLISE POR FAIXAS:")
    bins = [(0.0, 0.2, 'none'), (0.2, 0.4, 'poor'), (0.4, 0.6, 'fair'), 
            (0.6, 0.8, 'good'), (0.8, 1.0, 'excellent')]
    
    for min_score, max_score, label in bins:
        mask = (true_scores >= min_score) & (true_scores < max_score)
        if mask.sum() > 0:
            bin_mae = mean_absolute_error(true_scores[mask], pred_scores[mask])
            count = mask.sum()
            print(f"   {label:10s} [{min_score:.1f}-{max_score:.1f}]: "
                  f"{count:4d} pares | MAE: {bin_mae:.4f}")
    
    # Piores predições
    print(f"\n❌ TOP 5 PIORES PREDIÇÕES:")
    errors = np.abs(true_scores - pred_scores)
    worst_indices = np.argsort(errors)[-5:][::-1]
    
    for rank, idx in enumerate(worst_indices, 1):
        pair = test_pairs[idx]
        print(f"\n[{rank}] Erro: {errors[idx]:.3f}")
        print(f"    Currículo: {pair['resume_filename']}")
        print(f"    Vaga: {pair['job_title']}")
        print(f"    Score Real: {true_scores[idx]:.3f} | Predito: {pred_scores[idx]:.3f}")
        print(f"    Skills resumo: {', '.join(pair.get('resume_skills', [])[:5])}")
        print(f"    Skills vaga: {', '.join(pair.get('job_required_skills', []))}")
    
    # Melhores predições
    print(f"\n✅ TOP 5 MELHORES PREDIÇÕES:")
    best_indices = np.argsort(errors)[:5]
    
    for rank, idx in enumerate(best_indices, 1):
        pair = test_pairs[idx]
        print(f"\n[{rank}] Erro: {errors[idx]:.3f}")
        print(f"    Currículo: {pair['resume_filename']}")
        print(f"    Vaga: {pair['job_title']}")
        print(f"    Score Real: {true_scores[idx]:.3f} | Predito: {pred_scores[idx]:.3f}")
    
    # Distribuição de erros
    print(f"\n📊 DISTRIBUIÇÃO DE ERROS:")
    print(f"   Erro < 0.05: {(errors < 0.05).sum()} ({(errors < 0.05).mean()*100:.1f}%)")
    print(f"   Erro < 0.10: {(errors < 0.10).sum()} ({(errors < 0.10).mean()*100:.1f}%)")
    print(f"   Erro < 0.15: {(errors < 0.15).sum()} ({(errors < 0.15).mean()*100:.1f}%)")
    print(f"   Erro < 0.20: {(errors < 0.20).sum()} ({(errors < 0.20).mean()*100:.1f}%)")
    print(f"   Erro >= 0.20: {(errors >= 0.20).sum()} ({(errors >= 0.20).mean()*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ AVALIAÇÃO CONCLUÍDA!")
    print("=" * 80)
    
    # Retorna métricas principais
    return {
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'pearson': pearson_corr,
        'spearman': spearman_corr
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='models/semantic_matcher_finetuned',
                      help='Caminho do modelo')
    parser.add_argument('--data', type=str, default='data/matching_pairs_annotated.json',
                      help='Dados de teste')
    
    args = parser.parse_args()
    
    metrics = evaluate_model(args.model, args.data)
