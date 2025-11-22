#!/usr/bin/env python3
"""
Sistema Híbrido de Scoring: Combina ML Não-Supervisionado + Rule-Based
"""
from typing import Dict, Tuple
import numpy as np
from pathlib import Path

from app.ml.unsupervised_scoring import UnsupervisedResumeScorer, extract_features_array
from app.scoring.use_case import evaluate_resume_from_doc


class HybridScorer:
    """
    Combina dois sistemas de scoring:
    1. ML Não-Supervisionado (aprende padrões do dataset)
    2. Rule-Based (lógica de negócio explícita)
    
    Estratégia:
    - 50% ML (padrões implícitos)
    - 50% Rule-Based (critérios explícitos)
    - Ajusta pesos baseado em confiança
    """
    
    def __init__(self, model_path: str = 'models/unsupervised_scorer.pkl'):
        """
        Args:
            model_path: Caminho para modelo ML treinado
        """
        self.ml_scorer = UnsupervisedResumeScorer.load(model_path)
        self.ml_weight = 0.5
        self.rb_weight = 0.5
        
    def score(self, doc: dict) -> Dict:
        """
        Avalia currículo com sistema híbrido
        
        Args:
            doc: Documento do currículo
        
        Returns:
            Dict com scores, metadata e explicação
        """
        # 1. ML Score
        features = extract_features_array(doc)
        ml_score, ml_meta = self.ml_scorer.predict_score(features)
        
        # 2. Rule-Based Score
        rb_result = evaluate_resume_from_doc(doc)
        rb_score = rb_result['scores']['final']
        rb_subscores = rb_result['scores']['by_block']
        
        # 3. Ajustar pesos baseado em confiança
        # Se currículo é outlier (excepcional), dar mais peso ao ML
        # Se currículo tem muitos subscores, dar mais peso ao rule-based
        adjusted_ml_weight = self.ml_weight
        adjusted_rb_weight = self.rb_weight
        
        if ml_meta.get('is_outlier', False):
            # Outlier excepcional - ML captura melhor
            adjusted_ml_weight = 0.7
            adjusted_rb_weight = 0.3
        
        subscore_count = sum(1 for v in rb_subscores.values() if v > 0)
        if subscore_count >= 6:
            # Currículo completo - Rule-based mais confiável
            adjusted_rb_weight = 0.6
            adjusted_ml_weight = 0.4
        
        # Normalizar pesos
        total_weight = adjusted_ml_weight + adjusted_rb_weight
        adjusted_ml_weight /= total_weight
        adjusted_rb_weight /= total_weight
        
        # 4. Score híbrido
        hybrid_score = (ml_score * adjusted_ml_weight + 
                       rb_score * adjusted_rb_weight)
        
        # 5. Label: BOM ou RUIM (critério baseado no perfil)
        # Estagiários (sem experiência): >= 40 = BOM
        # Experientes: >= 50 = BOM
        has_experience = doc.get('has_experience', False)
        if has_experience:
            # Profissional: critério mais rigoroso
            label = "Bom" if hybrid_score >= 50 else "Ruim"
        else:
            # Estagiário/Júnior: critério mais leve
            label = "Bom" if hybrid_score >= 40 else "Ruim"
        
        # 6. Explicação
        explanation = self._generate_explanation(
            ml_score, ml_meta, rb_score, rb_subscores,
            adjusted_ml_weight, adjusted_rb_weight
        )
        
        return {
            'score': round(hybrid_score, 1),
            'label': label,
            'components': {
                'ml_score': round(ml_score, 1),
                'ml_label': ml_meta['label'],
                'ml_weight': round(adjusted_ml_weight, 2),
                'rb_score': round(rb_score, 1),
                'rb_label': rb_result['scores']['label'],
                'rb_weight': round(adjusted_rb_weight, 2)
            },
            'ml_metadata': {
                'cluster_id': ml_meta['cluster_id'],
                'cluster_quality': round(ml_meta['cluster_quality'], 3),
                'is_outlier': ml_meta['is_outlier']
            },
            'rb_subscores': {k: round(v, 1) for k, v in rb_subscores.items()},
            'explanation': explanation,
            'features': rb_result['features']
        }
    
    def _generate_explanation(
        self,
        ml_score: float,
        ml_meta: Dict,
        rb_score: float,
        rb_subscores: Dict,
        ml_weight: float,
        rb_weight: float
    ) -> str:
        """Gera explicação textual do score"""
        
        # Top 3 subscores
        top_subscores = sorted(rb_subscores.items(), key=lambda x: x[1], reverse=True)[:3]
        top_names = {
            'skills': 'Habilidades',
            'experience': 'Experiência',
            'projects': 'Projetos',
            'certs': 'Certificações',
            'impact': 'Impacto',
            'semantic': 'Similaridade',
            'doc_quality': 'Qualidade',
            'contact': 'Contato',
            'context': 'Contexto'
        }
        
        explanation_parts = []
        
        # Componentes do score
        explanation_parts.append(
            f"Score híbrido calculado com {ml_weight*100:.0f}% ML + {rb_weight*100:.0f}% Rule-Based"
        )
        
        # ML insights
        cluster_quality = ml_meta['cluster_quality']
        if ml_meta['is_outlier']:
            explanation_parts.append(
                f"✨ Perfil excepcional detectado (cluster {ml_meta['cluster_id']})"
            )
        else:
            explanation_parts.append(
                f"Pertence ao cluster {ml_meta['cluster_id']} (qualidade: {cluster_quality:.2f})"
            )
        
        # Top subscores
        if top_subscores:
            top_str = ', '.join([
                f"{top_names.get(name, name)}: {value:.1f}"
                for name, value in top_subscores if value > 0
            ])
            if top_str:
                explanation_parts.append(f"Destaques: {top_str}")
        
        # Diferença ML vs RB
        diff = ml_score - rb_score
        if abs(diff) > 15:
            if diff > 0:
                explanation_parts.append(
                    f"ML detectou padrões positivos (+{diff:.0f} pontos vs rules)"
                )
            else:
                explanation_parts.append(
                    f"Rules identificaram gaps ({diff:.0f} pontos vs ML)"
                )
        
        return '. '.join(explanation_parts) + '.'


def main():
    """Exemplo de uso"""
    from app.db.mongo import get_db
    import random
    
    print("🎯 SISTEMA HÍBRIDO DE SCORING")
    print("="*80)
    
    scorer = HybridScorer()
    
    # Carregar amostra
    db = get_db()
    resumes = list(db.dados_processados.find().limit(100))
    sample = random.sample(resumes, 5)
    
    for i, doc in enumerate(sample, 1):
        result = scorer.score(doc)
        
        years = doc.get('years_experience', 0) or 0
        skills = len(doc.get('skills', []))
        
        print(f"\n[{i}] Currículo: {years:.1f} anos, {skills} skills")
        print(f"    Score: {result['score']}/100 ({result['label']})")
        print(f"    • ML: {result['components']['ml_score']} "
              f"({result['components']['ml_label']}) - "
              f"peso {result['components']['ml_weight']}")
        print(f"    • RB: {result['components']['rb_score']} "
              f"({result['components']['rb_label']}) - "
              f"peso {result['components']['rb_weight']}")
        print(f"    📝 {result['explanation']}")


if __name__ == '__main__':
    main()
