# 🧹 Análise de Limpeza do Projeto - ResumAI

## 📊 Status Atual
- **Total de arquivos não rastreados**: ~50
- **Arquivos modificados**: 7
- **Arquivos deletados**: 5

## 🗑️ Arquivos para REMOVER (não são necessários)

### 1. Checkpoints de Treinamento (TODOS)
**Pasta completa**: `checkpoints/` (~500MB)
- ❌ `checkpoints/model/`
- ❌ `checkpoints/model_1/`
- ❌ `checkpoints/model_2/`
- ❌ `checkpoints/model_3/`

**Motivo**: Checkpoints intermediários de treinamento. Não são necessários pois já temos os modelos finais treinados.

**Ação**: Adicionar ao `.gitignore` e deletar

---

### 2. Runs Antigas de Classificadores (Parcial)
**Pasta**: `models/resume_classifier/`

**REMOVER** (runs antigas de experimentos):
- ❌ `run-2025-11-18-smoke/` (modelo de teste smoke)
- ❌ `run-2025-11-18-gpu-full/` (run experimental completo)
- ❌ `checkpoint-34/` (checkpoint antigo)
- ❌ `checkpoint-51/` (checkpoint antigo)

**MANTER** (modelo balanceado final em uso):
- ✅ `run-2025-11-18-balanced/` (modelo em produção)
  - Mas podemos remover seus checkpoints intermediários:
    - ❌ `checkpoint-68/`
    - ❌ `checkpoint-102/`

---

### 3. Scripts de Teste (Temporários)
- ❌ `test_regex.py` (teste de regex isolado)
- ❌ `test_payload.json` (payload de teste da API)
- ❌ `test_unsupervised_vs_rulebased.py` (comparação já feita)
- ❌ `train_unsupervised.py` (script antigo de treinamento)

**MANTER** (testes úteis):
- ✅ `test_api.py` (suite de testes da API)
- ✅ `test_hybrid_scorer.py` (teste do scorer híbrido)
- ✅ `test_semantic_integration.py` (teste de integração)

---

### 4. Documentação Duplicada/Obsoleta
- ❌ `API_IMPLEMENTATION_SUCCESS.md` (temporário, info já no README)
- ✅ `API_README.md` (manter - documentação completa da API)
- ✅ `USAGE_HYBRID_CLASSIFIER.md` (manter - guia de uso)
- ✅ `README.md` (manter - documentação principal)
- ✅ `README-ML.md` (manter - documentação ML)

---

### 5. Dados de Treinamento (Arquivos Grandes)
**Pasta**: `data/`

**Status atual**:
- `matching_pairs_to_annotate.json` (pode ser grande)
- `matching_pairs_annotated.json` (6000+ pares, ~5MB)
- `matching_annotation_example.json` (exemplo pequeno)
- `scoring_annotations.json`
- `scoring_annotations_auto.json`

**Decisão**: 
- ✅ MANTER `matching_annotation_example.json` (exemplo para documentação)
- ❓ `matching_pairs_annotated.json` - MANTER se < 10MB (dados valiosos de treinamento)
- ❌ `matching_pairs_to_annotate.json` - REMOVER (dados brutos, pode ser regenerado)
- ❌ `scoring_annotations_auto.json` - REMOVER (auto-gerado, pode ser recriado)
- ✅ MANTER `scoring_annotations.json` (anotações manuais valiosas)

---

### 6. Logs e Outputs
- ❌ `app/extraction.log` (log temporário)
- ❌ `app/data/outputs/resumes/logs/extraction.log` (log temporário)
- ❌ `app/resumes_dataset.json` (dataset temporário de testes)

---

### 7. Arquivos Antigos do Resume Classifier (raiz)
- ❌ `models/resume_classifier/vocab.txt` (raiz antiga)
- ❌ `models/resume_classifier/training_results.json` (raiz antiga)
- ❌ `models/resume_classifier/training_args.bin` (raiz antiga)
- ❌ `models/resume_classifier/tokenizer_config.json` (raiz antiga)
- ❌ `models/resume_classifier/tokenizer.json` (raiz antiga)
- ❌ `models/resume_classifier/special_tokens_map.json` (raiz antiga)
- ❌ `models/resume_classifier/config.json` (raiz antiga)
- ❌ `models/resume_classifier/model.safetensors` (raiz antiga)

**Motivo**: Temos os modelos organizados nas subpastas (run-2025-11-18-balanced)

---

## ✅ Arquivos ESSENCIAIS para MANTER

### Código da Aplicação
```
app/
├── __init__.py ✅
├── api.py ✅ (API REST)
├── main.py ✅ (entry point)
├── db/
│   ├── __init__.py ✅
│   ├── mongo.py ✅
│   ├── extracao_json.py ✅
│   ├── extracao_dataset01.py ✅
│   ├── pre_processamento.py ✅
│   ├── recalcular_experiencia.py ✅
│   ├── reprocessar_tudo.py ✅
│   └── ver_documento.py ✅
├── ml/
│   ├── __init__.py ✅
│   ├── unsupervised_scoring.py ✅
│   ├── semantic_similarity.py ✅ (modelo em produção)
│   ├── train_semantic_matcher.py ✅
│   ├── train_advanced.py ✅
│   ├── evaluate_semantic_matcher.py ✅
│   ├── collect_matching_data.py ✅
│   ├── auto_annotate_matching.py ✅
│   ├── predict.py ✅
│   ├── prepare_training_data.py ✅
│   └── train_model.py ✅
├── nlp/
│   ├── __init__.py ✅
│   └── spacy_nlp.py ✅
└── scoring/
    ├── __init__.py ✅
    ├── config.py ✅
    ├── engine.py ✅
    ├── subscores.py ✅
    ├── use_case.py ✅
    └── hybrid_scorer.py ✅
```

