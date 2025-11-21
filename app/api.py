#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ResumAI API - FastAPI REST API for Resume Evaluation
Endpoints para avaliar currículos usando ML + Rule-Based Scoring
"""
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.db.mongo import get_db
from app.scoring.hybrid_scorer import HybridScorer
from app.scoring.use_case import evaluate_resume_from_doc

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="ResumAI API",
    description="API para avaliação inteligente de currículos usando ML e análise semântica",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - permite frontend acessar API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Scorer híbrido singleton
_scorer = None

def get_scorer() -> HybridScorer:
    """Dependency injection para scorer"""
    global _scorer
    if _scorer is None:
        logger.info("Carregando HybridScorer...")
        _scorer = HybridScorer()
        logger.info("HybridScorer carregado com sucesso!")
    return _scorer


# ==================== Modelos Pydantic ====================

class EvaluationRequest(BaseModel):
    resume_text: str = Field(..., description="Texto do currículo", min_length=100)
    job_description: Optional[str] = Field(None, description="Descrição da vaga (opcional)")
    
    class Config:
        schema_extra = {
            "example": {
                "resume_text": "Desenvolvedor Python com 5 anos de experiência...",
                "job_description": "Buscamos desenvolvedor Python sênior com experiência em Django..."
            }
        }


class EvaluationResponse(BaseModel):
    score: float = Field(..., description="Score final (0-100)")
    label: str = Field(..., description="Label qualitativo (Ruim/Regular/Bom/Muito Bom/Excelente)")
    semantic_match: Optional[float] = Field(None, description="Score de match semântico (0-1)")
    subscores: Dict[str, float] = Field(..., description="Subscores detalhados")
    method: str = Field(..., description="Método usado (hybrid/rule_based/ml_only)")
    is_experienced: bool = Field(..., description="Classificação de experiência")
    explanation: Dict[str, List[str]] = Field(..., description="Explicação dos subscores")
    
    class Config:
        schema_extra = {
            "example": {
                "score": 78.5,
                "label": "Bom",
                "semantic_match": 0.92,
                "subscores": {
                    "skills": 0.85,
                    "experience": 0.90,
                    "impact": 0.75,
                    "semantic": 0.92
                },
                "method": "hybrid",
                "is_experienced": True,
                "explanation": {
                    "top_up": ["experience", "skills", "semantic"],
                    "top_down": ["projects", "certs"]
                }
            }
        }


class RankingRequest(BaseModel):
    job_description: str = Field(..., description="Descrição da vaga")
    resume_ids: Optional[List[str]] = Field(None, description="IDs específicos (opcional)")
    limit: int = Field(10, description="Número máximo de resultados", ge=1, le=100)


class RankingResponse(BaseModel):
    job_description: str
    total_evaluated: int
    top_candidates: List[Dict[str, Any]]


class FeatureExtractionResponse(BaseModel):
    skills: List[str]
    years_experience: float
    tokens: int
    has_email: bool
    has_phone: bool
    metrics_hits: int
    project_hits: int
    sections_present: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    models_loaded: bool
    database_connected: bool
    version: str


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz - informações da API"""
    return {
        "api": "ResumAI",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "evaluate": "/evaluate",
            "evaluate_by_id": "/evaluate/{resume_id}",
            "rank": "/rank",
            "extract": "/extract",
            "health": "/health"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """Health check - verifica status da API e dependências"""
    
    # Verificar conexão com MongoDB
    db_connected = False
    try:
        db = get_db()
        db.command('ping')
        db_connected = True
    except Exception as e:
        logger.error(f"Erro ao conectar MongoDB: {e}")
    
    # Verificar se modelos estão carregados
    models_loaded = _scorer is not None
    
    return HealthResponse(
        status="healthy" if (db_connected and models_loaded) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=models_loaded,
        database_connected=db_connected,
        version="1.0.0"
    )


@app.post("/evaluate", response_model=EvaluationResponse, tags=["Evaluation"])
async def evaluate_resume(
    request: EvaluationRequest,
    scorer: HybridScorer = Depends(get_scorer)
):
    """
    Avalia currículo usando sistema híbrido (ML + Rule-Based)
    
    - **resume_text**: Texto do currículo (obrigatório)
    - **job_description**: Descrição da vaga (opcional, melhora semantic match)
    
    Retorna score final, subscores detalhados e classificação de experiência.
    """
    try:
        # Preparar documento
        doc = {
            "resume_text_clean": request.resume_text,
            "job_description": request.job_description
        }
        
        # Avaliar com scorer híbrido
        result = scorer.score(doc)
        
        # Extrair semantic score se disponível
        semantic_match = None
        if request.job_description:
            semantic_match = result.get('rb_subscores', {}).get('semantic', None)
        
        return EvaluationResponse(
            score=result['score'],
            label=result['label'],
            semantic_match=semantic_match,
            subscores=result['rb_subscores'],
            method=result.get('method', 'hybrid'),
            is_experienced=result.get('is_experienced', False),
            explanation=result.get('explain', {})
        )
        
    except Exception as e:
        logger.error(f"Erro ao avaliar currículo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar currículo: {str(e)}")


@app.post("/evaluate/{resume_id}", response_model=EvaluationResponse, tags=["Evaluation"])
async def evaluate_by_id(
    resume_id: str,
    job_description: Optional[str] = None,
    scorer: HybridScorer = Depends(get_scorer)
):
    """
    Avalia currículo do MongoDB por ID
    
    - **resume_id**: ObjectId do currículo no MongoDB
    - **job_description**: Descrição da vaga (opcional, query parameter)
    """
    try:
        # Buscar currículo no MongoDB
        db = get_db()
        doc = db["dados_processados"].find_one({"_id": ObjectId(resume_id)})
        
        if not doc:
            raise HTTPException(status_code=404, detail=f"Currículo {resume_id} não encontrado")
        
        # Adicionar job_description se fornecido
        if job_description:
            doc["job_description"] = job_description
        
        # Avaliar
        result = scorer.score(doc)
        
        semantic_match = None
        if job_description:
            semantic_match = result.get('rb_subscores', {}).get('semantic', None)
        
        return EvaluationResponse(
            score=result['score'],
            label=result['label'],
            semantic_match=semantic_match,
            subscores=result['rb_subscores'],
            method=result.get('method', 'hybrid'),
            is_experienced=result.get('is_experienced', False),
            explanation=result.get('explain', {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao avaliar currículo {resume_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rank", response_model=RankingResponse, tags=["Ranking"])
async def rank_resumes(
    request: RankingRequest,
    scorer: HybridScorer = Depends(get_scorer)
):
    """
    Rankeia currículos para uma vaga específica
    
    - **job_description**: Descrição da vaga
    - **resume_ids**: Lista de IDs específicos (opcional)
    - **limit**: Número máximo de resultados (padrão: 10)
    
    Retorna top N candidatos ordenados por score.
    """
    try:
        db = get_db()
        
        # Buscar currículos
        query = {"resume_text_clean": {"$exists": True, "$ne": ""}}
        if request.resume_ids:
            query["_id"] = {"$in": [ObjectId(id) for id in request.resume_ids]}
        
        resumes = list(db["dados_processados"].find(query).limit(request.limit * 2))
        
        if not resumes:
            raise HTTPException(status_code=404, detail="Nenhum currículo encontrado")
        
        # Avaliar todos
        results = []
        for resume in resumes:
            try:
                resume["job_description"] = request.job_description
                evaluation = scorer.score(resume)
                
                results.append({
                    "resume_id": str(resume["_id"]),
                    "filename": resume.get("filename", "unknown"),
                    "score": evaluation['score'],
                    "label": evaluation['label'],
                    "semantic_match": evaluation.get('rb_subscores', {}).get('semantic', 0),
                    "is_experienced": evaluation.get('is_experienced', False),
                    "skills": resume.get("skills", [])[:5]  # Top 5 skills
                })
            except Exception as e:
                logger.warning(f"Erro ao avaliar currículo {resume['_id']}: {e}")
                continue
        
        # Ordenar por score
        results.sort(key=lambda x: x['score'], reverse=True)
        top_results = results[:request.limit]
        
        # Adicionar ranking
        for i, result in enumerate(top_results, 1):
            result['rank'] = i
        
        return RankingResponse(
            job_description=request.job_description,
            total_evaluated=len(results),
            top_candidates=top_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao rankear currículos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract", response_model=FeatureExtractionResponse, tags=["Features"])
async def extract_features(request: EvaluationRequest):
    """
    Extrai features de um currículo sem avaliar
    
    Útil para análise exploratória e debugging.
    """
    try:
        from app.scoring.use_case import build_features_from_doc
        
        doc = {
            "resume_text_clean": request.resume_text,
            "job_description": request.job_description
        }
        
        features = build_features_from_doc(doc)
        
        return FeatureExtractionResponse(
            skills=features.get('skills', []),
            years_experience=features.get('years_total', 0),
            tokens=features.get('tokens', 0),
            has_email=features.get('has_email', False),
            has_phone=features.get('has_phone', False),
            metrics_hits=features.get('metrics_hits', 0),
            project_hits=features.get('project_hits', 0),
            sections_present=features.get('sections_present', 0)
        )
        
    except Exception as e:
        logger.error(f"Erro ao extrair features: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["Analytics"])
async def get_statistics():
    """Estatísticas gerais do sistema"""
    try:
        db = get_db()
        
        total_resumes = db["dados_processados"].count_documents({})
        total_evaluations = db["evaluations"].count_documents({})
        
        # Score médio das últimas 100 avaliações
        recent_evals = list(db["evaluations"].find(
            {},
            {"scores.final": 1}
        ).sort("created_at", -1).limit(100))
        
        avg_score = 0
        if recent_evals:
            scores = [e.get('scores', {}).get('final', 0) for e in recent_evals]
            avg_score = sum(scores) / len(scores)
        
        return {
            "total_resumes": total_resumes,
            "total_evaluations": total_evaluations,
            "average_score_recent": round(avg_score, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Eventos de Startup/Shutdown ====================

@app.on_event("startup")
async def startup_event():
    """Inicialização da API"""
    logger.info("🚀 ResumAI API iniciando...")
    logger.info("Carregando modelos ML...")
    
    # Pre-carregar scorer
    try:
        get_scorer()
        logger.info("✅ Modelos carregados com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelos: {e}")
    
    logger.info("✅ ResumAI API pronta!")
    logger.info("📖 Documentação: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup ao desligar API"""
    logger.info("🛑 ResumAI API desligando...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
