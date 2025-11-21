#!/usr/bin/env python3
"""
Sistema de Scoring Não-Supervisionado
Usa clustering e análise de componentes principais para avaliar currículos
sem necessidade de anotações humanas.
"""
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
import joblib
from pathlib import Path
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class UnsupervisedResumeScorer:
    """
    Avaliador não-supervisionado de currículos
    
    Estratégia:
    1. Normalizar features extraídas
    2. Reduzir dimensionalidade com PCA
    3. Clustering (K-Means) para identificar grupos
    4. Anomaly detection para identificar outliers
    5. Score baseado em:
       - Distância ao cluster "melhor"
       - Densidade local (quão comum é o perfil)
       - Anomaly score (quão excepcional é)
    """
    
    def __init__(self, n_clusters: int = 5, n_components: int = 8):
        """
        Args:
            n_clusters: Número de clusters (grupos de currículos)
            n_components: Dimensões do PCA (redução de dimensionalidade)
        """
        self.n_clusters = n_clusters
        self.n_components = n_components
        
        # Modelos
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components)
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        
        # Metadados do treinamento
        self.feature_names = None
        self.cluster_profiles = None  # Perfil médio de cada cluster
        self.cluster_quality_scores = None  # Score de qualidade de cada cluster
        self.fitted = False
        
    def fit(self, features: np.ndarray, feature_names: List[str]):
        """
        Treina o modelo não-supervisionado
        
        Args:
            features: Array (n_samples, n_features)
            feature_names: Lista de nomes das features
        """
        print(f"🔄 Treinando modelo não-supervisionado...")
        print(f"   Dataset: {features.shape[0]} currículos, {features.shape[1]} features")
        
        self.feature_names = feature_names
        
        # 1. Normalização
        print(f"   [1/5] Normalizando features...")
        X_scaled = self.scaler.fit_transform(features)
        
        # 2. PCA - Redução de dimensionalidade
        print(f"   [2/5] Aplicando PCA ({self.n_components} componentes)...")
        X_pca = self.pca.fit_transform(X_scaled)
        variance_explained = self.pca.explained_variance_ratio_.sum()
        print(f"         Variância explicada: {variance_explained*100:.1f}%")
        
        # 3. Clustering
        print(f"   [3/5] Clustering com K-Means ({self.n_clusters} clusters)...")
        self.kmeans.fit(X_pca)
        labels = self.kmeans.labels_
        silhouette = silhouette_score(X_pca, labels)
        print(f"         Silhouette Score: {silhouette:.3f}")
        
        # 4. Anomaly Detection
        print(f"   [4/5] Treinando Isolation Forest...")
        self.isolation_forest.fit(X_pca)
        
        # 5. Analisar perfis dos clusters
        print(f"   [5/5] Analisando perfis dos clusters...")
        self.cluster_profiles = self._analyze_cluster_profiles(features, labels)
        self.cluster_quality_scores = self._rank_clusters_by_quality(self.cluster_profiles)
        
        self.fitted = True
        print(f"✅ Modelo treinado com sucesso!\n")
        
        self._print_cluster_summary()
        
        return self
    
    def _analyze_cluster_profiles(self, features: np.ndarray, labels: np.ndarray) -> List[Dict]:
        """Analisa o perfil médio de cada cluster"""
        profiles = []
        
        for cluster_id in range(self.n_clusters):
            mask = labels == cluster_id
            cluster_features = features[mask]
            
            profile = {
                'cluster_id': cluster_id,
                'size': int(mask.sum()),
                'percentage': float(mask.sum() / len(labels) * 100),
                'mean_features': {
                    name: float(cluster_features[:, i].mean())
                    for i, name in enumerate(self.feature_names)
                },
                'std_features': {
                    name: float(cluster_features[:, i].std())
                    for i, name in enumerate(self.feature_names)
                }
            }
            profiles.append(profile)
        
        return profiles
    
    def _rank_clusters_by_quality(self, profiles: List[Dict]) -> Dict[int, float]:
        """
        Rank clusters por qualidade baseado em features importantes
        
        Critérios (pesos):
        - skills_count: 30%
        - years_experience: 25%
        - metrics_hits: 20%
        - projects_hits: 10%
        - cert_points: 10%
        - doc_quality: 5%
        """
        weights = {
            'skills_count': 0.30,
            'years_experience': 0.25,
            'metrics_count': 0.20,
            'projects_count': 0.10,
            'cert_count': 0.10,
            'doc_quality': 0.05
        }
        
        quality_scores = {}
        
        for profile in profiles:
            cluster_id = profile['cluster_id']
            mean_features = profile['mean_features']
            
            # Calcular score ponderado
            score = 0
            for feature_name, weight in weights.items():
                if feature_name in mean_features:
                    # Normalizar feature (assumindo ranges típicos)
                    feature_value = mean_features[feature_name]
                    
                    if feature_name == 'skills_count':
                        normalized = min(feature_value / 20, 1.0)  # 20+ skills = 100%
                    elif feature_name == 'years_experience':
                        normalized = min(feature_value / 15, 1.0)  # 15+ anos = 100%
                    elif feature_name == 'metrics_count':
                        normalized = min(feature_value / 10, 1.0)  # 10+ metrics = 100%
                    elif feature_name == 'projects_count':
                        normalized = min(feature_value / 5, 1.0)   # 5+ projects = 100%
                    elif feature_name == 'cert_count':
                        normalized = min(feature_value / 3, 1.0) # 3+ certs = 100%
                    elif feature_name == 'doc_quality':
                        normalized = feature_value  # Já normalizado 0-1
                    else:
                        normalized = feature_value
                    
                    score += normalized * weight
            
            quality_scores[cluster_id] = score
        
        return quality_scores
    
    def _print_cluster_summary(self):
        """Imprime resumo dos clusters identificados"""
        print("=" * 80)
        print("📊 CLUSTERS IDENTIFICADOS")
        print("=" * 80)
        
        # Ordenar por qualidade
        sorted_clusters = sorted(
            self.cluster_profiles,
            key=lambda x: self.cluster_quality_scores[x['cluster_id']],
            reverse=True
        )
        
        quality_labels = ['🌟 Excelente', '✨ Muito Bom', '👍 Bom', '📊 Regular', '📉 Básico']
        
        for idx, profile in enumerate(sorted_clusters):
            cluster_id = profile['cluster_id']
            quality = self.cluster_quality_scores[cluster_id]
            label = quality_labels[idx] if idx < len(quality_labels) else '❓'
            
            print(f"\n{label} - Cluster {cluster_id}")
            print(f"   Tamanho: {profile['size']} currículos ({profile['percentage']:.1f}%)")
            print(f"   Score de Qualidade: {quality:.3f}")
            print(f"   Perfil médio:")
            
            # Mostrar top 5 features
            mean_features = profile['mean_features']
            top_features = sorted(mean_features.items(), key=lambda x: x[1], reverse=True)[:5]
            for fname, fvalue in top_features:
                print(f"     • {fname}: {fvalue:.2f}")
        
        print("\n" + "=" * 80)
    
    def predict_score(self, features: np.ndarray) -> Tuple[float, Dict]:
        """
        Prediz score para um currículo
        
        Args:
            features: Array (n_features,) ou (1, n_features)
        
        Returns:
            score: Float 0-100
            metadata: Dict com informações adicionais
        """
        if not self.fitted:
            raise ValueError("Modelo não treinado! Chame .fit() primeiro.")
        
        # Garantir shape correto
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        
        # 1. Normalizar
        X_scaled = self.scaler.transform(features)
        
        # 2. PCA
        X_pca = self.pca.transform(X_scaled)
        
        # 3. Predizer cluster
        cluster_id = self.kmeans.predict(X_pca)[0]
        
        # 4. Calcular distâncias
        distances = self.kmeans.transform(X_pca)[0]
        distance_to_assigned = distances[cluster_id]
        min_distance = distances.min()
        
        # 5. Anomaly score
        anomaly_score = self.isolation_forest.score_samples(X_pca)[0]
        # Normalizar: -0.5 (normal) a 0.5 (anômalo) → 0 a 1
        anomaly_normalized = (anomaly_score + 0.5)
        
        # 6. Calcular score final
        # Componentes:
        # - 50%: Qualidade do cluster atribuído
        # - 30%: Quão próximo está do centróide (densidade)
        # - 20%: Quão excepcional é (anomaly - valores altos = excepcional)
        
        cluster_quality = self.cluster_quality_scores[cluster_id]
        
        # Proximidade ao centróide (inverso da distância, normalizado)
        # Distância típica ~2-5, então normalizamos
        proximity_score = max(0, 1 - (distance_to_assigned / 5.0))
        
        # Score final (0-100)
        base_score = cluster_quality * 100  # 0-100
        proximity_bonus = proximity_score * 20  # até +20
        anomaly_bonus = max(0, anomaly_normalized) * 10  # até +10 se excepcional
        
        final_score = base_score + proximity_bonus + anomaly_bonus
        final_score = max(0, min(100, final_score))  # Clip 0-100
        
        # Label
        if final_score >= 80:
            label = "Excelente"
        elif final_score >= 65:
            label = "Bom"
        elif final_score >= 50:
            label = "Regular"
        elif final_score >= 35:
            label = "Fraco"
        else:
            label = "Muito Fraco"
        
        metadata = {
            'cluster_id': int(cluster_id),
            'cluster_quality': float(cluster_quality),
            'cluster_size': self.cluster_profiles[cluster_id]['size'],
            'distance_to_centroid': float(distance_to_assigned),
            'proximity_score': float(proximity_score),
            'anomaly_score': float(anomaly_normalized),
            'is_outlier': bool(anomaly_normalized > 0.6),
            'score_components': {
                'base': float(base_score),
                'proximity_bonus': float(proximity_bonus),
                'anomaly_bonus': float(anomaly_bonus)
            },
            'label': label
        }
        
        return float(final_score), metadata
    
    def save(self, path: str):
        """Salva modelo treinado"""
        model_data = {
            'scaler': self.scaler,
            'pca': self.pca,
            'kmeans': self.kmeans,
            'isolation_forest': self.isolation_forest,
            'feature_names': self.feature_names,
            'cluster_profiles': self.cluster_profiles,
            'cluster_quality_scores': self.cluster_quality_scores,
            'n_clusters': self.n_clusters,
            'n_components': self.n_components
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_data, path)
        print(f"💾 Modelo salvo em: {path}")
    
    @classmethod
    def load(cls, path: str):
        """Carrega modelo treinado"""
        model_data = joblib.load(path)
        
        scorer = cls(
            n_clusters=model_data['n_clusters'],
            n_components=model_data['n_components']
        )
        
        scorer.scaler = model_data['scaler']
        scorer.pca = model_data['pca']
        scorer.kmeans = model_data['kmeans']
        scorer.isolation_forest = model_data['isolation_forest']
        scorer.feature_names = model_data['feature_names']
        scorer.cluster_profiles = model_data['cluster_profiles']
        scorer.cluster_quality_scores = model_data['cluster_quality_scores']
        scorer.fitted = True
        
        print(f"📦 Modelo carregado de: {path}")
        return scorer


