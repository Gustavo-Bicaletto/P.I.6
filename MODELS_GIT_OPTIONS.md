# ⚠️ ATENÇÃO: Modelos Grandes no Git

## 🚨 Problema Potencial

Você tem **1.4GB de modelos** para fazer commit:
- `models/semantic_matcher_finetuned/` → **1.1GB** (modelo principal)
- `models/resume_classifier/run-2025-11-18-balanced/` → **255MB**
- `models/unsupervised_scorer.pkl` → **3MB**
- `models/scoring_model.pkl` → **3MB**

**GitHub tem limite de 100MB por arquivo** e **recomenda usar Git LFS para arquivos > 50MB**.

---

## 🎯 Opções Disponíveis

### Opção 1: Git LFS (Recomendado para Colaboração) ⭐

**Quando usar**: Se outras pessoas precisarão clonar o repositório com os modelos.

**Vantagens**:
- ✅ Modelos ficam no repositório (versionados)
- ✅ Git gerencia automaticamente
- ✅ Clones são mais rápidos (modelos baixados sob demanda)

**Como fazer**:
```bash
# 1. Instalar Git LFS (uma vez)
git lfs install

# 2. Rastrear arquivos grandes
git lfs track "*.safetensors"
git lfs track "*.pkl"
git lfs track "models/semantic_matcher_finetuned/tokenizer.json"

# 3. Adicionar .gitattributes (criado automaticamente)
git add .gitattributes

# 4. Adicionar tudo e commitar
git add .
git commit -m "feat: Complete ML pipeline with REST API

✨ Features:
- Semantic matching model (Pearson 0.956, MAE 0.02)
- Hybrid scoring system (ML + Rule-Based)
- FastAPI REST API with 8 production endpoints
- Complete documentation and tests

🧹 Cleanup: -1.8GB, -61 files
🎯 Models tracked with Git LFS (1.4GB)"

# 5. Push
git push origin main
```

**Custo**: GitHub LFS tem 1GB grátis/mês de armazenamento e 1GB de bandwidth.

---

### Opção 2: Ignorar Modelos (Recomendado para Solo) 🔒

**Quando usar**: Se você é o único desenvolvedor e quer repositório leve.

**Vantagens**:
- ✅ Repositório pequeno (~50MB)
- ✅ Push/pull rápidos
- ✅ Sem custos de LFS
- ✅ Modelos ficam locais

**Como fazer**:
```bash
# 1. Adicionar modelos ao .gitignore
echo "" >> .gitignore
echo "# Modelos grandes (manter localmente)" >> .gitignore
echo "models/semantic_matcher_finetuned/" >> .gitignore
echo "models/resume_classifier/run-2025-11-18-balanced/" >> .gitignore
echo "models/unsupervised_scorer.pkl" >> .gitignore
echo "models/scoring_model.pkl" >> .gitignore

# 2. Remover do staging (se já adicionou)
git rm --cached -r models/semantic_matcher_finetuned 2>$null
git rm --cached -r models/resume_classifier/run-2025-11-18-balanced 2>$null
git rm --cached models/unsupervised_scorer.pkl 2>$null
git rm --cached models/scoring_model.pkl 2>$null

# 3. Commit
git add .
git commit -m "feat: Complete ML pipeline with REST API

✨ Features:
- Semantic matching model (Pearson 0.956, MAE 0.02)
- Hybrid scoring system (ML + Rule-Based)
- FastAPI REST API with 8 production endpoints
- Complete documentation and tests

🧹 Cleanup: -1.8GB, -61 files
📝 Note: Models (1.4GB) stored locally/cloud, not in repo"

# 4. Push
git push origin main

# 5. Documentar onde estão os modelos
echo "Modelos armazenados localmente em: E:\PI6\P.I.6\models\" > MODELS_LOCATION.md
git add MODELS_LOCATION.md
git commit -m "docs: Add models location reference"
git push
```

**Nota**: Crie backup dos modelos em cloud storage (Google Drive, Dropbox, S3, etc.)

---

### Opção 3: Cloud Storage + Download Script 🌐

**Quando usar**: Para produção ou equipes grandes.

**Vantagens**:
- ✅ Repositório leve
- ✅ Modelos em infraestrutura escalável
- ✅ Fácil distribuição
- ✅ Versionamento separado

