#!/usr/bin/env python3
"""
Testa sistema híbrido de scoring
"""
from app.scoring.hybrid_scorer import HybridScorer
from app.db.mongo import get_db
import random
import numpy as np


def main():
    print("=" * 80)
    print("🎯 TESTE DO SISTEMA HÍBRIDO DE SCORING")
    print("=" * 80)
    
    print("\n📦 Carregando scorer híbrido...")
    scorer = HybridScorer()
    
    print("\n📥 Carregando currículos...")
    db = get_db()
    resumes = list(db.dados_processados.find().limit(200))
    
    # Amostra estratificada
    random.seed(42)
    
    # Diferentes faixas de experiência
    by_years = {
        '0-2 anos': [],
        '3-10 anos': [],
        '11-20 anos': [],
        '20+ anos': []
    }
    
    for doc in resumes:
        years = doc.get('years_experience', 0) or 0
        if years < 3:
            by_years['0-2 anos'].append(doc)
        elif years <= 10:
            by_years['3-10 anos'].append(doc)
        elif years <= 20:
            by_years['11-20 anos'].append(doc)
        else:
            by_years['20+ anos'].append(doc)
    
    # Selecionar 5 de cada
    sample = []
    for group_name, docs in by_years.items():
        if docs:
            n = min(5, len(docs))
            sample.extend(random.sample(docs, n))
            print(f"   {group_name}: {n} currículos")
    
    random.shuffle(sample)
    
    print(f"\n🔬 Avaliando {len(sample)} currículos...\n")
    
    results = []
    for i, doc in enumerate(sample, 1):
        try:
            result = scorer.score(doc)
            
            years = doc.get('years_experience', 0) or 0
            skills = len(doc.get('skills', []))
            
            print(f"[{i:2d}] {years:.1f} anos, {skills} skills")
            print(f"     Híbrido: {result['score']}/100 ({result['label']})")
            print(f"     • ML: {result['components']['ml_score']} "
                  f"({result['components']['ml_label']}) × {result['components']['ml_weight']}")
            print(f"     • RB: {result['components']['rb_score']} "
                  f"({result['components']['rb_label']}) × {result['components']['rb_weight']}")
            
            if result['ml_metadata']['is_outlier']:
                print(f"     ⭐ Outlier excepcional!")
            
            # Top 2 subscores
            subscores = result['rb_subscores']
            top2 = sorted(subscores.items(), key=lambda x: x[1], reverse=True)[:2]
            if top2 and top2[0][1] > 0:
                print(f"     Top: {top2[0][0]}={top2[0][1]:.1f}, {top2[1][0]}={top2[1][1]:.1f}")
            
            results.append(result)
            
        except Exception as e:
            print(f"[{i:2d}] ❌ Erro: {e}")
            import traceback
            traceback.print_exc()
    
    # Estatísticas
    print("\n" + "=" * 80)
    print("📊 ESTATÍSTICAS DO SISTEMA HÍBRIDO")
    print("=" * 80)
    
    scores = [r['score'] for r in results]
    ml_scores = [r['components']['ml_score'] for r in results]
    rb_scores = [r['components']['rb_score'] for r in results]
    
    print(f"\nScores Híbridos:")
    print(f"   Média: {np.mean(scores):.1f}")
    print(f"   Mediana: {np.median(scores):.1f}")
    print(f"   Min-Max: {min(scores):.1f} - {max(scores):.1f}")
    print(f"   Desvio: {np.std(scores):.1f}")
    
    # Distribuição por label
    labels_count = {}
    for r in results:
        label = r['label']
        labels_count[label] = labels_count.get(label, 0) + 1
    
    print(f"\nDistribuição:")
    for label in ['Excelente', 'Bom', 'Regular', 'Fraco', 'Muito Fraco']:
        count = labels_count.get(label, 0)
        pct = count / len(results) * 100
        print(f"   {label}: {count} ({pct:.1f}%)")
    
    # Comparação com componentes
    print(f"\nComparação com Componentes:")
    print(f"   ML médio: {np.mean(ml_scores):.1f}")
    print(f"   RB médio: {np.mean(rb_scores):.1f}")
    print(f"   Diferença ML-RB: {np.mean(ml_scores) - np.mean(rb_scores):+.1f}")
    
    # Outliers detectados
    outliers = sum(1 for r in results if r['ml_metadata']['is_outlier'])
    print(f"\nOutliers excepcionais: {outliers} ({outliers/len(results)*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO!")
    print("\n💡 Sistema híbrido balanceia:")
    print("   • Padrões implícitos do ML (contexto do dataset)")
    print("   • Critérios explícitos do Rule-Based (lógica de negócio)")
    print("   • Ajusta pesos dinamicamente baseado em confiança")


if __name__ == '__main__':
    main()