def extract_features_array(doc: dict) -> np.ndarray:
    """
    Extrai features numéricas de um documento DIRETAMENTE
    Não usa evaluate_resume_from_doc para evitar overhead
    
    Returns:
        Array com features na ordem:
        [skills_count, years_experience, projects_count, cert_count,
         metrics_count, tokens, has_email, has_phone, has_linkedin,
         doc_quality, is_experienced]
    """
    # Skills
    skills = doc.get('skills', [])
    skills_count = len(skills) if skills else 0
    
    # Experiência
    years_exp = doc.get('years_experience', 0) or 0
    
    # Projetos (contar experiências que mencionam projetos)
    experiences = doc.get('experiences', [])
    projects_count = sum(1 for exp in experiences if exp.get('description', '').lower().find('projeto') >= 0)
    
    # Certificações (estimativa)
    # Procurar por keywords de certificação no texto
    text = doc.get('resume_text_clean', '') or ''
    cert_keywords = ['certificação', 'certificado', 'certified', 'certificate', 'aws', 'azure', 'google cloud']
    cert_count = sum(1 for keyword in cert_keywords if keyword.lower() in text.lower())
    cert_count = min(cert_count, 5)  # Cap em 5
    
    # Métricas/Impactos (números + palavras de impacto)
    import re
    metrics_patterns = [
        r'\d+%',  # Percentuais
        r'\d+\s*(usuários|clientes|vendas|projetos)',  # Números com contexto
        r'(aumentou|reduziu|melhorou|otimizou|desenvolveu)\s+\d+',  # Verbos de impacto
    ]
    metrics_count = 0
    for pattern in metrics_patterns:
        metrics_count += len(re.findall(pattern, text.lower()))
    metrics_count = min(metrics_count, 15)  # Cap em 15
    
    # Tokens (tamanho do documento)
    tokens = len(text.split()) if text else 0
    
    # Contatos
    metadata = doc.get('metadata', {})
    has_email = 1 if metadata.get('email') else 0
    has_phone = 1 if metadata.get('phone') else 0
    has_linkedin = 1 if metadata.get('linkedin') else 0
    
    # Qualidade do documento (estimativa baseada em completude)
    doc_quality = 0.0
    if years_exp > 0:
        doc_quality += 0.2
    if skills_count > 0:
        doc_quality += 0.3
    if len(experiences) > 0:
        doc_quality += 0.2
    if has_email or has_phone:
        doc_quality += 0.2
    if tokens > 300:
        doc_quality += 0.1
    doc_quality = min(doc_quality, 1.0)
    
    # Classificação
    is_experienced = 1 if years_exp >= 2.0 else 0
    
    return np.array([
        float(skills_count),
        float(years_exp),
        float(projects_count),
        float(cert_count),
        float(metrics_count),
        float(tokens),
        float(has_email),
        float(has_phone),
        float(has_linkedin),
        float(doc_quality),
        float(is_experienced)
    ])


FEATURE_NAMES = [
    'skills_count', 'years_experience', 'projects_count', 'cert_count',
    'metrics_count', 'tokens', 'has_email', 'has_phone', 'has_linkedin',
    'doc_quality', 'is_experienced'
]
