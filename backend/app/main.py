"""
Monitor de Orçamento Público Municipal
Backend API - FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import structlog
from datetime import datetime

from app.core.config import settings
from app.core.database import init_db
from app.schemas import ErrorResponse, HealthCheckResponse

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events da aplicação
    """
    # Startup
    logger.info("Starting Monitor de Orçamento Público Municipal API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Validar API Keys
    try:
        if settings.ENVIRONMENT == "production":
            settings.validate_api_keys()
            logger.info("API keys validated successfully")
    except ValueError as e:
        logger.error(f"API key validation failed: {e}")
        if settings.ENVIRONMENT == "production":
            raise
        else:
            logger.warning("Running in development mode without valid API keys")
    
    # Inicializar banco de dados
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Verificar conexão com ChromaDB
    try:
        from app.services.vector_db import VectorDBService
        vector_db = VectorDBService()
        logger.info("ChromaDB connection verified")
    except Exception as e:
        logger.warning(f"ChromaDB connection check failed: {e}")
    
    # Verificar conexão com Redis
    try:
        from app.services.cache_service import get_cache_service
        cache_service = await get_cache_service()
        if await cache_service.health_check():
            logger.info("Redis connection verified")
        else:
            logger.warning("Redis connection check failed")
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
    
    logger.info("Application startup complete")
    logger.info(f"API docs available at: http://localhost:{settings.BACKEND_PORT}/docs")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Monitor de Orçamento Público Municipal API")
    
    # Fechar conexões
    try:
        from app.services.portal_client import close_portal_client
        from app.services.cache_service import close_cache_service
        await close_portal_client()
        await close_cache_service()
        logger.info("Connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing connections: {e}")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema inteligente para monitoramento e análise de gastos públicos municipais",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ====================================
# Middleware de CORS
# ====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================================
# Exception Handlers
# ====================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para erros de validação do Pydantic
    """
    logger.error("Validation error", errors=exc.errors())
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="ValidationError",
            message="Dados inválidos fornecidos",
            details={"errors": exc.errors()}
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler para exceções gerais
    """
    logger.error("Unhandled exception", exception=str(exc), exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="Erro interno do servidor",
            details={"exception": str(exc)} if settings.DEBUG else None
        ).model_dump()
    )


# ====================================
# Health Check Endpoint
# ====================================

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health Check",
    description="Verifica o status da aplicação e seus serviços"
)
async def health_check():
    """
    Endpoint de health check para monitoramento
    """
    services = {}
    
    # Verificar banco de dados
    try:
        from app.core.database import engine
        with engine.connect() as conn:
            services["database"] = "connected"
    except Exception as e:
        services["database"] = f"error: {str(e)}"
        logger.error("Database health check failed", error=str(e))
    
    # Verificar Gemini API Key
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here":
        services["gemini_api"] = "configured"
    else:
        services["gemini_api"] = "not_configured"
    
    # Verificar ChromaDB
    try:
        from app.services.vector_db import VectorDBService
        vector_db = VectorDBService()
        services["chromadb"] = "connected"
    except Exception as e:
        services["chromadb"] = f"error: {str(e)}"
        logger.error("ChromaDB health check failed", error=str(e))
    
    # Verificar Redis
    try:
        from app.services.cache_service import get_cache_service
        cache_service = await get_cache_service()
        if await cache_service.health_check():
            services["redis"] = "connected"
        else:
            services["redis"] = "error: connection failed"
    except Exception as e:
        services["redis"] = f"error: {str(e)}"
        logger.error("Redis health check failed", error=str(e))
    
    # Status geral
    status = "ok" if all(
        v == "connected" or v == "configured" 
        for k, v in services.items()
    ) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        version=settings.APP_VERSION,
        services=services
    )


@app.get(
    "/",
    tags=["Root"],
    summary="Root Endpoint",
    description="Informações básicas da API"
)
async def root():
    """
    Endpoint raiz da API
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": f"http://localhost:{settings.BACKEND_PORT}/docs",
        "health": f"http://localhost:{settings.BACKEND_PORT}/health",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# ====================================
# Incluir Routers (API Routes)
# ====================================

from app.api.routes import municipalities, documents, portal, chat, portal_ingestion, metadata, audit, schemas, dashboard, ldo

app.include_router(
    municipalities.router,
    prefix="/api/municipalities",
    tags=["Municipalities"]
)

app.include_router(
    documents.router,
    prefix="/api/documents",
    tags=["Documents"]
)

app.include_router(
    portal.router,
    prefix="/api",
    tags=["Portal da Transparência"]
)

app.include_router(
    portal_ingestion.router,
    prefix="/api",
    tags=["Portal Ingestion"]
)

app.include_router(
    chat.router,
    prefix="/api",
    tags=["Chat"]
)

app.include_router(
    metadata.router,
    prefix="/api/metadata",
    tags=["Metadata Catalog"]
)

app.include_router(
    audit.router,
    prefix="/api",
    tags=["Audit & Verification"]
)

app.include_router(
    schemas.router,
    prefix="/api",
    tags=["Schema Catalog"]
)

app.include_router(
    dashboard.router,
    prefix="/api/dashboard",
    tags=["Dashboard LOA/LDO"]
)

app.include_router(
    ldo.router,
    prefix="/api",
    tags=["LDO"]
)


# ====================================
# Executar aplicação (para desenvolvimento)
# ====================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

