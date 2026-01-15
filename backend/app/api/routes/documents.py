"""
Rotas para gerenciamento de documentos (LOA/LDO)
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import List, Dict
import structlog
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import subprocess
import re

from app.core.database import get_db
from app.core.config import settings
from app.models import Document, Municipality
from app.schemas import (
    DocumentStatusResponse,
    UploadResponse,
    ErrorResponse
)
from app.api.dependencies import get_municipality_or_404
from app.services.file_validator import FileValidator
from app.services.file_manager import FileManager
from app.services.document_processor import DocumentProcessor
from app.services.dashboard_extraction_service import DashboardExtractionService
from app.services.batch_extraction_service import BatchExtractionService
from app.services.gemini_with_timeout import GeminiWithTimeout

router = APIRouter()
logger = structlog.get_logger()

# Instanciar serviços
file_validator = FileValidator()
file_manager = FileManager()
document_processor = DocumentProcessor()

# Thread pool para processamento em background
executor = ThreadPoolExecutor(max_workers=2)

def _process_document_background(document_id: str, database_url: str):
    """
    Função para processar documento em thread separada.
    Cria engine SQLite com timeout e WAL mode para evitar locks.
    Também extrai dados estruturados para o Dashboard LOA/LDO.
    """
    from sqlalchemy.orm import sessionmaker
    import asyncio
    
    thread_name = threading.current_thread().name
    logger.info(
        "Background processing started in thread",
        document_id=document_id,
        thread=thread_name
    )
    
    # Criar engine com timeout e WAL mode para SQLite
    engine = create_engine(
        database_url,
        connect_args={
            'timeout': 30,  # 30 segundos de timeout
            'check_same_thread': False
        },
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    # Ativar WAL mode para permitir leituras concorrentes
    if 'sqlite' in database_url:
        from sqlalchemy import text as sql_text
        try:
            with engine.connect() as conn:
                conn.execute(sql_text('PRAGMA journal_mode=WAL'))
                conn.commit()
                logger.info("WAL mode enabled for thread", thread=thread_name)
        except Exception as e:
            logger.warning("Failed to enable WAL mode", error=str(e))
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Processar documento de forma síncrona nesta thread
        success = asyncio.run(document_processor.process_document(document_id, db))
        
        if success:
            logger.info(
                "Background processing completed",
                document_id=document_id,
                thread=thread_name
            )
            
            # ==============================================
            # EXTRAÇÃO AUTOMÁTICA PARA DASHBOARD LOA/LDO
            # ==============================================
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                
                # Verificar se é LOA ou LDO
                if document and document.type in ["LOA", "LDO"]:
                    logger.info(
                        "Starting dashboard extraction with batch processing",
                        document_id=document_id,
                        doc_type=document.type,
                        batch_size=20,
                        model="gemini-2.5-pro"
                    )
                    
                    # USAR BATCH EXTRACTION COM GEMINI PRO PARA TODOS OS DOCUMENTOS
                    # Gemini Pro é mais capaz para extrair tabelas complexas (como regionalização)
                    # Isso garante:
                    # - Extração precisa de tabelas multi-coluna
                    # - Processamento robusto de dados estruturados complexos
                    # - Melhor compreensão de layout e formatação
                    
                    batch_service = BatchExtractionService(pages_per_batch=20)
                    
                    # Configurar Gemini 2.5 Pro com timeout de 10 minutos
                    batch_service.model = GeminiWithTimeout(
                        api_key=settings.GEMINI_API_KEY,
                        model_name='gemini-2.5-pro',
                        timeout=600  # 10 minutos por batch (Pro é mais lento mas mais preciso)
                    )
                    
                    # Processar baseado no tipo
                    if document.type == "LDO":
                        # LDO usa método específico mas também em batches
                        exercicio = batch_service.extract_ldo_from_pdf_in_batches(
                            pdf_path=document.file_path,
                            db=db,
                            municipality_id=str(document.municipality_id),
                            document_id=document.id
                        )
                    else:  # LOA
                        # LOA usa método padrão em batches
                        exercicio = batch_service.extract_from_pdf_in_batches(
                            pdf_path=document.file_path,
                            db=db,
                            municipality_id=str(document.municipality_id),
                            document_id=document.id
                        )
                    
                    logger.info(
                        "Dashboard extraction completed",
                        document_id=document_id,
                        exercicio_ano=exercicio.ano,
                        orcamento_total=str(exercicio.orcamento_total)
                    )
                    
            except Exception as e:
                # Log error but don't fail the main process
                logger.error(
                    "Dashboard extraction failed (non-fatal)",
                    document_id=document_id,
                    error=str(e)
                )
        else:
            logger.error(
                "Background processing failed",
                document_id=document_id,
                thread=thread_name
            )
            
    except Exception as e:
        logger.error(
            "Background processing error",
            document_id=document_id,
            thread=thread_name,
            error=str(e)
        )
    finally:
        db.close()
        engine.dispose()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de Documento",
    description="Faz upload de um documento (LOA ou LDO) para processamento",
    responses={
        201: {"description": "Documento enviado com sucesso"},
        400: {"model": ErrorResponse, "description": "Arquivo inválido"},
        413: {"model": ErrorResponse, "description": "Arquivo muito grande"},
        422: {"model": ErrorResponse, "description": "Dados inválidos"}
    }
)
async def upload_document(
    file: UploadFile = File(..., description="Arquivo PDF do documento"),
    municipality_id: str = Form(..., description="ID do município"),
    doc_type: str = Form(..., description="Tipo do documento: 'LOA' ou 'LDO'"),
    db: Session = Depends(get_db)
):
    """
    Faz upload de um documento (LOA ou LDO).
    
    O arquivo será:
    1. Validado (formato PDF, tamanho)
    2. Salvo no volume Docker
    3. Registrado no banco de dados
    4. Enviado para processamento assíncrono (Fase 2)
    
    **Parâmetros:**
    - **file**: Arquivo PDF (máx 50MB)
    - **municipality_id**: ID do município (obter via /api/municipalities)
    - **doc_type**: Tipo do documento ('LOA' ou 'LDO')
    
    **Retorna:**
    - document_id: ID do documento criado
    - status: 'pending' (aguardando processamento)
    - estimated_processing_time_minutes: Tempo estimado
    """
    logger.info(
        "Upload request received",
        filename=file.filename,
        municipality_id=municipality_id,
        doc_type=doc_type
    )
    
    # 1. Validar tipo de documento
    file_validator.validate_document_type(doc_type)
    doc_type = doc_type.upper()
    
    # 2. Verificar se município existe
    municipality = db.query(Municipality).filter(
        Municipality.id == municipality_id
    ).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município com ID '{municipality_id}' não encontrado"
        )
    
    # 3. Validar arquivo PDF
    await file_validator.validate_pdf(file)
    
    # 4. Verificar se já existe documento deste tipo
    existing_doc = db.query(Document).filter(
        Document.municipality_id == municipality_id,
        Document.type == doc_type
    ).order_by(Document.version.desc()).first()
    
    # Determinar versão
    version = 1 if not existing_doc else existing_doc.version + 1
    
    if existing_doc and existing_doc.status in ["pending", "processing"]:
        # Já existe upload em andamento
        logger.warning(
            "Document upload already in progress",
            municipality_id=municipality_id,
            doc_type=doc_type,
            existing_status=existing_doc.status
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um documento {doc_type} em processamento. "
                   f"Aguarde a conclusão ou cancele o processamento anterior."
        )
    
    # 5. Salvar arquivo no disco
    try:
        file_path, file_size = await file_manager.save_upload(
            file=file,
            municipality_id=municipality_id,
            doc_type=doc_type
        )
    except Exception as e:
        logger.error("Failed to save file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar arquivo: {str(e)}"
        )
    
    # 6. Criar registro no banco de dados
    document = Document(
        municipality_id=municipality_id,
        type=doc_type,
        filename=file.filename,
        file_path=file_path,
        file_size_bytes=file_size,
        upload_date=datetime.utcnow(),
        status="pending",
        version=version
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    logger.info(
        "Document uploaded successfully",
        document_id=document.id,
        municipality_id=municipality_id,
        doc_type=doc_type,
        version=version,
        file_size_mb=file_size / (1024 * 1024)
    )
    
    # 7. Estimar tempo de processamento
    estimated_time = file_manager.estimate_processing_time(file_size)
    
    # TODO Fase 3: Enviar para fila de processamento (Celery) para produção
    # Por enquanto, processar será manual via POST /api/documents/{id}/process
    # process_document.delay(document.id)
    
    return UploadResponse(
        document_id=document.id,
        filename=file.filename,
        file_size_bytes=file_size,
        status="pending",
        message=f"Documento {doc_type} enviado com sucesso e será processado em breve",
        estimated_processing_time_minutes=estimated_time
    )


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Status do Documento",
    description="Obtém o status de processamento de um documento",
    responses={
        200: {"description": "Status obtido com sucesso"},
        404: {"model": ErrorResponse, "description": "Documento não encontrado"}
    }
)
async def get_document_status(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna o status de processamento de um documento.
    
    **Status possíveis:**
    - `pending`: Aguardando processamento
    - `processing`: Sendo processado
    - `completed`: Processamento concluído
    - `failed`: Erro no processamento
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID '{document_id}' não encontrado"
        )
    
    return DocumentStatusResponse(**document.to_dict())


@router.get(
    "/",
    response_model=List[DocumentStatusResponse],
    summary="Listar Documentos",
    description="Lista todos os documentos cadastrados no sistema"
)
async def list_documents(
    municipality_id: str = None,
    doc_type: str = None,
    status_filter: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista documentos com filtros opcionais.
    
    **Filtros:**
    - **municipality_id**: Filtrar por município
    - **doc_type**: Filtrar por tipo ('LOA' ou 'LDO')
    - **status_filter**: Filtrar por status ('pending', 'processing', 'completed', 'failed')
    """
    query = db.query(Document)
    
    if municipality_id:
        query = query.filter(Document.municipality_id == municipality_id)
    
    if doc_type:
        query = query.filter(Document.type == doc_type.upper())
    
    if status_filter:
        query = query.filter(Document.status == status_filter)
    
    documents = query.order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()
    
    return [DocumentStatusResponse(**doc.to_dict()) for doc in documents]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar Documento",
    description="Remove documento e arquivo associado",
    responses={
        204: {"description": "Documento deletado com sucesso"},
        404: {"model": ErrorResponse, "description": "Documento não encontrado"}
    }
)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove documento do sistema.
    
    ⚠️ **ATENÇÃO:**
    - Remove registro do banco de dados
    - Remove arquivo do disco
    - Remove embeddings do ChromaDB (quando implementado)
    - Esta ação não pode ser desfeita!
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID '{document_id}' não encontrado"
        )
    
    logger.warning("Deleting document", document_id=document_id)
    
    # Deletar arquivo do disco
    file_manager.delete_file(document.file_path)
    
    # TODO: Deletar embeddings do ChromaDB na Fase 2
    # if document.chromadb_collection_id:
    #     vector_db.delete_collection(document.chromadb_collection_id)
    
    # Deletar registro do banco
    db.delete(document)
    db.commit()
    
    logger.info("Document deleted successfully", document_id=document_id)
    
    return None


