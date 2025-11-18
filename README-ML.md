# 🤖 Treinamento de Modelo ML para Classificação de Currículos

Este guia explica como treinar um modelo de Machine Learning para classificar currículos automaticamente.

## 📋 Pré-requisitos

1. Python 3.8+
2. MongoDB com dados processados (coleção `dados_processados`)
3. GPU NVIDIA (opcional, mas recomendado para treino mais rápido)

## 🚀 Passo a Passo

### 1. Instalar Dependências

```bash
# Instalar dependências de ML
pip install -r requirements-ml.txt

# OU se tiver GPU NVIDIA (muito mais rápido):
pip install torch --index-url https://download.pytorch.org/whl/cu118
pip install transformers datasets scikit-learn accelerate tqdm
```

### 2. Preparar Dados de Treinamento

Este passo extrai dados do MongoDB e cria datasets balanceados:

```bash
# Preparar dados (balanceado, mínimo 2 anos para "experienced")
python -m app.ml.prepare_training_data --min-years 2.0

# Opções avançadas:
python -m app.ml.prepare_training_data \
  --min-years 2.0 \
  --max-per-class 1000 \
  --test-size 0.2 \
  --val-size 0.1 \
  --output-dir data/training
```

**Saída esperada:**
- `data/training/train.json` - Dados de treino
- `data/training/validation.json` - Dados de validação
- `data/training/test.json` - Dados de teste
- `data/training/metadata.json` - Metadados do dataset

### 3. Treinar o Modelo

```bash
# Treino básico com DistilBERT (modelo menor e rápido)
python -m app.ml.train_model --model distilbert-base-uncased --epochs 3

# Com GPU (recomendado):
python -m app.ml.train_model \
  --model distilbert-base-uncased \
  --epochs 3 \
  --batch-size 16 \
  --lr 2e-5

# Sem GPU (mais lento):
python -m app.ml.train_model \
  --model distilbert-base-uncased \
  --epochs 3 \
  --batch-size 8 \
  --no-gpu
```

**Modelos disponíveis:**

| Modelo | Tamanho | Velocidade | Qualidade | Recomendação |
|--------|---------|------------|-----------|--------------|
| `distilbert-base-uncased` | 66M | ⚡⚡⚡ | ⭐⭐⭐ | **Início** |
| `bert-base-uncased` | 110M | ⚡⚡ | ⭐⭐⭐⭐ | Produção |
| `roberta-base` | 125M | ⚡⚡ | ⭐⭐⭐⭐ | Melhor qualidade |

**Saída esperada:**
- `models/resume_classifier/` - Modelo treinado
- `models/resume_classifier/training_results.json` - Métricas de avaliação

### 4. Testar o Modelo

```bash
# Testar com documentos do MongoDB
python -m app.ml.predict --model models/resume_classifier --from-db --limit 10

# Testar documento específico
python -m app.ml.predict --model models/resume_classifier --doc-id "673abc123def456789012345"

# Testar com texto direto
python -m app.ml.predict --model models/resume_classifier --text "Senior Software Engineer with 10 years..."

# Testar com arquivo
python -m app.ml.predict --model models/resume_classifier --file curriculo.txt
```

## 📊 Métricas de Avaliação

Após o treinamento, você verá métricas como:

```
🎯 Resultados no Teste:
   Accuracy:  0.9250
   F1 Score:  0.9180
   Precision: 0.9300
   Recall:    0.9060
```

**O que significam:**
- **Accuracy**: % de acertos totais
- **F1 Score**: Média harmônica de precisão e recall (métrica principal)
- **Precision**: Dos que previu como "experienced", quantos realmente são
- **Recall**: Dos que são "experienced", quantos o modelo encontrou

## ⚙️ Configurações Avançadas

### Ajustar Hiperparâmetros

```bash
python -m app.ml.train_model \
  --model distilbert-base-uncased \
  --epochs 5 \
  --batch-size 32 \
  --lr 3e-5 \
  --max-length 768
```

### Usar GPU Mais Eficientemente

Se você tem GPU NVIDIA, o treinamento usará automaticamente:
- **Mixed Precision (FP16)**: 2x mais rápido, usa menos memória
- **Gradient Accumulation**: Para simular batch sizes maiores

### Aumentar Dataset

```bash
# Usar mais amostras por classe
python -m app.ml.prepare_training_data --max-per-class 2000

# Não balancear (usar todos os dados)
python -m app.ml.prepare_training_data --no-balance
```

## 🐛 Troubleshooting

### CUDA Out of Memory
```bash
# Reduzir batch size
python -m app.ml.train_model --batch-size 8
```

### Modelo não converge
```bash
# Aumentar épocas ou learning rate
python -m app.ml.train_model --epochs 5 --lr 3e-5
```

### Desbalanceamento de classes
```bash
# Verificar metadata.json após preparar dados
cat data/training/metadata.json
```

## 📦 Estrutura de Arquivos

```
data/
├── training/
│   ├── train.json           # Dados de treino
│   ├── validation.json      # Dados de validação
│   ├── test.json           # Dados de teste
│   └── metadata.json       # Metadados

models/
└── resume_classifier/
    ├── config.json         # Configuração do modelo
    ├── pytorch_model.bin   # Pesos do modelo
    ├── tokenizer_config.json
    ├── vocab.txt
    └── training_results.json  # Resultados do treino
```

## 🎯 Próximos Passos

1. ✅ Treinar modelo inicial
2. ✅ Avaliar métricas
3. 🔄 Ajustar hiperparâmetros se necessário
4. 🚀 Integrar modelo no sistema de scoring
5. 📈 Re-treinar periodicamente com novos dados

## 💡 Dicas

- **Comece pequeno**: Use `distilbert-base-uncased` primeiro
- **GPU é essencial**: Treino sem GPU pode levar horas
- **Monitore métricas**: F1 Score > 0.85 é bom para começar
- **Balance os dados**: Classes desbalanceadas prejudicam o modelo
- **Re-treine regularmente**: Com novos currículos processados

## 📚 Documentação

- [Transformers](https://huggingface.co/docs/transformers)
- [PyTorch](https://pytorch.org/docs/stable/index.html)
- [Datasets](https://huggingface.co/docs/datasets)
