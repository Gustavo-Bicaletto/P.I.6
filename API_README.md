# ResumAI API

API REST para avaliação inteligente de currículos usando ML + Rule-Based Scoring.

## 🚀 Quick Start

### 1. Instalar dependências

```bash
pip install -r requirements.txt
pip install -r requirements-api.txt
```

### 2. Iniciar servidor

```bash
python app/api.py
```

Ou com uvicorn diretamente:

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

### 3. Acessar documentação

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📡 Endpoints

### Evaluation

#### POST /evaluate
Avalia currículo com texto direto

```bash
curl -X POST "http://localhost:8000/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Desenvolvedor Python com 5 anos...",
    "job_description": "Buscamos desenvolvedor Python sênior..."
  }'
```

#### POST /evaluate/{resume_id}
Avalia currículo do MongoDB por ID

```bash
curl -X POST "http://localhost:8000/evaluate/65abc123def456" \
  -H "Content-Type: application/json" \
  -d '{"job_description": "Vaga de Python Developer..."}'
```

### Ranking

#### POST /rank
Rankeia múltiplos currículos para uma vaga

```bash
curl -X POST "http://localhost:8000/rank" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Desenvolvedor Python Sênior...",
    "limit": 10
  }'
```

### Features

#### POST /extract
Extrai features sem avaliar (útil para debugging)

```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"resume_text": "João Silva, 5 anos Python..."}'
```

### Monitoring

#### GET /health
Health check da API

```bash
curl "http://localhost:8000/health"
```

#### GET /stats
Estatísticas gerais do sistema

```bash
curl "http://localhost:8000/stats"
```

## 📊 Response Format

### Evaluation Response
```json
{
  "score": 78.5,
  "label": "Bom",
  "semantic_match": 0.92,
  "subscores": {
    "skills": 0.85,
    "experience": 0.90,
    "impact": 0.75,
    "semantic": 0.92,
    "quality": 0.80
  },
  "method": "hybrid",
  "is_experienced": true,
  "explanation": {
    "top_up": ["experience", "skills", "semantic"],
    "top_down": ["projects", "certs"]
  }
}
```

### Ranking Response
```json
{
  "job_description": "Vaga de Python Developer...",
  "total_evaluated": 15,
  "top_candidates": [
    {
      "rank": 1,
      "resume_id": "65abc123",
      "filename": "joao_silva.pdf",
      "score": 85.2,
      "label": "Muito Bom",
      "semantic_match": 0.94,
      "is_experienced": true,
      "skills": ["python", "django", "aws", "docker", "mongodb"]
    }
  ]
}
```

## 🧪 Testing

Execute o script de testes:

```bash
python test_api.py
```

Ou use Postman/Insomnia com a collection disponível em `/docs`.

## 🔒 Autenticação (Futuro)

Para produção, adicionar autenticação via API Key:

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != "your-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key
```

Uso:
```python
@app.post("/evaluate", dependencies=[Depends(verify_api_key)])
async def evaluate_resume(...):
    ...
```

## 📦 Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-api.txt

COPY app/ ./app/
COPY models/ ./models/

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build e run:
```bash
docker build -t resumai-api .
docker run -p 8000:8000 resumai-api
```

## 🌐 Cloud Deployment

### Heroku
```bash
heroku create resumai-api
git push heroku main
```

### Railway
```bash
railway login
railway init
railway up
```

### Render
Criar `render.yaml`:
```yaml
services:
  - type: web
    name: resumai-api
    env: python
    buildCommand: pip install -r requirements.txt -r requirements-api.txt
    startCommand: uvicorn app.api:app --host 0.0.0.0 --port $PORT
```

## 📈 Monitoring

### Logs
```bash
# Ver logs em tempo real
tail -f app.log
```

### Prometheus Metrics (Futuro)
```bash
pip install prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

## 🎯 Performance

- **Throughput**: ~100 req/s (RTX 4060 Ti)
- **Latency**: ~50-100ms por avaliação
- **Semantic Model**: 95.6% Pearson correlation
- **Accuracy**: MAE 0.02 (2% error)

## 🤝 Integração Frontend

### JavaScript/React
```javascript
const evaluateResume = async (resumeText, jobDescription) => {
  const response = await fetch('http://localhost:8000/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_text: resumeText, job_description: jobDescription })
  });
  return await response.json();
};
```

### Python Client
```python
import requests

def evaluate_resume(resume_text: str, job_desc: str = None):
    response = requests.post(
        "http://localhost:8000/evaluate",
        json={"resume_text": resume_text, "job_description": job_desc}
    )
    return response.json()
```

## 📝 License

MIT License - ResumAI © 2024