@router.post(
    "/{document_id}/reprocess",
    response_model=DocumentStatusResponse,
    summary="Reprocessar Documento",
    description="Inicia reprocessamento de um documento que falhou",
    responses={
        200: {"description": "Reprocessamento iniciado"},
        404: {"model": ErrorResponse, "description": "Documento não encontrado"},
        409: {"model": ErrorResponse, "description": "Documento já está sendo processado"}
    }
)
async def reprocess_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Reprocessa um documento que falhou ou precisa ser atualizado.
    
    Útil quando:
    - Processamento falhou
    - Algoritmo de processamento foi melhorado
    - Deseja regenerar embeddings
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID '{document_id}' não encontrado"
        )
    
    if document.status in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Documento já está em processamento (status: {document.status})"
        )
    
    # Resetar status para reprocessar
    document.status = "pending"
    document.error_message = None
    document.processed_date = None
    document.total_chunks = 0
    
    db.commit()
    db.refresh(document)
    
    logger.info("Document queued for reprocessing", document_id=document_id)
    
    # TODO: Enviar para fila de processamento (Celery) na Fase 3
    # process_document.delay(document.id)
    
    return DocumentStatusResponse(**document.to_dict())


@router.post(
    "/{document_id}/process",
    response_model=DocumentStatusResponse,
    summary="Processar Documento",
    description="Inicia processamento de um documento (extração, chunking, embeddings)",
    responses={
        200: {"description": "Processamento iniciado"},
        404: {"model": ErrorResponse, "description": "Documento não encontrado"},
        409: {"model": ErrorResponse, "description": "Documento já está sendo processado"}
    }
)
async def process_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Processa um documento pendente em background:
    1. Extrai texto do PDF
    2. Cria chunks inteligentes
    3. Gera embeddings com Gemini
    4. Armazena no ChromaDB
    
    ⚠️ **ATENÇÃO:** Este processo roda em background e pode levar alguns minutos.
    Use o endpoint GET /documents/{id} para verificar o status.
    
    **Status após processamento:**
    - `processing`: Processamento em andamento
    - `completed`: Documento pronto para uso no chat
    - `failed`: Erro no processamento (ver error_message)
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID '{document_id}' não encontrado"
        )
    
    if document.status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Documento já está sendo processado"
        )
    
    if document.status == "completed":
        # Já está processado, retornar info
        logger.info("Document already processed", document_id=document_id)
        return DocumentStatusResponse(**document.to_dict())
    
    # Marcar como processando ANTES de iniciar
    document.status = "processing"
    db.commit()
    db.refresh(document)
    
    logger.info("Document queued for thread pool processing", document_id=document_id)
    
    # Submeter processamento para thread pool
    # Isso roda em uma thread completamente separada, não bloqueando o FastAPI
    executor.submit(
        _process_document_background,
        document_id,
        settings.DATABASE_URL
    )
    
    # Retornar imediatamente com status "processing"
    return DocumentStatusResponse(**document.to_dict())


