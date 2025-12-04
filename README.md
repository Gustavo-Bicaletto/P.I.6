# ResumAI - Sistema de Análise Inteligente de Currículos

> Projeto Integrador 6 - PUC Campinas

Sistema inteligente de análise e avaliação de currículos utilizando **Machine Learning** e **Processamento de Linguagem Natural (NLP)** para fornecer feedback detalhado e profissional sobre qualidade de currículos.

---

## 🎯 Sobre o Projeto

O **ResumAI** é uma ferramenta desenvolvida para auxiliar candidatos a melhorarem seus currículos através de análise automatizada baseada em inteligência artificial. O sistema avalia múltiplos aspectos do currículo e fornece feedback detalhado e acionável para otimização.

### Problema Solucionado

- **Candidatos** têm dificuldade em saber se seus currículos estão bem estruturados
- Falta de feedback objetivo sobre pontos fortes e fracos
- Desconhecimento sobre o que recrutadores buscam em currículos
- Necessidade de orientação específica para melhorias

### Solução

Sistema automatizado que:
- Analisa currículos em **PDF e TXT**
- Fornece **score de 0-100** baseado em múltiplos critérios
- Identifica **pontos fortes e oportunidades de melhoria**
- Oferece **recomendações personalizadas e detalhadas**
- Classifica automaticamente perfil: **Experiente vs Júnior/Estagiário**

---

## ✨ Funcionalidades

### Análise Automática
- 📄 **Upload de currículos** em PDF ou TXT via interface web
- 🤖 **Classificação automática** de perfil (Experiente/Júnior)
- 📊 **Score final** de 0-100 pontos
- 🎯 **Avaliação multi-critério**:
  - Habilidades técnicas
  - Anos de experiência
  - Qualidade do documento
  - Projetos mencionados
  - Certificações
  - Métricas e resultados quantificáveis
  - Informações de contato

### Feedback Inteligente
- ✅ **Pontos fortes** identificados automaticamente
- ⚠️ **Oportunidades de melhoria** com explicações detalhadas
- 💡 **Recomendações acionáveis** específicas por nível de score
- 📈 **Planos de ação** personalizados (7-21 dias)
- 🔍 **Análise contextualizada** por perfil profissional

### Interface Web Moderna
- 🎨 Design moderno e responsivo
- 🖱️ **Drag-and-drop** para upload de arquivos
- ⚡ Análise em tempo real
- 📱 Compatível com dispositivos móveis
- 🌐 Interface em português brasileiro

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.10+**
- **Flask 3.0** - Framework web
- **PyTorch 2.x** - Deep Learning
- **Transformers (Hugging Face)** - Modelos BERT
- **spaCy 3.8** - Processamento de linguagem natural
- **scikit-learn** - Machine Learning tradicional
- **PyPDF2** - Extração de texto de PDFs

### Frontend
- **HTML5**
- **CSS3** (Design moderno com gradientes)
- **JavaScript Vanilla** (Sem dependências externas)

### Machine Learning
- **BERT** - Classificação de experiência (Júnior vs Experiente)
- **Sentence Transformers** - Similaridade semântica
- **Unsupervised Scoring** - Clustering para confiança
- **Regex + NLP** - Extração de features

### Infraestrutura
- **MongoDB** - Armazenamento de dados (opcional)
- **Git/GitHub** - Controle de versão

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐
│  Interface Web  │ (HTML/CSS/JS)
│  (index.html)   │
└────────┬────────┘
         │ HTTP POST /api/analyze
         ▼
┌─────────────────┐
│   Flask Server  │ (web_server.py)
│   (Port 5000)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Text Extractor │ (PyPDF2)
│  (PDF → Text)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Feature Builder │ (use_case.py)
│  - Skills       │
│  - Experience   │
│  - Projects     │
│  - Metrics      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Hybrid Scorer   │ (hybrid_scorer.py)
│  - ML Model     │
│  - Rule-based   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response JSON   │
│  - Score        │
│  - Features     │
│  - Feedback     │
└─────────────────┘
```

---

## 📦 Instalação

### Pré-requisitos
- Python 3.10 ou superior
- pip (gerenciador de pacotes Python)
- 2GB de espaço em disco (para modelos ML)

### Passo 1: Clonar o Repositório
```bash
git clone https://github.com/Gustavo-Bicaletto/P.I.6.git
cd P.I.6-1
```

### Passo 2: Criar Ambiente Virtual
```bash
python -m venv .venv
```

### Passo 3: Ativar Ambiente Virtual
**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### Passo 4: Instalar Dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### Passo 5: Baixar Modelos spaCy
```bash
python -m spacy download pt_core_news_sm
python -m spacy download pt_core_news_md
```

---

## 🚀 Como Usar

### Iniciar o Servidor
```bash
python web_server.py
```

O servidor iniciará em: `http://localhost:5000`

### Acessar a Interface Web
1. Abra seu navegador
2. Acesse: `http://localhost:5000`
3. Arraste um arquivo PDF ou TXT para a área de upload (ou clique para selecionar)
4. Aguarde a análise (5-15 segundos)
5. Visualize o resultado detalhado

### Formatos Aceitos
- **PDF**: `.pdf` (até 16MB)
- **TXT**: `.txt` (até 16MB)

### Exemplo de Uso via Terminal
Para testar sem interface web:
```bash
python test_complete.py seu_curriculo.txt
```

---

## 📄 Licença

Este projeto é parte do Projeto Integrador 6 da PUC Campinas.

---