### Modelos ML (Manter apenas os essenciais)
```
models/
├── unsupervised_scorer.pkl ✅ (3MB)
├── semantic_matcher_finetuned/ ✅ (1.1GB - modelo principal)
└── resume_classifier/
    └── run-2025-11-18-balanced/ ✅ (modelo balanceado em produção)
        ├── model.safetensors ✅
        ├── config.json ✅
        ├── tokenizer*.json ✅
        └── deep_test_report.json ✅
```

### Documentação
```
├── README.md ✅
├── README-ML.md ✅
├── API_README.md ✅
├── USAGE_HYBRID_CLASSIFIER.md ✅
├── requirements.txt ✅
├── requirements-ml.txt ✅
└── requirements-api.txt ✅
```

### Testes
```
├── test_api.py ✅
├── test_hybrid_scorer.py ✅
└── test_semantic_integration.py ✅
```

### Configuração
```
├── .gitignore ✅
├── .gitattributes ✅
└── .env.example ✅
```

---

## 📝 Plano de Ação

### 1. Atualizar .gitignore
Adicionar:
```
# Checkpoints de treinamento
checkpoints/

# Logs
*.log
app/data/outputs/

# Dados temporários
data/matching_pairs_to_annotate.json
data/scoring_annotations_auto.json
test_payload.json
app/resumes_dataset.json

# Modelos antigos/experimentais
models/resume_classifier/run-2025-11-18-smoke/
models/resume_classifier/run-2025-11-18-gpu-full/
models/resume_classifier/checkpoint-*/

# Arquivos da raiz antiga do classifier
models/resume_classifier/*.safetensors
models/resume_classifier/vocab.txt
models/resume_classifier/training_*.json
models/resume_classifier/training_*.bin
```

### 2. Remover Arquivos
```bash
# Checkpoints
rm -rf checkpoints/

# Runs antigas
rm -rf models/resume_classifier/run-2025-11-18-smoke/
rm -rf models/resume_classifier/run-2025-11-18-gpu-full/
rm -rf models/resume_classifier/checkpoint-34/
rm -rf models/resume_classifier/checkpoint-51/
rm -rf models/resume_classifier/run-2025-11-18-balanced/checkpoint-68/
rm -rf models/resume_classifier/run-2025-11-18-balanced/checkpoint-102/

# Arquivos raiz antiga do classifier
rm models/resume_classifier/vocab.txt
rm models/resume_classifier/training_results.json
rm models/resume_classifier/training_args.bin
rm models/resume_classifier/tokenizer_config.json
rm models/resume_classifier/tokenizer.json
rm models/resume_classifier/special_tokens_map.json
rm models/resume_classifier/config.json
rm models/resume_classifier/model.safetensors

# Scripts de teste temporários
rm test_regex.py
rm test_payload.json
rm test_unsupervised_vs_rulebased.py
rm train_unsupervised.py

# Documentação temporária
rm API_IMPLEMENTATION_SUCCESS.md

# Logs
rm app/extraction.log
rm -rf app/data/outputs/

# Datasets temporários
rm app/resumes_dataset.json
rm data/matching_pairs_to_annotate.json
rm data/scoring_annotations_auto.json
```

### 3. Adicionar ao Git (apenas essenciais)
```bash
git add .
git status
```

---

## 📊 Resumo da Limpeza

### Antes
- ~163 arquivos totais
- Checkpoints: ~500MB
- Runs antigas: ~1.5GB
- Total: ~3GB+

### Depois (estimado)
- ~80 arquivos essenciais
- Modelos em produção: ~1.2GB
- Código + docs: ~2MB
- Total: ~1.2GB

### Economia
- **-50% arquivos** (83 arquivos removidos)
- **-60% espaço** (~1.8GB economizado)
- **+100% organização** ✨

---

## ⚠️ IMPORTANTE

**ANTES DE DELETAR**, faça backup dos modelos:
```bash
# Criar backup
mkdir backup_models
cp -r models/ backup_models/
cp -r checkpoints/ backup_models/
```

**Modelos que NÃO devem ser deletados**:
1. ✅ `models/semantic_matcher_finetuned/` - Modelo semântico principal (Pearson 0.956)
2. ✅ `models/unsupervised_scorer.pkl` - Scorer não supervisionado
3. ✅ `models/resume_classifier/run-2025-11-18-balanced/` - Classificador em produção

---

## 🎯 Resultado Final

Projeto limpo, organizado e pronto para commit com:
- ✅ Código essencial apenas
- ✅ Modelos em produção
- ✅ Documentação completa
- ✅ Testes funcionais
- ❌ Sem checkpoints desnecessários
- ❌ Sem runs experimentais antigas
- ❌ Sem arquivos temporários
