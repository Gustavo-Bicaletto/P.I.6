#!/usr/bin/env python3
"""
Auto-anotação de pares currículo-vaga usando modelo genérico + heurísticas
Gera anotações automáticas para fine-tuning do Sentence-BERT
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sentence_transformers import SentenceTransformer, util


def calculate_skill_overlap(resume_skills: List[str], job_skills: List[str]) -> float:
    """Calcula % de overlap de skills"""
    if not job_skills:
        return 0.0
    
    resume_set = set([s.lower() for s in resume_skills])
    job_set = set([s.lower() for s in job_skills])
    
    matches = len(resume_set.intersection(job_set))
    return matches / len(job_set)


def analyze_seniority_match(resume_years: float, job_title: str) -> float:
    """Analisa se senioridade combina"""
    job_lower = job_title.lower()
    
    # Júnior: 0-2 anos
    if any(term in job_lower for term in ['júnior', 'junior', 'jr', 'trainee', 'estágio']):
        if resume_years <= 2:
            return 1.0
        elif resume_years <= 4:
            return 0.7
        else:
            return 0.5  # Over-qualified
    
    # Pleno: 2-5 anos
    if any(term in job_lower for term in ['pleno', 'mid-level', 'intermediário']):
        if 2 <= resume_years <= 5:
            return 1.0
        elif resume_years < 2:
            return 0.4  # Under-qualified
        elif resume_years <= 7:
            return 0.8
        else:
            return 0.6  # Over-qualified
    
    # Sênior: 5+ anos
    if any(term in job_lower for term in ['sênior', 'senior', 'sr', 'especialista', 'expert']):
        if resume_years >= 5:
            return 1.0
        elif resume_years >= 3:
            return 0.5  # Under-qualified
        else:
            return 0.2
    
    # Sem indicação de senioridade
    if resume_years >= 3:
        return 0.8
    else:
        return 0.6


def detect_area_mismatch(resume_text: str, job_description: str) -> bool:
    """Detecta se são áreas completamente diferentes"""
    
    # Áreas técnicas
    tech_areas = {
        'desenvolvimento': ['python', 'java', 'javascript', 'developer', 'programador', 'software engineer'],
        'dados': ['data scientist', 'data analyst', 'machine learning', 'bi', 'analista de dados'],
        'devops': ['devops', 'sre', 'cloud', 'kubernetes', 'docker', 'infraestrutura'],
        'design': ['designer', 'ui', 'ux', 'figma', 'photoshop'],
        'gestao': ['gerente', 'manager', 'coordenador', 'diretor'],
        'financeiro': ['contador', 'accountant', 'financeiro', 'contabilidade', 'auditor'],
        'vendas': ['vendas', 'sales', 'comercial', 'account executive'],
        'marketing': ['marketing', 'digital marketing', 'seo', 'social media'],
        'rh': ['recursos humanos', 'hr', 'recrutamento', 'talent'],
    }
    
    resume_lower = resume_text.lower()
    job_lower = job_description.lower()
    
    resume_areas = set()
    job_areas = set()
    
    for area, keywords in tech_areas.items():
        if any(kw in resume_lower for kw in keywords):
            resume_areas.add(area)
        if any(kw in job_lower for kw in keywords):
            job_areas.add(area)
    
    # Se não tem overlap de áreas, é mismatch
    if resume_areas and job_areas and not resume_areas.intersection(job_areas):
        return True
    
    return False


def auto_annotate_pair(pair: Dict[str, Any], model: SentenceTransformer) -> Dict[str, Any]:
    """Auto-anota um par usando modelo + heurísticas"""
    
    # 1. Similaridade semântica genérica (0-1)
    resume_emb = model.encode(pair['resume_text'][:1000], convert_to_tensor=True)
    job_emb = model.encode(pair['job_description'], convert_to_tensor=True)
    semantic_sim = float(util.cos_sim(resume_emb, job_emb)[0][0])
    
    # 2. Overlap de skills (0-1)
    skill_overlap = calculate_skill_overlap(
        pair.get('resume_skills', []),
        pair.get('job_required_skills', [])
    )
    
    # 3. Match de senioridade (0-1)
    seniority_match = analyze_seniority_match(
        pair.get('resume_years', 0),
        pair['job_title']
    )
    
    # 4. Detecta área incompatível
    area_mismatch = detect_area_mismatch(
        pair['resume_text'],
        pair['job_description']
    )
    
    # Cálculo do score final
    if area_mismatch:
        # Áreas diferentes = match muito baixo
        final_score = min(0.3, semantic_sim * 0.5)
    else:
        # Média ponderada: 40% skills, 30% semantic, 30% seniority
        final_score = (
            skill_overlap * 0.4 +
            semantic_sim * 0.3 +
            seniority_match * 0.3
        )
    
    # Determina label baseado no score
    if final_score >= 0.8:
        label = "excellent"
    elif final_score >= 0.6:
        label = "good"
    elif final_score >= 0.4:
        label = "fair"
    elif final_score >= 0.2:
        label = "poor"
    else:
        label = "none"
    
    # Gera notas explicativas
    notes_parts = []
    if skill_overlap > 0.7:
        notes_parts.append(f"Skills match {skill_overlap:.0%}")
    elif skill_overlap > 0:
        notes_parts.append(f"Parcial skills {skill_overlap:.0%}")
    else:
        notes_parts.append("Sem skills em comum")
    
    if area_mismatch:
        notes_parts.append("Áreas diferentes")
    
    if seniority_match < 0.5:
        notes_parts.append("Senioridade incompatível")
    
    notes = " | ".join(notes_parts)
    
    # Atualiza o par
    pair['match_score'] = round(final_score, 2)
    pair['match_label'] = label
    pair['notes'] = notes
    pair['auto_annotated'] = True
    
    return pair


def main():
    print("=" * 80)
    print("🤖 AUTO-ANOTAÇÃO DE PARES CURRÍCULO-VAGA")
    print("=" * 80)
    
    # Carrega modelo
    print("\n📥 Carregando Sentence-BERT...")
    model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')
    print("✅ Modelo carregado")
    
    # Carrega dados
    input_file = Path("data/matching_pairs_to_annotate.json")
    print(f"\n📂 Lendo {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        pairs = json.load(f)
    
    print(f"✅ Carregados {len(pairs)} pares")
    
    # Auto-anota
    print("\n🔄 Auto-anotando pares...")
    annotated_pairs = []
    
    for i, pair in enumerate(pairs, 1):
        if i % 10 == 0:
            print(f"   Processado {i}/{len(pairs)} pares...")
        
        annotated_pair = auto_annotate_pair(pair, model)
        annotated_pairs.append(annotated_pair)
    
    # Estatísticas
    print("\n📊 Estatísticas da auto-anotação:")
    label_counts = {}
    scores = []
    
    for pair in annotated_pairs:
        label = pair['match_label']
        label_counts[label] = label_counts.get(label, 0) + 1
        scores.append(pair['match_score'])
    
    for label in ['excellent', 'good', 'fair', 'poor', 'none']:
        count = label_counts.get(label, 0)
        pct = count / len(annotated_pairs) * 100
        print(f"   {label:10s}: {count:3d} ({pct:5.1f}%)")
    
    avg_score = sum(scores) / len(scores)
    print(f"\n   Score médio: {avg_score:.2f}")
    print(f"   Score min/max: {min(scores):.2f} / {max(scores):.2f}")
    
    # Salva
    output_file = Path("data/matching_pairs_annotated.json")
    print(f"\n💾 Salvando em {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(annotated_pairs, f, indent=2, ensure_ascii=False)
    
    print("✅ Auto-anotação concluída!")
    print("\n📋 Próximo passo:")
    print("   python app/ml/train_semantic_matcher.py")
    print("\n⚠️  Nota: Anotação automática não é perfeita.")
    print("   Você pode revisar/ajustar alguns pares se quiser melhorar ainda mais.")


if __name__ == "__main__":
    main()
