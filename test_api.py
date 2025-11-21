#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste da API ResumAI
Testa todos os endpoints principais
"""
import requests
import json
from typing import Dict, Any

API_URL = "http://localhost:8000"

def print_result(title: str, result: Dict[Any, Any]):
    """Imprime resultado formatado"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def test_health():
    """Testa endpoint de health"""
    print("\n🏥 Testando /health...")
    response = requests.get(f"{API_URL}/health")
    print_result("Health Check", response.json())
    return response.status_code == 200


def test_evaluate():
    """Testa avaliação de currículo"""
    print("\n📊 Testando /evaluate...")
    
    payload = {
        "resume_text": """
        João Silva
        Desenvolvedor Python Full Stack
        
        Experiência:
        - 5 anos como Desenvolvedor Python na Empresa XYZ
        - Especialista em Django, Flask, FastAPI
        - Experiência com MongoDB, PostgreSQL
        - Deploy em AWS e Docker
        
        Habilidades:
        Python, Django, FastAPI, MongoDB, PostgreSQL, Docker, AWS, Git, REST APIs
        
        Projetos:
        - Desenvolveu API REST que processa 10k requests/dia
        - Otimizou queries SQL, reduzindo tempo de resposta em 40%
        - Implementou sistema de cache com Redis
        
        Formação:
        Bacharelado em Ciência da Computação
        
        Email: joao.silva@email.com
        Telefone: (11) 99999-9999
        """,
        "job_description": """
        Buscamos Desenvolvedor Python Sênior
        
        Requisitos:
        - Mínimo 4 anos de experiência com Python
        - Experiência com frameworks web (Django/Flask/FastAPI)
        - Conhecimento em bancos de dados SQL e NoSQL
        - Experiência com Docker e cloud (AWS/GCP/Azure)
        - APIs REST
        
        Diferencial:
        - Experiência com otimização de performance
        - Conhecimento em cache (Redis/Memcached)
        """
    }
    
    response = requests.post(f"{API_URL}/evaluate", json=payload)
    print_result("Evaluation Result", response.json())
    return response.status_code == 200


def test_extract():
    """Testa extração de features"""
    print("\n🔍 Testando /extract...")
    
    payload = {
        "resume_text": """
        Maria Santos
        Analista de Dados
        
        3 anos de experiência com análise de dados
        Python, SQL, Power BI, Excel
        
        Projetos:
        - Dashboard de vendas com aumento de 25% em conversões
        - Análise preditiva com 90% de acurácia
        
        Email: maria@email.com
        """
    }
    
    response = requests.post(f"{API_URL}/extract", json=payload)
    print_result("Feature Extraction", response.json())
    return response.status_code == 200


def test_stats():
    """Testa endpoint de estatísticas"""
    print("\n📈 Testando /stats...")
    response = requests.get(f"{API_URL}/stats")
    print_result("Statistics", response.json())
    return response.status_code == 200


def test_root():
    """Testa endpoint raiz"""
    print("\n🏠 Testando / (root)...")
    response = requests.get(API_URL)
    print_result("Root Endpoint", response.json())
    return response.status_code == 200


def main():
    """Executa todos os testes"""
    print("="*60)
    print("  🧪 ResumAI API - Test Suite")
    print("="*60)
    print(f"API URL: {API_URL}")
    
    tests = [
        ("Root", test_root),
        ("Health Check", test_health),
        ("Extract Features", test_extract),
        ("Evaluate Resume", test_evaluate),
        ("Statistics", test_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Erro em {name}: {e}")
            results.append((name, False))
    
    # Resumo
    print(f"\n{'='*60}")
    print("  📋 RESUMO DOS TESTES")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n🎯 Total: {passed}/{total} testes passaram")
    
    if passed == total:
        print("✅ Todos os testes passaram!")
    else:
        print(f"⚠️  {total - passed} teste(s) falharam")


if __name__ == "__main__":
    main()
