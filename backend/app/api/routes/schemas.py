"""
Rotas para Schema Catalog (Fase 2)
Permite consultar schemas descobertos automaticamente
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import structlog

from app.api.dependencies import get_db
from app.services.schema_discovery_service import SchemaDiscoveryService
from app.services.semantic_field_mapper import SemanticFieldMapper

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/schemas", tags=["schemas"])


# Schemas
class FileSchemaResponse(BaseModel):
    """Response de file schema"""
    id: str
    raw_file_id: str
    filename: str
    file_format: str
    total_rows: Optional[int]
    total_columns: int
    discovered_at: str
    status: str


class ColumnInfoResponse(BaseModel):
    """Response de column info"""
    original_name: str
    normalized_name: str
    display_name: str
    semantic_aliases: List[str]
    data_type: str
    sample_values: List
    content_signature: str


class SearchColumnRequest(BaseModel):
    """Request para buscar coluna"""
    query: str
    file_schema_id: Optional[str] = None


@router.get("/", response_model=List[FileSchemaResponse])
async def list_schemas(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Lista todos os schemas descobertos
    
    Args:
        limit: Limite de resultados
        offset: Offset para paginação
        db: Sessão do banco
    
    Returns:
        Lista de schemas
    """
    try:
        schema_service = SchemaDiscoveryService(db)
        schemas = schema_service.get_all_active_schemas()
        
        # Paginação manual
        schemas = schemas[offset:offset + limit]
        
        logger.info(f"Listed {len(schemas)} schemas")
        
        return [
            FileSchemaResponse(
                id=s.id,
                raw_file_id=s.raw_file_id,
                filename=s.filename,
                file_format=s.file_format,
                total_rows=s.total_rows,
                total_columns=s.total_columns,
                discovered_at=s.discovered_at.isoformat(),
                status=s.status
            )
            for s in schemas
        ]
        
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schema_id}")
async def get_schema(
    schema_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna schema completo (com colunas)
    
    Args:
        schema_id: ID do schema
        db: Sessão do banco
    
    Returns:
        Schema completo
    """
    try:
        from app.models.file_schema import FileSchema
        
        schema = db.query(FileSchema).filter(FileSchema.id == schema_id).first()
        
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        
        logger.info(f"Retrieved schema: {schema_id}")
        
        return schema.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schema_id}/columns")
async def get_schema_columns(
    schema_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna apenas as colunas de um schema
    
    Args:
        schema_id: ID do schema
        db: Sessão do banco
    
    Returns:
        Lista de colunas
    """
    try:
        from app.models.file_schema import FileSchema
        
        schema = db.query(FileSchema).filter(FileSchema.id == schema_id).first()
        
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        
        logger.info(f"Retrieved columns for schema: {schema_id}")
        
        return {
            "schema_id": schema.id,
            "filename": schema.filename,
            "columns": schema.columns_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{schema_id}/llm-format")
async def get_schema_llm_format(
    schema_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna schema formatado para LLM
    
    Args:
        schema_id: ID do schema
        db: Sessão do banco
    
    Returns:
        Schema formatado
    """
    try:
        from app.models.file_schema import FileSchema
        
        schema = db.query(FileSchema).filter(FileSchema.id == schema_id).first()
        
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found")
        
        logger.info(f"Retrieved LLM format for schema: {schema_id}")
        
        return {
            "schema_id": schema.id,
            "filename": schema.filename,
            "formatted_text": schema.format_for_llm()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema LLM format: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-column")
async def search_column(
    request: SearchColumnRequest,
    db: Session = Depends(get_db)
):
    """
    Busca coluna por alias ou nome
    
    Args:
        request: Query de busca
        db: Sessão do banco
    
    Returns:
        Colunas encontradas
    """
    try:
        schema_service = SchemaDiscoveryService(db)
        
        matches = schema_service.search_column_by_alias(
            alias=request.query,
            file_schema_id=request.file_schema_id
        )
        
        logger.info(f"Search column '{request.query}': {len(matches)} matches")
        
        return {
            "query": request.query,
            "matches_count": len(matches),
            "matches": matches
        }
        
    except Exception as e:
        logger.error(f"Error searching column: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map-query")
async def map_query_to_fields(
    query: str,
    db: Session = Depends(get_db)
):
    """
    Mapeia query do usuário para campos reais
    
    Exemplo:
    - Query: "edital 10367 da SEINF"
    - Retorna: [
        {"field": "EDITAL N°", "value": 10367},
        {"field": "ORIGEM", "value": "SEINF"}
      ]
    
    Args:
        query: Query do usuário
        db: Sessão do banco
    
    Returns:
        Mapeamentos encontrados
    """
    try:
        mapper = SemanticFieldMapper(db)
        
        mappings = mapper.map_user_query_to_fields(query)
        
        logger.info(f"Map query '{query}': {len(mappings)} mappings")
        
        return {
            "query": query,
            "mappings_count": len(mappings),
            "mappings": [m.to_dict() for m in mappings],
            "formatted_text": mapper.format_mappings_for_llm(mappings)
        }
        
    except Exception as e:
        logger.error(f"Error mapping query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw-file/{raw_file_id}/schema")
async def get_schema_by_raw_file(
    raw_file_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna schema de um raw file
    
    Args:
        raw_file_id: ID do raw file
        db: Sessão do banco
    
    Returns:
        Schema
    """
    try:
        schema_service = SchemaDiscoveryService(db)
        
        schema = schema_service.get_schema_by_raw_file(raw_file_id)
        
        if not schema:
            raise HTTPException(status_code=404, detail="Schema not found for this raw file")
        
        logger.info(f"Retrieved schema for raw_file: {raw_file_id}")
        
        return schema.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema by raw file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

