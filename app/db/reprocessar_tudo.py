#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Deleta a coleção dados_processados e reprocessa tudo do zero
"""
import os
from dotenv import load_dotenv
import pymongo

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI')
client = pymongo.MongoClient(MONGO_URI)
db = client['resumAI']

# Deletar coleção processada
print("🗑️  Deletando coleção 'dados_processados'...")
db['dados_processados'].drop()
print("✅ Coleção deletada!")

# Verificar
count = db['dados_processados'].count_documents({})
print(f"📊 Documentos restantes: {count}")

client.close()

print("\n🚀 Agora execute:")
print("   python -m app.db.pre_processamento")
