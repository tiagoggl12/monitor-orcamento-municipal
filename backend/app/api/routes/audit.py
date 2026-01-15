"""
Rotas de Auditoria e Verificação (Fase 1)
Permite verificação judicial e rastreamento completo
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
import structlog

from app.api.dependencies import get_db
from app.services.data_lineage_service import DataLineageService
from app.services.raw_file_service import RawFileService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


# Schemas
class VerificationResponse(BaseModel):
    """Response de verificação"""
    lineage_entry: Dict[str, Any]
    raw_file: Dict[str, Any]
    parsed_data: Optional[Dict[str, Any]]
    integrity_check: Dict[str, Any]
    verification_signature: str


class LineageResponse(BaseModel):
    """Response de lineage"""
    raw_file: Dict[str, Any]
    lineage_entries: list
    parsed_data_count: int
    operations_summary: Dict[str, Any]
    chat_usage_count: int


class CitationsResponse(BaseModel):
    """Response de citações"""
    message_id: str
    citations_count: int
    citations: list


@router.get("/verify/{lineage_id}", response_model=VerificationResponse)
async def verify_lineage_entry(
    lineage_id: str,
    db: Session = Depends(get_db)
):
    """
    Verifica um lineage entry (USO JUDICIAL)
    
    Retorna:
    - Dados completos do lineage
    - Verificação de integridade (hash)
    - Assinatura de verificação
    
    Args:
        lineage_id: ID do lineage entry
        db: Sessão do banco
    
    Returns:
        Dados de verificação completos
    """
    try:
        lineage_service = DataLineageService(db)
        verification_data = lineage_service.verify_lineage_entry(lineage_id)
        
        if "error" in verification_data:
            raise HTTPException(status_code=404, detail=verification_data["error"])
        
        logger.info(
            "Lineage entry verified",
            lineage_id=lineage_id,
            integrity=verification_data["integrity_check"]["passed"]
        )
        
        return verification_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying lineage entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/file/{raw_file_id}", response_model=LineageResponse)
async def get_file_lineage(
    raw_file_id: str,
    include_chat_usage: bool = True,
    db: Session = Depends(get_db)
):
    """
    Retorna lineage completo de um arquivo
    
    Args:
        raw_file_id: ID do raw file
        include_chat_usage: Incluir uso em chats
        db: Sessão do banco
    
    Returns:
        Lineage completo do arquivo
    """
    try:
        lineage_service = DataLineageService(db)
        lineage_data = lineage_service.get_file_lineage(
            raw_file_id=raw_file_id,
            include_chat_usage=include_chat_usage
        )
        
        if "error" in lineage_data:
            raise HTTPException(status_code=404, detail=lineage_data["error"])
        
        logger.info(
            "File lineage retrieved",
            raw_file_id=raw_file_id,
            operations=len(lineage_data["lineage_entries"])
        )
        
        return lineage_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/message/{message_id}", response_model=CitationsResponse)
async def get_message_citations(
    message_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna citações de uma mensagem de chat
    
    Mostra EXATAMENTE de onde veio cada informação:
    - Arquivo original
    - Linha exata
    - Hash para verificação
    - Link de verificação
    
    Args:
        message_id: ID da mensagem
        db: Sessão do banco
    
    Returns:
        Citações rastreáveis
    """
    try:
        lineage_service = DataLineageService(db)
        citations_data = lineage_service.get_data_lineage_for_chat_message(
            message_id=message_id
        )
        
        logger.info(
            "Message citations retrieved",
            message_id=message_id,
            citations=citations_data["citations_count"]
        )
        
        return citations_data
        
    except Exception as e:
        logger.error(f"Error getting message citations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw-file/{raw_file_id}")
async def get_raw_file_info(
    raw_file_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna informações de um raw file
    
    Args:
        raw_file_id: ID do raw file
        db: Sessão do banco
    
    Returns:
        Informações do arquivo
    """
    try:
        raw_file_service = RawFileService(db)
        raw_file = raw_file_service.get_raw_file_by_id(raw_file_id)
        
        if not raw_file:
            raise HTTPException(status_code=404, detail="Raw file not found")
        
        logger.info(
            "Raw file info retrieved",
            raw_file_id=raw_file_id
        )
        
        return raw_file.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting raw file info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/raw-file/{raw_file_id}/verify-integrity")
async def verify_file_integrity(
    raw_file_id: str,
    db: Session = Depends(get_db)
):
    """
    Verifica integridade de um arquivo (hash)
    
    Args:
        raw_file_id: ID do raw file
        db: Sessão do banco
    
    Returns:
        Resultado da verificação
    """
    try:
        raw_file_service = RawFileService(db)
        raw_file = raw_file_service.get_raw_file_by_id(raw_file_id)
        
        if not raw_file:
            raise HTTPException(status_code=404, detail="Raw file not found")
        
        integrity_ok = raw_file_service.verify_integrity(raw_file)
        
        logger.info(
            "File integrity verified",
            raw_file_id=raw_file_id,
            passed=integrity_ok
        )
        
        return {
            "raw_file_id": raw_file_id,
            "integrity_passed": integrity_ok,
            "sha256_hash": raw_file.sha256_hash,
            "filename": raw_file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying file integrity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas gerais do sistema
    
    Args:
        db: Sessão do banco
    
    Returns:
        Estatísticas
    """
    try:
        lineage_service = DataLineageService(db)
        stats = lineage_service.get_statistics()
        
        logger.info("Statistics retrieved")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

