#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testa normalização de datas MM/YYYY fragmentadas
"""
import sys
sys.path.insert(0, 'd:/PI 6/P.I.6-1')

from app.db.pre_processamento import normalize_fragmented_dates, extract_experiences

# Texto de exemplo
texto = """Investment Accountant

10/2012

to 

11/2015

Reconciled mutual fund accounts with the custody"""

print("=" * 80)
print("TEXTO ORIGINAL:")
print("=" * 80)
print(texto)

print("\n" + "=" * 80)
print("APÓS NORMALIZAÇÃO:")
print("=" * 80)
texto_norm = normalize_fragmented_dates(texto)
print(texto_norm)

print("\n" + "=" * 80)
print("EXPERIÊNCIAS EXTRAÍDAS:")
print("=" * 80)
exps = extract_experiences(texto)
print(f"Total: {len(exps)}")
for exp in exps:
    print(f"\n  Título: {exp['title']}")
    print(f"  Datas: {exp['dates']}")
    print(f"  Empresa: {exp['company']}")
