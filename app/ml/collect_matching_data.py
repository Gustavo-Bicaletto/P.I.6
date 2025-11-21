#!/usr/bin/env python3
"""
Coleta dados para treinamento de Matching Semântico
Exporta pares (currículo, vaga) do MongoDB para anotação manual
"""
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.mongo import get_db


def collect_resume_job_pairs(limit: int = 100):
    """
    Coleta pares de currículos e vagas para anotação
    
    Args:
        limit: Número máximo de pares a coletar
    """
    print("=" * 80)
    print("📊 COLETA DE DADOS PARA MATCHING SEMÂNTICO")
    print("=" * 80)
    
    db = get_db()
    
    # Coletar currículos variados
    print(f"\n📥 Coletando {limit} currículos...")
    resumes = list(db.dados_processados.find(
        {"resume_text_clean": {"$exists": True, "$ne": ""}},
        {
            "_id": 1,
            "filename": 1,
            "resume_text_clean": 1,
            "skills": 1,
            "years_experience": 1
        }
    ).limit(limit))
    
    print(f"✅ Coletados {len(resumes)} currículos")
    
    # Criar estrutura para anotação
    pairs = []
    
    # Descrições de vagas de DIVERSAS ÁREAS (tech, financeiro, vendas, marketing, etc.)
    sample_jobs = [
        # TECNOLOGIA
        {
            "job_id": "job_001",
            "title": "Desenvolvedor Python Sênior",
            "description": "Buscamos desenvolvedor Python com 5+ anos de experiência. Requisitos: Python, Django/Flask, PostgreSQL, Docker, AWS. Experiência com APIs REST e microserviços.",
            "required_skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"]
        },
        {
            "job_id": "job_002",
            "title": "Desenvolvedor Full Stack Pleno",
            "description": "Desenvolvedor Full Stack para trabalhar com React e Node.js. Requisitos: JavaScript, React, Node.js, MongoDB, Git. Desejável: TypeScript, Next.js.",
            "required_skills": ["JavaScript", "React", "Node.js", "MongoDB"]
        },
        {
            "job_id": "job_003",
            "title": "Data Scientist",
            "description": "Cientista de dados para análise e modelagem. Requisitos: Python, Pandas, Scikit-learn, SQL, Machine Learning. Desejável: TensorFlow, PyTorch.",
            "required_skills": ["Python", "Machine Learning", "SQL", "Pandas"]
        },
        {
            "job_id": "job_004",
            "title": "DevOps Engineer",
            "description": "Engenheiro DevOps para gerenciar infraestrutura cloud. Requisitos: AWS/Azure, Kubernetes, Docker, Terraform, CI/CD. Experiência com monitoring (Prometheus, Grafana).",
            "required_skills": ["AWS", "Kubernetes", "Docker", "Terraform", "CI/CD"]
        },
        
        # FINANCEIRO & CONTABILIDADE
        {
            "job_id": "job_005",
            "title": "Contador Sênior",
            "description": "Contador com experiência em contabilidade gerencial e fiscal. Requisitos: CRC ativo, conhecimento em IFRS, fechamento contábil, conciliações, ERP (SAP/TOTVS). Mínimo 5 anos de experiência.",
            "required_skills": ["Contabilidade", "IFRS", "SAP", "Fechamento Contábil", "Conciliações"]
        },
        {
            "job_id": "job_006",
            "title": "Analista Financeiro Pleno",
            "description": "Analista financeiro para planejamento e controle. Requisitos: Excel avançado, análise de fluxo de caixa, budget, forecast, Power BI. Graduação em Administração/Economia/Contabilidade.",
            "required_skills": ["Excel", "Análise Financeira", "Budget", "Power BI", "Fluxo de Caixa"]
        },
        
        # VENDAS & COMERCIAL
        {
            "job_id": "job_007",
            "title": "Executivo de Vendas B2B",
            "description": "Executivo comercial para vendas corporativas. Requisitos: Experiência com vendas consultivas, gestão de pipeline (CRM), prospecção ativa, negociação. Desejável: Inglês fluente.",
            "required_skills": ["Vendas B2B", "CRM", "Prospecção", "Negociação"]
        },
        {
            "job_id": "job_008",
            "title": "Gerente Comercial",
            "description": "Gerente para liderar equipe de vendas. Requisitos: 5+ anos em gestão comercial, experiência com metas, coaching de equipe, análise de KPIs. Ensino superior completo.",
            "required_skills": ["Gestão Comercial", "Liderança", "Gestão de Equipes", "KPIs"]
        },
        
        # MARKETING
        {
            "job_id": "job_009",
            "title": "Analista de Marketing Digital",
            "description": "Analista para gestão de campanhas digitais. Requisitos: Google Ads, Facebook Ads, SEO, Google Analytics, copywriting. Experiência com e-commerce é diferencial.",
            "required_skills": ["Marketing Digital", "Google Ads", "SEO", "Analytics"]
        },
        
        # RECURSOS HUMANOS
        {
            "job_id": "job_010",
            "title": "Analista de Recrutamento e Seleção",
            "description": "Analista de RH para R&S. Requisitos: Experiência com recrutamento tech e não-tech, LinkedIn Recruiter, entrevistas por competências, testes comportamentais. Psicologia/Administração.",
            "required_skills": ["Recrutamento", "Seleção", "Entrevistas", "LinkedIn Recruiter"]
        },
        
        # DESIGN
        {
            "job_id": "job_011",
            "title": "UI/UX Designer",
            "description": "Designer para produtos digitais. Requisitos: Figma, Adobe XD, prototipação, design system, testes de usabilidade. Portfolio obrigatório.",
            "required_skills": ["UI Design", "UX Design", "Figma", "Prototipação"]
        },
        
        # OPERAÇÕES & LOGÍSTICA
        {
            "job_id": "job_012",
            "title": "Analista de Logística",
            "description": "Analista para gestão de supply chain. Requisitos: Experiência com logística de distribuição, controle de estoque, WMS, análise de rotas, negociação com transportadoras.",
            "required_skills": ["Logística", "Supply Chain", "WMS", "Gestão de Estoque"]
        }
    ]
    
    print(f"\n🎯 Criando pares para {len(sample_jobs)} vagas de exemplo...")
    
    # Criar pares (cada currículo com cada vaga)
    for resume in resumes:
        resume_text = resume.get('resume_text_clean', '')
        resume_skills = resume.get('skills', [])
        years = resume.get('years_experience', 0) or 0
        
        # Limitar texto para não ficar muito grande
        resume_text_short = resume_text[:1000] if len(resume_text) > 1000 else resume_text
        
        for job in sample_jobs:
            pair = {
                "resume_id": str(resume['_id']),
                "resume_filename": resume.get('filename', 'unknown'),
                "resume_text": resume_text_short,
                "resume_skills": resume_skills[:10],  # Top 10 skills
                "resume_years": years,
                "job_id": job['job_id'],
                "job_title": job['title'],
                "job_description": job['description'],
                "job_required_skills": job['required_skills'],
                
                # Campos para anotação manual
                "match_score": None,  # 0.0 a 1.0 (a preencher)
                "match_label": None,  # "excellent" / "good" / "fair" / "poor" / "none"
                "notes": ""  # Observações do anotador
            }
            pairs.append(pair)
    
    print(f"✅ Criados {len(pairs)} pares (currículo × vaga)")
    
    # Salvar em JSON
    output_file = Path("data/matching_pairs_to_annotate.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Dados salvos em: {output_file}")
    print(f"\n📋 Próximos passos:")
    print(f"   1. Abrir {output_file}")
    print(f"   2. Para cada par, preencher:")
    print(f"      • match_score: 0.0 (sem match) a 1.0 (match perfeito)")
    print(f"      • match_label: 'excellent', 'good', 'fair', 'poor', 'none'")
    print(f"      • notes: observações (opcional)")
    print(f"   3. Salvar como: data/matching_pairs_annotated.json")
    print(f"   4. Executar: python app/ml/train_semantic_matcher.py")
    
    # Criar arquivo de exemplo anotado
    example_file = Path("data/matching_annotation_example.json")
    example_pairs = pairs[:2]  # Pegar 2 exemplos
    
    # Anotar exemplos
    example_pairs[0]['match_score'] = 0.85
    example_pairs[0]['match_label'] = 'good'
    example_pairs[0]['notes'] = 'Candidato tem Python e experiência relevante, mas faltam algumas skills AWS'
    
    example_pairs[1]['match_score'] = 0.3
    example_pairs[1]['match_label'] = 'poor'
    example_pairs[1]['notes'] = 'Skills não compatíveis com a vaga'
    
    with open(example_file, 'w', encoding='utf-8') as f:
        json.dump(example_pairs, f, ensure_ascii=False, indent=2)
    
    print(f"\n📖 Exemplo de anotação em: {example_file}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Coleta pares currículo-vaga para anotação')
    parser.add_argument('--limit', type=int, default=50, help='Número de currículos (default: 50)')
    args = parser.parse_args()
    
    collect_resume_job_pairs(limit=args.limit)