**Como fazer**:

#### 1. Fazer Upload dos Modelos
```bash
# AWS S3 (exemplo)
aws s3 sync models/ s3://resumai-models/

# Google Cloud Storage (exemplo)
gsutil -m cp -r models/ gs://resumai-models/

# Azure Blob Storage (exemplo)
az storage blob upload-batch -d resumai-models -s models/
```

#### 2. Criar Script de Download
```python
# download_models.py
import requests
import os
from pathlib import Path

MODEL_URLS = {
    "semantic_matcher": "https://storage.example.com/semantic_matcher.tar.gz",
    "resume_classifier": "https://storage.example.com/resume_classifier.tar.gz",
    "unsupervised_scorer": "https://storage.example.com/unsupervised_scorer.pkl",
}

def download_models():
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    for name, url in MODEL_URLS.items():
        print(f"Downloading {name}...")
        # Download logic here
        
if __name__ == "__main__":
    download_models()
```

#### 3. Adicionar ao .gitignore e documentar
```bash
# Ignorar modelos
echo "models/*.safetensors" >> .gitignore
echo "models/semantic_matcher_finetuned/" >> .gitignore
echo "models/resume_classifier/run-*/" >> .gitignore

# Commit script
git add download_models.py
git add README.md  # Adicionar instruções de download
git commit -m "feat: Add models download script"
git push
```

---

## 📊 Comparação das Opções

| Critério | Git LFS | Ignorar | Cloud Storage |
|----------|---------|---------|---------------|
| **Tamanho do repo** | Médio (LFS pointers) | Pequeno | Pequeno |
| **Facilidade setup** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Colaboração** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| **Custo** | $5/mês (50GB) | Grátis | Variável |
| **Versionamento** | ✅ | ❌ | ✅ (manual) |
| **Performance** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🎯 Recomendação Final

### Para este projeto:

**RECOMENDO: Opção 2 (Ignorar Modelos)** porque:
1. ✅ Você é desenvolvedor solo (não precisa de LFS)
2. ✅ Modelos foram treinados localmente
3. ✅ Push/pull muito mais rápidos
4. ✅ Sem custos adicionais
5. ✅ Repositório fica leve e profissional

**Backup dos Modelos**:
```bash
# Criar backup compactado
Compress-Archive -Path models/ -DestinationPath backup_models.zip

# Upload para Google Drive / Dropbox / OneDrive
# Ou guardar em HD externo
```

---

## 🚀 Comando Recomendado

Execute este comando para ignorar os modelos grandes:

```bash
# Adicionar ao .gitignore
echo "`n# Modelos grandes (manter localmente)" >> .gitignore
echo "models/semantic_matcher_finetuned/" >> .gitignore
echo "models/resume_classifier/run-2025-11-18-balanced/" >> .gitignore
echo "models/unsupervised_scorer.pkl" >> .gitignore
echo "models/scoring_model.pkl" >> .gitignore

# Commit e push
git add .gitignore
git commit -m "chore: Ignore large ML models (1.4GB)"
git add .
git commit -m "feat: Complete ML pipeline with REST API

✨ Features:
- Semantic matching model (Pearson 0.956, MAE 0.02)
- Hybrid scoring system (ML + Rule-Based)
- FastAPI REST API with 8 production endpoints
- Complete documentation and tests

🧹 Cleanup: -1.8GB, -61 files"

git push origin main
```

**Tamanho final do push**: ~50MB (código + docs + imagens)

---

## ❓ FAQ

**Q: E se eu quiser compartilhar os modelos depois?**  
A: Upload para Google Drive e compartilhe o link no README.

**Q: Os modelos são reproduzíveis?**  
A: Sim! Os scripts de treinamento estão no repo. Qualquer um pode treinar novamente.

**Q: Preciso versionar os modelos?**  
A: Não necessariamente. Se treinar novo modelo, pode sobrescrever ou criar nova pasta.

**Q: E se eu mudar de ideia?**  
A: Pode adicionar Git LFS depois facilmente.

---

## ✅ Decisão

**Escolha uma opção acima e execute os comandos correspondentes.**

Recomendo **Opção 2** para este projeto! 🎯
