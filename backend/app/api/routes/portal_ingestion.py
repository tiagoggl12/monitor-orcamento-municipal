"""
Rotas da API para Ingestão de Packages do Portal
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import structlog
from concurrent.futures import ThreadPoolExecutor

from app.api.dependencies import get_db
from app.services.portal_ingestion_service import PortalIngestionService

logger = structlog.get_logger(__name__)

# Executor para processar jobs em background
executor = ThreadPoolExecutor(max_workers=2)

router = APIRouter(prefix="/portal/ingest", tags=["portal-ingestion"])


# Schemas
class StartIngestionRequest(BaseModel):
    """Request para iniciar ingestão"""
    packages: List[str]
    municipality_id: str


class IngestionJobResponse(BaseModel):
    """Response de job de ingestão"""
    job_id: str
    status: str
    message: str


class CollectionResponse(BaseModel):
    """Response de collections"""
    collections: List[str]
    total: int


# NÃO instanciar globalmente - criar com db session


def _process_job_in_background(job_id: str):
    """
    Função wrapper para processar job em thread separada.
    Esta função roda em ThreadPoolExecutor para não bloquear o event loop.
    """
    import asyncio
    from app.core.database import SessionLocal
    
    logger.info(f"[BACKGROUND] Starting processing for job {job_id}")
    
    # Criar nova sessão para a thread
    db = SessionLocal()
    
    # Criar serviço com db (FASE 1)
    ingestion_service = PortalIngestionService(db=db)
    
    # Criar novo event loop para esta thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Processar o job
        logger.info(f"[BACKGROUND] Calling process_job for {job_id}")
        result = loop.run_until_complete(
            ingestion_service.process_job(job_id, db)
        )
        
        logger.info(f"[BACKGROUND] Job {job_id} completed successfully", result=result)
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Job {job_id} failed with error: {str(e)}")
        import traceback
        logger.error(f"[BACKGROUND] Traceback: {traceback.format_exc()}")
    finally:
        logger.info(f"[BACKGROUND] Closing resources for job {job_id}")
        try:
            db.close()
        except:
            pass
        try:
            loop.close()
        except:
            pass


@router.post("/start", response_model=IngestionJobResponse)
async def start_ingestion(
    request: StartIngestionRequest,
    db: Session = Depends(get_db)
):
    """
    Inicia um job de ingestão de packages
    
    Args:
        request: Lista de packages e município
        db: Sessão do banco
        
    Returns:
        ID do job criado
    """
    try:
        # Criar serviço com db (FASE 1)
        ingestion_service = PortalIngestionService(db=db)
        
        # Criar job no banco
        job_id = await ingestion_service.start_ingestion(
            package_names=request.packages,
            municipality_id=request.municipality_id,
            db=db
        )
        
        # Garantir que o job está persistido no banco
        db.flush()
        db.commit()
        
        # Pequeno delay para garantir que o job está disponível
        import time
        time.sleep(0.1)
        
        # Verificar se job foi criado
        from app.models.portal_ingestion_job import PortalIngestionJob
        job_check = db.query(PortalIngestionJob).filter(
            PortalIngestionJob.id == job_id
        ).first()
        
        if not job_check:
            raise HTTPException(status_code=500, detail="Job was not created in database")
        
        logger.info(
            "Ingestion job created and verified",
            job_id=job_id,
            packages=len(request.packages)
        )
        
        # Processar em thread separada (não bloqueia o FastAPI)
        executor.submit(_process_job_in_background, job_id)
        
        return IngestionJobResponse(
            job_id=job_id,
            status="pending",
            message=f"Job criado com sucesso. Processando {len(request.packages)} packages em background."
        )
        
    except Exception as e:
        logger.error(f"Error starting ingestion", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtém o status de um job de ingestão
    
    Args:
        job_id: ID do job
        db: Sessão do banco
        
    Returns:
        Status do job
    """
    try:
        logger.debug(f"Getting status for job_id: {job_id}")
        
        status = ingestion_service.get_job_status(job_id, db)
        
        if not status:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        logger.debug(f"Job status: {status.get('status')}")
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{job_id}")
async def get_job_progress(job_id: str):
    """
    Obtém o progresso em tempo real de um job (lendo do arquivo de log)
    
    Args:
        job_id: ID do job
        
    Returns:
        Progresso atual do processamento
    """
    try:
        import os
        
        progress_file = f"/tmp/ingest_progress_{job_id}.txt"
        
        if not os.path.exists(progress_file):
            return {
                "current_package_index": 0,
                "total_packages": 0,
                "message": "Aguardando início do processamento...",
                "percentage": 0,
                "documents_inserted": 0
            }
        
        try:
            with open(progress_file, 'r') as f:
                content = f.read().strip()
            
            if not content:
                return {
                    "current_package_index": 0,
                    "total_packages": 0,
                    "message": "Processamento iniciando...",
                    "percentage": 0,
                    "documents_inserted": 0
                }
            
            # Parse com suporte a dois formatos:
            # Formato 1 (packages): "current/total|message|documents_inserted"
            # Formato 2 (batches): "current_batch|total_batches|message|percentage|documents_inserted"
            parts = content.split('|')
            
            if len(parts) >= 5:
                # Formato novo com batches
                current_batch = int(parts[0])
                total_batches = int(parts[1])
                message = parts[2] if len(parts) > 2 else "Processando..."
                percentage = int(parts[3]) if len(parts) > 3 else 0
                documents_inserted = int(parts[4]) if len(parts) > 4 else 0
                
                return {
                    "current_batch": current_batch,
                    "total_batches": total_batches,
                    "message": message,
                    "percentage": percentage,
                    "documents_inserted": documents_inserted
                }
            else:
                # Formato antigo com packages
                progress_parts = parts[0].split('/')
                
                current = int(progress_parts[0])
                total = int(progress_parts[1])
                message = parts[1] if len(parts) > 1 else "Processando..."
                documents_inserted = int(parts[2]) if len(parts) > 2 else 0
                
                percentage = int((current / total * 100)) if total > 0 else 0
                
                return {
                    "current_package_index": current,
                    "total_packages": total,
                    "message": message,
                    "percentage": percentage,
                    "documents_inserted": documents_inserted
                }
            
        except Exception as e:
            logger.error(f"Error parsing progress file", job_id=job_id, error=str(e))
            return {
                "current_package_index": 0,
                "total_packages": 0,
                "message": "Erro ao ler progresso",
                "percentage": 0,
                "documents_inserted": 0
            }
        
    except Exception as e:
        logger.error(f"Error getting job progress", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections", response_model=CollectionResponse)
async def list_collections():
    """
    Lista todas as collections do Portal no ChromaDB
    
    Returns:
        Lista de collections
    """
    try:
        collections = ingestion_service.list_collections()
        
        return CollectionResponse(
            collections=collections,
            total=len(collections)
        )
        
    except Exception as e:
        logger.error(f"Error listing collections", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processed-packages")
async def list_processed_packages(
    municipality_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Lista packages que já foram processados com informações detalhadas
    
    Args:
        municipality_id: Filtrar por município (opcional)
        
    Returns:
        Dicionário com package_name -> informações de processamento
    """
    try:
        from app.models.portal_ingestion_job import PortalIngestionJob
        import json
        
        query = db.query(PortalIngestionJob).filter(
            PortalIngestionJob.status == "completed"
        )
        
        if municipality_id:
            query = query.filter(PortalIngestionJob.municipality_id == municipality_id)
        
        jobs = query.order_by(PortalIngestionJob.completed_at.desc()).all()
        
        # Mapear packages processados
        processed = {}
        
        for job in jobs:
            try:
                packages_list = json.loads(job.packages)
                
                for package_name in packages_list:
                    # Guardar apenas o mais recente de cada package
                    if package_name not in processed:
                        processed[package_name] = {
                            "package_name": package_name,
                            "last_processed": job.completed_at.isoformat() if job.completed_at else None,
                            "job_id": job.id,
                            "total_documents": job.total_documents,
                            "status": "completed"
                        }
            except:
                continue
        
        return {
            "processed_packages": processed,
            "total": len(processed)
        }
        
    except Exception as e:
        logger.error(f"Error listing processed packages", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collection/{collection_name}")
async def delete_collection(collection_name: str):
    """
    Deleta uma collection do ChromaDB
    
    Args:
        collection_name: Nome da collection
        
    Returns:
        Resultado da operação
    """
    try:
        success = ingestion_service.delete_collection(collection_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete collection")
        
        return {
            "message": f"Collection {collection_name} deleted successfully",
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting collection",
            collection=collection_name,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def list_jobs(
    municipality_id: str = None,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Lista todos os jobs de ingestão com filtros
    
    Args:
        municipality_id: Filtrar por município (opcional)
        status: Filtrar por status (opcional)
        limit: Limite de resultados (padrão: 50)
        db: Sessão do banco
        
    Returns:
        Lista de jobs com informações detalhadas
    """
    try:
        from app.models.portal_ingestion_job import PortalIngestionJob
        import json
        
        query = db.query(PortalIngestionJob)
        
        if municipality_id:
            query = query.filter(PortalIngestionJob.municipality_id == municipality_id)
        
        if status:
            query = query.filter(PortalIngestionJob.status == status)
        
        jobs = query.order_by(PortalIngestionJob.created_at.desc()).limit(limit).all()
        
        # Enriquecer com informações dos packages
        jobs_data = []
        for job in jobs:
            job_dict = job.to_dict()
            
            # Parse packages JSON
            try:
                packages_list = json.loads(job.packages)
                job_dict['packages_list'] = packages_list
            except:
                job_dict['packages_list'] = []
            
            jobs_data.append(job_dict)
        
        return {
            "jobs": jobs_data,
            "total": len(jobs_data)
        }
        
    except Exception as e:
        logger.error(f"Error listing jobs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-job")
async def get_active_job(
    municipality_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Retorna o job ativo (processing ou pending) mais recente
    
    Args:
        municipality_id: Filtrar por município (opcional)
        db: Sessão do banco
        
    Returns:
        Job ativo ou None
    """
    try:
        from app.models.portal_ingestion_job import PortalIngestionJob
        
        query = db.query(PortalIngestionJob).filter(
            PortalIngestionJob.status.in_(["processing", "pending"])
        )
        
        if municipality_id:
            query = query.filter(PortalIngestionJob.municipality_id == municipality_id)
        
        job = query.order_by(PortalIngestionJob.created_at.desc()).first()
        
        if not job:
            return {"active_job": None}
        
        return {
            "active_job": job.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error getting active job", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-job/{job_id}")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancela um job em processamento (útil para jobs travados)
    
    Args:
        job_id: ID do job
        db: Sessão do banco
        
    Returns:
        Resultado da operação
    """
    try:
        from app.models.portal_ingestion_job import PortalIngestionJob
        from datetime import datetime
        
        job = db.query(PortalIngestionJob).filter(
            PortalIngestionJob.id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        if job.status in ["completed", "failed", "cancelled"]:
            return {
                "message": f"Job already in terminal state: {job.status}",
                "job_id": job_id
            }
        
        # Marcar como cancelado
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        job.error_message = "Cancelled by user or system restart"
        
        db.commit()
        
        # Tentar limpar arquivo de progresso
        try:
            import os
            progress_file = f"/tmp/ingest_progress_{job_id}.txt"
            if os.path.exists(progress_file):
                os.remove(progress_file)
        except:
            pass
        
        logger.info(f"Job cancelled", job_id=job_id)
        
        return {
            "message": "Job cancelled successfully",
            "job_id": job_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