@router.get(
    "/{document_id}/progress",
    response_model=Dict,
    summary="Obter Progresso em Tempo Real",
    description="Lê os logs para extrair o progresso atual do processamento"
)
async def get_document_progress(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtém o progresso de processamento em tempo real através dos logs.
    
    Não depende do banco de dados, lê diretamente os logs do container.
    
    Returns:
        {
            "document_id": str,
            "status": str,
            "current_batch": int,
            "total_batches": int,
            "percentage": float
        }
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento com ID '{document_id}' não encontrado"
        )
    
    # Se não está processando, retornar info do banco
    if document.status != "processing":
        return {
            "document_id": document_id,
            "status": document.status,
            "current_batch": document.processed_batches or 0,
            "total_batches": document.total_batches or 0,
            "percentage": 100.0 if document.status == "completed" else 0.0
        }
    
    # Se está processando, criar arquivo temporário de progresso
    progress_file = f"/tmp/processing_{document_id}.txt"
    
    try:
        import os
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                content = f.read().strip()
                if content:
                    # Formato: "batch_atual"
                    current_batch = int(content)
                    total_batches = 170
                    percentage = round((current_batch / total_batches) * 100, 2)
                    
                    return {
                        "document_id": document_id,
                        "status": "processing",
                        "current_batch": current_batch,
                        "total_batches": total_batches,
                        "percentage": percentage
                    }
    except Exception as e:
        logger.warning(
            "Failed to read progress file",
            document_id=document_id,
            error=str(e)
        )
    
    # Fallback: retornar info básica
    return {
        "document_id": document_id,
        "status": "processing",
        "current_batch": 0,
        "total_batches": 170,
        "percentage": 0.0
    }


@router.get(
    "/{document_id}/stats",
    summary="Estatísticas do Processamento",
    description="Obtém estatísticas detalhadas do processamento de um documento"
)
async def get_document_stats(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna estatísticas detalhadas do processamento:
    - Total de chunks criados
    - Informações do ChromaDB
    - Tempo de processamento
    - Status atual
    """
    stats = document_processor.get_processing_stats(document_id, db)
    
    if "error" in stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=stats["error"]
        )
    
    return stats

