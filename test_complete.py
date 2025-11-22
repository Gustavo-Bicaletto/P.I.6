#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Teste Completo do ResumAI
Avalia a QUALIDADE de um currículo (sem necessidade de vaga)
"""
import sys
from pathlib import Path
from typing import Dict, Any

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.scoring.hybrid_scorer import HybridScorer
from app.scoring.use_case import build_features_from_doc, build_subscores


def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_section(title: str):
    """Imprime seção formatada"""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


def format_score(score: float, max_val: float = 1.0) -> str:
    """Formata score com barra de progresso"""
    if max_val == 1.0:
        percentage = score * 100
        bar_length = int(score * 20)
    else:
        percentage = (score / max_val) * 100
        bar_length = int((score / max_val) * 20)
    
    bar = '█' * bar_length + '░' * (20 - bar_length)
    return f"{bar} {percentage:.1f}%"


def test_complete_pipeline(resume_path: str):
    """
    Testa pipeline completo do ResumAI - Avaliação de Qualidade
    
    Args:
        resume_path: Caminho para arquivo .txt do currículo
    """
    
    print_header("🧪 AVALIAÇÃO DE QUALIDADE - ResumAI")
    print(f"📄 Currículo: {resume_path}")
    
    # 1. Carregar currículo
    print_section("1️⃣ Carregando Currículo")
    try:
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
        
        print(f"✅ Arquivo carregado: {len(resume_text)} caracteres")
        print(f"📝 Preview (primeiros 200 chars):")
        print(f"   {resume_text[:200]}...")
    except Exception as e:
        print(f"❌ Erro ao carregar arquivo: {e}")
        return
    
    # Preparar documento (sem vaga - foco em qualidade)
    doc = {
        "resume_text_clean": resume_text,
        "job_description": None
    }
    
    # 2. Extração de Features
    print_section("2️⃣ Extração de Features (NLP + Regex)")
    try:
        features = build_features_from_doc(doc)
        
        # Adicionar has_experience ao doc para o hybrid_scorer usar
        doc['has_experience'] = features.get('has_experience', False)
        
        print(f"\n📊 Features Extraídas:")
        print(f"   🔧 Skills detectadas: {len(features.get('skills', []))}")
        if features.get('skills'):
            print(f"      → {', '.join(features['skills'][:10])}")
            if len(features['skills']) > 10:
                print(f"      ... e mais {len(features['skills']) - 10}")
        
        print(f"\n   📅 Experiência:")
        print(f"      → Anos de experiência: {features.get('years_total', 0):.1f} anos")
        print(f"      → Tem experiência: {'✅' if features.get('has_experience') else '❌'}")
        
        print(f"\n   📈 Conteúdo:")
        print(f"      → Métricas quantificáveis: {features.get('metrics_hits', 0)}")
        print(f"      → Projetos mencionados: {features.get('project_hits', 0)}")
        print(f"      → Certificações: {features.get('cert_points', 0)}")
        
        print(f"\n   📝 Qualidade do Documento:")
        print(f"      → Tokens: {features.get('tokens', 0)}")
        print(f"      → Seções presentes: {features.get('sections_present', 0)}")
        print(f"      → Tem email: {'✅' if features.get('has_email') else '❌'}")
        print(f"      → Tem telefone: {'✅' if features.get('has_phone') else '❌'}")
        
    except Exception as e:
        print(f"❌ Erro na extração de features: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Classificação de Experiência
    print_section("3️⃣ Classificação de Experiência (BERT)")
    try:
        scorer = HybridScorer()
        result = scorer.score(doc)
        
        # Usar has_experience das features (mais confiável)
        is_experienced = features.get('has_experience', False)
        confidence = result.get('ml_confidence', 0)
        
        print(f"\n🎯 Resultado:")
        print(f"   Classificação: {'✅ EXPERIENTE' if is_experienced else '❌ SEM EXPERIÊNCIA'}")
        print(f"   Confiança do modelo: {format_score(confidence)}")
        print(f"   Método usado: {result.get('method', 'unknown').upper()}")
        
    except Exception as e:
        print(f"❌ Erro na classificação: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Scoring Híbrido (ML + Rule-Based)
    print_section("4️⃣ Scoring Híbrido (ML + Rule-Based)")
    try:
        subscores = result.get('rb_subscores', {})
        final_score = result.get('score', 0)
        label = result.get('label', 'Desconhecido')
        
        print(f"\n📊 Avaliação por Categoria:")
        subscore_names = {
            'skills': '🔧 Habilidades Técnicas',
            'experience': '📅 Experiência',
            'projects': '🚀 Projetos',
            'certs': '🎓 Certificações',
            'impact': '📈 Resultados/Métricas',
            'doc_quality': '📝 Qualidade do Documento',
            'contact': '📞 Informações de Contato'
        }
        
        # Mostrar apenas scores relevantes (sem semantic e context que eram para matching)
        for key, name in subscore_names.items():
            if key in subscores:
                score = subscores[key]
                print(f"   {name}: {format_score(score)}")
        
        print(f"\n🎯 Avaliação Final:")
        print(f"   {format_score(final_score, 100)} ({final_score:.1f}/100)")
        print(f"   Qualidade: {label.upper()}")
        
        # Explicação
        explain = result.get('explain', {})
        if explain.get('top_up'):
            top_up_filtered = [s for s in explain['top_up'] if s not in ['semantic', 'context']]
            if top_up_filtered:
                print(f"\n   ⬆️  Pontos fortes: {', '.join(top_up_filtered[:3])}")
        if explain.get('top_down'):
            top_down_filtered = [s for s in explain['top_down'] if s not in ['semantic', 'context']]
            if top_down_filtered:
                print(f"   ⬇️  Pontos a melhorar: {', '.join(top_down_filtered[:3])}")
        
    except Exception as e:
        print(f"❌ Erro no scoring: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Resumo Final
    print_header("📋 RESUMO FINAL")
    
    print(f"\n✅ Avaliação Concluída!")
    print(f"\n📊 Resumo:")
    print(f"   • Skills identificadas: {len(features.get('skills', []))}")
    print(f"   • Perfil: {'Experiente' if is_experienced else 'Estagiário/Júnior'}")
    print(f"   • Score: {final_score:.1f}/100")
    print(f"   • Avaliação: {label.upper()}")
    print(f"   • Seções do currículo: {features.get('sections_present', 0)}")
    
    # Critério usado
    cutoff = 50.0 if is_experienced else 40.0
    perfil_nome = "Experiente" if is_experienced else "Estagiário/Júnior"
    print(f"\n📌 Critério aplicado: {perfil_nome} (>= {cutoff:.0f} = BOM)")
    
    print(f"\n💡 Recomendações para Melhoria:")
    recommendations = []
    
    if subscores.get('skills', 0) < 0.6:
        recommendations.append("   • Adicionar mais habilidades técnicas relevantes")
    if subscores.get('experience', 0) < 0.5:
        recommendations.append("   • Detalhar melhor a experiência profissional com períodos e responsabilidades")
    if subscores.get('projects', 0) < 0.5:
        recommendations.append("   • Incluir projetos relevantes (acadêmicos, pessoais ou profissionais)")
    if subscores.get('impact', 0) < 0.6:
        recommendations.append("   • Quantificar resultados e impacto (números, métricas, percentuais)")
    if subscores.get('doc_quality', 0) < 0.7:
        recommendations.append("   • Melhorar estrutura: adicionar seções importantes (Formação, Projetos, etc.)")
    if not features.get('has_email') or not features.get('has_phone'):
        recommendations.append("   • Garantir que email e telefone estejam visíveis")
    if subscores.get('certs', 0) < 0.5:
        recommendations.append("   • Adicionar certificações e cursos relevantes")
    
    if recommendations:
        for rec in recommendations[:5]:  # Mostrar no máximo 5 recomendações
            print(rec)
    else:
        print("   ✅ Currículo está bem estruturado!")
    
    print(f"\n🎯 Resultado Final:")
    if label == "Bom":
        print(f"   ✅ BOM - Currículo tem boa qualidade")
        print(f"      Está aprovado para seguir no processo de avaliação!")
    else:
        print(f"   ❌ RUIM - Currículo precisa de melhorias")
        print(f"      Recomenda-se revisão antes de submeter para processos seletivos.")
    
    print(f"\n{'='*70}\n")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Avaliação de Qualidade de Currículo - ResumAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Avaliar qualidade de um currículo
  python test_complete.py curriculo.txt
  
  # Avaliar currículo com caminho específico
  python test_complete.py "C:\\Users\\Nome\\Desktop\\meu_curriculo.txt"
        """
    )
    
    parser.add_argument('resume', help='Caminho para arquivo .txt do currículo')
    
    args = parser.parse_args()
    
    # Executar avaliação
    test_complete_pipeline(args.resume)


if __name__ == "__main__":
    main()
