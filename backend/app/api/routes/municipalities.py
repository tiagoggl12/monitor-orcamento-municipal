"""
Rotas para gerenciamento de municípios
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import structlog

from app.core.database import get_db
from app.models import Municipality, Document
from app.schemas import (
    MunicipalityCreate,
    MunicipalityResponse,
    MunicipalityDocumentsStatus,
    DocumentStatusResponse,
    ErrorResponse
)
from app.api.dependencies import get_municipality_or_404, get_municipality_by_params

router = APIRouter()
logger = structlog.get_logger()


@router.post(
    "/",
    response_model=MunicipalityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Município",
    description="Cria um novo município ou retorna existente",
    responses={
        201: {"description": "Município criado com sucesso"},
        200: {"description": "Município já existe"},
        422: {"model": ErrorResponse, "description": "Dados inválidos"}
    }
)
async def create_municipality(
    municipality_data: MunicipalityCreate,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova configuração de município.
    Se já existir município com mesmo nome, estado e ano, retorna o existente.
    """
    logger.info(
        "Creating municipality",
        name=municipality_data.name,
        state=municipality_data.state,
        year=municipality_data.year
    )
    
    # Verificar se já existe
    existing = await get_municipality_by_params(
        name=municipality_data.name,
        state=municipality_data.state,
        year=municipality_data.year,
        db=db
    )
    
    if existing:
        logger.info("Municipality already exists", municipality_id=existing.id)
        return MunicipalityResponse(**existing.to_dict())
    
    # Criar novo município
    municipality = Municipality(
        name=municipality_data.name,
        state=municipality_data.state.upper(),
        year=municipality_data.year
    )
    
    db.add(municipality)
    db.commit()
    db.refresh(municipality)
    
    logger.info("Municipality created successfully", municipality_id=municipality.id)
    
    return MunicipalityResponse(**municipality.to_dict())


@router.get(
    "/states",
    response_model=List[str],
    summary="Listar Estados",
    description="Retorna lista de estados únicos cadastrados"
)
async def list_states(db: Session = Depends(get_db)):
    """
    Lista todos os estados (UF) que possuem municípios cadastrados
    """
    states = db.query(Municipality.state).distinct().order_by(Municipality.state).all()
    return [state[0] for state in states]


@router.get(
    "/",
    response_model=List[MunicipalityResponse],
    summary="Listar Municípios",
    description="Lista todos os municípios configurados no sistema, opcionalmente filtrados por estado"
)
async def list_municipalities(
    state: str = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """
    Lista todos os municípios cadastrados no sistema.
    Pode filtrar por estado (UF) usando o parâmetro ?state=CE
    """
    query = db.query(Municipality)
    
    if state:
        query = query.filter(Municipality.state == state.upper())
    
    municipalities = query.order_by(Municipality.name).offset(skip).limit(limit).all()
    
    return [MunicipalityResponse(**m.to_dict()) for m in municipalities]


@router.get(
    "/{municipality_id}",
    response_model=MunicipalityResponse,
    summary="Obter Município",
    description="Busca informações de um município por ID",
    responses={
        200: {"description": "Município encontrado"},
        404: {"model": ErrorResponse, "description": "Município não encontrado"}
    }
)
async def get_municipality(
    municipality: Municipality = Depends(get_municipality_or_404)
):
    """
    Retorna informações de um município específico
    """
    return MunicipalityResponse(**municipality.to_dict())


@router.get(
    "/{municipality_id}/status",
    response_model=MunicipalityDocumentsStatus,
    summary="Status dos Documentos",
    description="Verifica se LOA e LDO estão processados para o município",
    responses={
        200: {"description": "Status obtido com sucesso"},
        404: {"model": ErrorResponse, "description": "Município não encontrado"}
    }
)
async def get_municipality_documents_status(
    municipality: Municipality = Depends(get_municipality_or_404),
    db: Session = Depends(get_db)
):
    """
    Verifica o status dos documentos (LOA e LDO) de um município.
    Retorna se os documentos já foram processados e se o sistema está pronto para chat.
    """
    logger.info("Checking documents status", municipality_id=municipality.id)
    
    # Buscar documentos LOA e LDO
    loa_doc = db.query(Document).filter(
        Document.municipality_id == municipality.id,
        Document.type == "LOA"
    ).order_by(Document.version.desc()).first()
    
    ldo_doc = db.query(Document).filter(
        Document.municipality_id == municipality.id,
        Document.type == "LDO"
    ).order_by(Document.version.desc()).first()
    
    # Verificar se estão processados
    loa_processed = loa_doc is not None and loa_doc.status == "completed"
    ldo_processed = ldo_doc is not None and ldo_doc.status == "completed"
    ready_for_chat = loa_processed and ldo_processed
    
    return MunicipalityDocumentsStatus(
        municipality=MunicipalityResponse(**municipality.to_dict()),
        loa_processed=loa_processed,
        ldo_processed=ldo_processed,
        loa_document=DocumentStatusResponse(**loa_doc.to_dict()) if loa_doc else None,
        ldo_document=DocumentStatusResponse(**ldo_doc.to_dict()) if ldo_doc else None,
        ready_for_chat=ready_for_chat
    )


@router.get(
    "/search/{name}/{state}/{year}",
    response_model=MunicipalityDocumentsStatus,
    summary="Buscar Município por Parâmetros",
    description="Busca município por nome, estado e ano e retorna status dos documentos",
    responses={
        200: {"description": "Município encontrado"},
        404: {"model": ErrorResponse, "description": "Município não encontrado"}
    }
)
async def search_municipality(
    name: str,
    state: str,
    year: int,
    db: Session = Depends(get_db)
):
    """
    Busca município por nome, estado e ano.
    Útil para verificar se documentos já foram processados antes de solicitar upload.
    """
    municipality = await get_municipality_by_params(name, state, year, db)
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município '{name}/{state}/{year}' não encontrado no sistema. "
                   "Crie uma nova configuração ou faça upload dos documentos."
        )
    
    # Retornar status dos documentos
    return await get_municipality_documents_status(municipality, db)


@router.delete(
    "/{municipality_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar Município",
    description="Remove município e todos os seus dados (documentos, sessões, etc)",
    responses={
        204: {"description": "Município deletado com sucesso"},
        404: {"model": ErrorResponse, "description": "Município não encontrado"}
    }
)
async def delete_municipality(
    municipality: Municipality = Depends(get_municipality_or_404),
    db: Session = Depends(get_db)
):
    """
    Remove município e todos os dados associados (cascade).
    ⚠️ ATENÇÃO: Esta ação não pode ser desfeita!
    """
    logger.warning("Deleting municipality", municipality_id=municipality.id)
    
    db.delete(municipality)
    db.commit()
    
    logger.info("Municipality deleted successfully", municipality_id=municipality.id)
    
    return None

