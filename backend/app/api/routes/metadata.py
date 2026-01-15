"""
Rotas para Metadata Catalog
===========================

Endpoints para obter catálogo de metadados do sistema
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.core.database import get_db
from app.services.metadata_catalog_service import MetadataCatalogService

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/catalog")
async def get_metadata_catalog(
    municipality_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna o catálogo completo de metadados disponíveis no sistema
    
    Este endpoint é usado para dar "awareness" ao LLM sobre o que existe
    no banco de dados, permitindo decisões inteligentes sobre onde buscar.
    
    Args:
        municipality_id: ID do município
        db: Sessão do banco de dados
        
    Returns:
        Catálogo estruturado com:
        - Dados do Portal da Transparência (órgãos, editais, modalidades)
        - Dados da LOA (anos disponíveis)
        - Dados da LDO (anos disponíveis)
        - Resumo geral
    """
    try:
        catalog_service = MetadataCatalogService()
        catalog = await catalog_service.get_full_catalog(municipality_id, db)
        
        return {
            "success": True,
            "catalog": catalog
        }
        
    except Exception as e:
        logger.error(f"Error getting metadata catalog", error=str(e), municipality_id=municipality_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/summary")
async def get_metadata_summary(
    municipality_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna apenas o resumo do catálogo (versão compacta)
    
    Args:
        municipality_id: ID do município
        db: Sessão do banco de dados
        
    Returns:
        Resumo compacto do catálogo
    """
    try:
        catalog_service = MetadataCatalogService()
        catalog = await catalog_service.get_full_catalog(municipality_id, db)
        
        # Retornar apenas resumo + informações essenciais
        return {
            "success": True,
            "summary": catalog.get("summary", {}),
            "municipality": catalog.get("municipality", {}),
            "portal": {
                "total_documents": catalog["portal_transparency"]["total_documents"],
                "organs": catalog["portal_transparency"]["organs"],
                "editals_range": catalog["portal_transparency"]["editals_range"],
            },
            "loa": {
                "total_documents": catalog["loa"]["total_documents"],
                "years": catalog["loa"]["years"]
            },
            "ldo": {
                "total_documents": catalog["ldo"]["total_documents"],
                "years": catalog["ldo"]["years"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metadata summary", error=str(e), municipality_id=municipality_id)
        raise HTTPException(status_code=500, detail=str(e))

