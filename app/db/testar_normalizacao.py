#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testa a normalização de datas fragmentadas
"""
import os
import sys
from dotenv import load_dotenv
import pymongo
import re

load_dotenv()

def normalize_fragmented_dates(text: str) -> str:
    """
    Normaliza datas fragmentadas que aparecem em linhas separadas.
    Exemplo: "July 2011\n \nto \nNovember 2012" -> "July 2011 to November 2012"
    """
    lines = text.split('\n')
    result = []
    skip_until = -1
    
    for i in range(len(lines)):
        if i < skip_until:
            continue
            
        line = lines[i].strip()
        
        # Padrão: linha com apenas "Month Year"
        month_year = re.match(r'^((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})$', line, re.IGNORECASE)
        
        if month_year:
            start_date = month_year.group(1)
            
            # Procurar "to" nas próximas linhas (até 10 linhas à frente)
            found_to = False
            end_date = None
            
            for j in range(i + 1, min(i + 11, len(lines))):
                check_line = lines[j].strip()
                
                # Linha vazia, ignorar
                if not check_line:
                    continue
                
                # Encontrou "to"
                if check_line.lower() == 'to':
                    found_to = True
                    # Procurar data final após o "to"
                    for k in range(j + 1, min(j + 6, len(lines))):
                        end_line = lines[k].strip()
                        if not end_line:
                            continue
                        
                        # Verificar se é uma data válida
                        end_match = re.match(r'^((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|Present|Current|Now)$', end_line, re.IGNORECASE)
                        
                        if end_match:
                            end_date = end_match.group(1)
                            # Consolidar data completa
                            result.append(f"{start_date} to {end_date}")
                            skip_until = k + 1
                            break
                        else:
                            # Não é data válida, parar busca
                            break
                    
                    if end_date:
                        break
                    else:
                        # Tinha "to" mas não encontrou data válida
                        break
                
                # Se a linha não é vazia nem "to", parar busca
                if check_line.lower() != 'to':
                    break
            
            # Se não consolidou, adicionar linha original
            if not end_date:
                result.append(line)
        else:
            result.append(line)
    
    return '\n'.join(result)


# Carregar documento do MongoDB
MONGO_URI = os.getenv('MONGO_URI')
client = pymongo.MongoClient(MONGO_URI)
db = client['resumAI']

# Pegar o documento problemático
doc = db['curriculos'].find_one({'filename': {'$regex': '10554236'}})

if doc:
    print("=" * 80)
    print(f"Documento: {doc.get('filename')}")
    print("=" * 80)
    
    texto_original = doc.get('resume_text', '')
    
    # Mostrar trecho com as datas problemáticas
    print("\nTRECHO ORIGINAL (primeiras 5 ocorrências de 'July' ou 'April'):")
    print("-" * 80)
    lines = texto_original.split('\n')
    for i, line in enumerate(lines[:200]):
        if 'July' in line or 'April' in line or line.strip() == 'to':
            print(f"Linha {i}: {line}")
            # Mostrar 5 linhas de contexto
            for j in range(max(0, i-2), min(len(lines), i+5)):
                if j != i:
                    print(f"      {j}: {lines[j]}")
            print()
            break
    
    # Aplicar normalização
    print("\n" + "=" * 80)
    print("APLICANDO NORMALIZAÇÃO...")
    print("=" * 80)
    texto_normalizado = normalize_fragmented_dates(texto_original)
    
    # Mostrar trecho normalizado
    print("\nTRECHO NORMALIZADO (primeiras 1000 chars):")
    print("-" * 80)
    start_idx = texto_normalizado.find('July')
    if start_idx > 0:
        print(texto_normalizado[max(0, start_idx-100):start_idx+900])
    else:
        print(texto_normalizado[:1000])
    
    # Contar quantas datas consolidadas
    consolidated = re.findall(r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\s+to\s+(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|Present|Current))', texto_normalizado, re.IGNORECASE)
    
    print("\n" + "=" * 80)
    print(f"RESULTADO: {len(consolidated)} datas consolidadas encontradas")
    print("=" * 80)
    for i, date_range in enumerate(consolidated[:10], 1):
        print(f"  {i}. {date_range}")

else:
    print("Documento não encontrado!")

client.close()
