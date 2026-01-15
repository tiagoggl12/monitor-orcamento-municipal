"""
Serviço de Ingestão de Packages do Portal da Transparência
"""
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import structlog
import traceback

from app.services.portal_client import PortalTransparenciaClient, get_portal_client
from app.services.resource_parser import ResourceParser
from app.services.vector_db import VectorDBService
from app.services.embedding_service import EmbeddingService
from app.services.raw_file_service import RawFileService
from app.services.data_lineage_service import DataLineageService
from app.services.schema_discovery_service import SchemaDiscoveryService
from app.models.portal_ingestion_job import PortalIngestionJob
from app.models.raw_file import RawFile
from app.models.parsed_data import ParsedData
from app.core.config import settings
from app.schemas.metadata_schemas import MetadataExtractor, MetadataValidator

logger = structlog.get_logger(__name__)


class PortalIngestionService:
    """
    Serviço para ingerir dados do Portal da Transparência
    COM AUDITABILIDADE COMPLETA (Fase 1)
    """
    
    def __init__(self, db: Session = None):
        self.portal_client = get_portal_client()
        self.parser = ResourceParser()
        self.vector_db = VectorDBService()
        self.embedding_service = EmbeddingService()
        
        # SERVIÇOS DE AUDITABILIDADE (Fase 1)
        self.db = db
        if db:
            self.raw_file_service = RawFileService(db)
            self.lineage_service = DataLineageService(db)
            
            # SERVIÇOS DE ELASTICIDADE (Fase 2)
            self.schema_discovery_service = SchemaDiscoveryService(db)
    
    async def start_ingestion(
        self,
        package_names: List[str],
        municipality_id: str,
        db: Session
    ) -> str:
        """
        Inicia um job de ingestão de packages
        
        Args:
            package_names: Lista de nomes de packages a processar
            municipality_id: ID do município
            db: Sessão do banco de dados
            
        Returns:
            ID do job criado
        """
        # Criar job
        job = PortalIngestionJob(
            municipality_id=municipality_id,
            packages=json.dumps(package_names),
            status="pending",
            total_packages=len(package_names)
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            "Ingestion job created",
            job_id=job.id,
            packages=len(package_names)
        )
        
        return job.id
    
    async def process_job(self, job_id: str, db: Session) -> Dict[str, Any]:
        """
        Processa um job de ingestão
        
        Args:
            job_id: ID do job
            db: Sessão do banco de dados
            
        Returns:
            Resultado do processamento
        """
        # Criar arquivo de progresso
        progress_file = f"/tmp/ingest_progress_{job_id}.txt"
        
        try:
            with open(progress_file, 'w') as f:
                f.write("0/0|Iniciando processamento...|0")
            logger.info(f"Progress file created: {progress_file}")
        except Exception as e:
            logger.error(f"Failed to create progress file: {e}")
        
        # Buscar job
        job = db.query(PortalIngestionJob).filter(
            PortalIngestionJob.id == job_id
        ).first()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Atualizar status
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db.commit()
        
        try:
            # Parse da lista de packages
            package_names = json.loads(job.packages)
            
            results = {
                "job_id": job_id,
                "total_packages": len(package_names),
                "processed": 0,
                "failed": 0,
                "details": []
            }
            
            # Processar cada package
            for idx, package_name in enumerate(package_names, 1):
                try:
                    # Atualizar job no banco
                    job.current_package = package_name
                    db.commit()
                    db.flush()  # Forçar flush
                    
                    # Escrever progresso em arquivo
                    try:
                        with open(progress_file, 'w') as f:
                            f.write(f"{idx}/{len(package_names)}|Processando: {package_name}|{job.total_documents}")
                        logger.debug(f"Progress file updated: {idx}/{len(package_names)}")
                    except Exception as e:
                        logger.error(f"Failed to update progress file: {e}")
                    
                    logger.info(f"Processing package {idx}/{len(package_names)}: {package_name}")
                    
                    result = await self.process_package(
                        package_name=package_name,
                        municipality_id=job.municipality_id,
                        job_id=job_id,
                        progress_file=progress_file
                    )
                    
                    job.processed_packages += 1
                    job.total_resources += result.get("resources_processed", 0)
                    job.processed_resources += result.get("resources_processed", 0)
                    job.total_documents += result.get("documents_inserted", 0)
                    
                    results["processed"] += 1
                    results["details"].append(result)
                    
                    db.commit()
                    db.flush()
                    
                    # Atualizar progresso após completar
                    docs_inserted = result.get('documents_inserted', 0)
                    try:
                        with open(progress_file, 'w') as f:
                            f.write(f"{idx}/{len(package_names)}|Completado: {package_name}|{job.total_documents}")
                        logger.info(f"Package completed: {package_name} ({docs_inserted} docs)")
                    except Exception as e:
                        logger.error(f"Failed to update progress file after completion: {e}")
                    
                    logger.info(
                        f"Package processed successfully",
                        package=package_name,
                        documents=result.get("documents_inserted", 0)
                    )
                    
                except Exception as e:
                    job.failed_packages += 1
                    results["failed"] += 1
                    
                    error_result = {
                        "package": package_name,
                        "status": "failed",
                        "error": str(e)
                    }
                    results["details"].append(error_result)
                    
                    logger.error(
                        f"Error processing package",
                        package=package_name,
                        error=str(e)
                    )
                    
                    db.commit()
            
            # Finalizar job
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.current_package = None
            db.commit()
            db.flush()
            db.refresh(job)  # Forçar refresh do objeto
            
            # Limpar arquivo de progresso
            try:
                import os
                if os.path.exists(progress_file):
                    os.remove(progress_file)
                    logger.info(f"Progress file deleted: {progress_file}")
            except Exception as e:
                logger.error(f"Failed to delete progress file: {e}")
            
            logger.info(
                "Ingestion job completed",
                job_id=job_id,
                processed=results["processed"],
                failed=results["failed"],
                total_documents=job.total_documents
            )
            
            return results
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            
            # Limpar arquivo de progresso
            try:
                import os
                if os.path.exists(progress_file):
                    os.remove(progress_file)
            except:
                pass
            
            logger.error(
                "Ingestion job failed",
                job_id=job_id,
                error=str(e)
            )
            raise
    
    async def process_package(
        self,
        package_name: str,
        municipality_id: str,
        job_id: str = None,
        progress_file: str = None
    ) -> Dict[str, Any]:
        """
        Processa um package individual
        
        Args:
            package_name: Nome do package
            municipality_id: ID do município
            job_id: ID do job (para progresso)
            progress_file: Arquivo de progresso
            
        Returns:
            Resultado do processamento
        """
        # 1. Buscar metadados do package
        package_data = await self.portal_client.show_package(package_name)
        
        result = {
            "package": package_name,
            "status": "processing",
            "resources_total": len(package_data.get("resources", [])),
            "resources_processed": 0,
            "resources_failed": 0,
            "documents_inserted": 0,
            "resource_details": []
        }
        
        # 2. Processar cada resource
        for resource in package_data.get("resources", []):
            resource_format = resource.get("format", "").upper()
            
            # Processar apenas TXT e CSV
            if resource_format not in ["TXT", "CSV"]:
                logger.debug(
                    f"Skipping resource (unsupported format)",
                    resource=resource.get("name"),
                    format=resource_format
                )
                continue
            
            try:
                resource_result = await self.process_resource(
                    resource=resource,
                    package_name=package_name,
                    municipality_id=municipality_id,
                    job_id=job_id,
                    progress_file=progress_file
                )
                
                result["resources_processed"] += 1
                result["documents_inserted"] += resource_result.get("documents", 0)
                result["resource_details"].append(resource_result)
                
            except Exception as e:
                result["resources_failed"] += 1
                result["resource_details"].append({
                    "resource_name": resource.get("name"),
                    "status": "failed",
                    "error": str(e)
                })
                
                logger.error(
                    f"Error processing resource",
                    resource=resource.get("name"),
                    error=str(e)
                )
        
        result["status"] = "completed"
        return result
    
    async def process_resource(
        self,
        resource: Dict[str, Any],
        package_name: str,
        municipality_id: str,
        job_id: str = None,
        progress_file: str = None
    ) -> Dict[str, Any]:
        """
        Processa um resource individual
        COM AUDITABILIDADE COMPLETA (Fase 1)
        
        Fluxo:
        1. Download → armazenar RAW FILE (source of truth)
        2. Parse → criar PARSED DATA para cada linha
        3. Embedding → armazenar no ChromaDB
        4. Lineage → registrar todas as transformações
        
        Args:
            resource: Dados do resource
            package_name: Nome do package
            municipality_id: ID do município
            job_id: ID do job (para progresso)
            progress_file: Arquivo de progresso
            
        Returns:
            Resultado do processamento
        """
        resource_name = resource.get("name", "unnamed")
        resource_url = resource.get("url")
        resource_format = resource.get("format", "").upper()
        resource_id = resource.get("id", "unknown")
        
        logger.info(
            f"Processing resource (Fase 1)",
            resource=resource_name,
            format=resource_format
        )
        
        raw_file = None
        lineage_download = None
        lineage_parse = None
        
        try:
            # ============================================================
            # FASE 1.1: DOWNLOAD + ARMAZENAR RAW FILE (SOURCE OF TRUTH)
            # ============================================================
            logger.info(f"📥 Downloading resource: {resource_name}")
            content = await self.download_resource(resource_url)
            content_bytes = content.encode('utf-8')
            
            # Registrar lineage do download
            if self.db and hasattr(self, 'lineage_service'):
                lineage_download = self.lineage_service.start_operation(
                    raw_file_id="pending",  # Será atualizado
                    operation="file_download",
                    operation_details={
                        "resource_url": resource_url,
                        "resource_name": resource_name,
                        "package_name": package_name
                    }
                )
            
            # Armazenar raw file (imutável, source of truth)
            if self.db and hasattr(self, 'raw_file_service'):
                logger.info(f"💾 Storing raw file: {resource_name}")
                raw_file = await self.raw_file_service.store_raw_file(
                    content=content_bytes,
                    filename=resource_name,
                    file_format=resource_format,
                    municipality_id=municipality_id,
                    source_type="portal_transparency",
                    source_identifier=f"{package_name}/{resource_id}",
                    metadata={
                        "package_name": package_name,
                        "resource_url": resource_url,
                        "resource_id": resource_id,
                        "download_date": datetime.utcnow().isoformat()
                    }  # será armazenado em extra_metadata
                )
                
                # Atualizar lineage com raw_file_id
                if lineage_download:
                    lineage_download.raw_file_id = raw_file.id
                    self.db.commit()
                    self.lineage_service.complete_operation(
                        lineage_download,
                        result={
                            "raw_file_id": raw_file.id,
                            "file_size_bytes": len(content_bytes),
                            "sha256_hash": raw_file.sha256_hash
                        }
                    )
            
            # ============================================================
            # FASE 1.2: PARSE DO CONTEÚDO
            # ============================================================
            if raw_file and hasattr(self, 'lineage_service'):
                lineage_parse = self.lineage_service.start_operation(
                    raw_file_id=raw_file.id,
                    operation=f"parse_{resource_format.lower()}",
                    operation_details={
                        "parser": f"{resource_format}_parser",
                        "resource_name": resource_name
                    }
                )
            
            if resource_format == "TXT":
                documents = self.parser.parse_txt(content, resource_name)
            elif resource_format == "CSV":
                documents = self.parser.parse_csv(content, resource_name)
            else:
                raise ValueError(f"Unsupported format: {resource_format}")
            
            if not documents:
                logger.warning(f"No documents parsed from resource: {resource_name}")
                return {
                    "resource_name": resource_name,
                    "status": "completed",
                    "documents": 0,
                    "raw_file_id": raw_file.id if raw_file else None
                }
            
            # ============================================================
            # FASE 1.3: CRIAR PARSED DATA (linha/coluna estruturada)
            # ============================================================
            parsed_data_ids = []
            
            for idx, doc in enumerate(documents):
                # Adicionar metadados base
                doc["package_name"] = package_name
                doc["municipality_id"] = municipality_id
                doc["resource_url"] = resource_url
                doc["resource_format"] = resource_format
                doc["processed_at"] = datetime.utcnow().isoformat()
                
                # Extrair metadados estruturados para CSV
                if resource_format == "CSV":
                    csv_fields = doc.get("fields", {})
                    structured_metadata = MetadataExtractor.extract_from_portal_csv(
                        row=csv_fields,
                        resource_name=resource_name
                    )
                    is_valid = MetadataValidator.validate(structured_metadata)
                    quality_score = MetadataValidator.get_quality_score(structured_metadata)
                    
                    doc["structured_metadata"] = structured_metadata
                    doc["metadata_valid"] = is_valid
                    doc["metadata_quality"] = quality_score
                
                # Criar ParsedData no PostgreSQL
                if raw_file and self.db:
                    parsed_data = ParsedData(
                        raw_file_id=raw_file.id,
                        row_number=doc.get("row_number", idx + 1),
                        data=doc.get("fields", {}),
                        data_normalized={},  # TODO: normalizar na Fase 2
                        text_content=doc.get("content", "")
                    )
                    
                    self.db.add(parsed_data)
                    self.db.flush()
                    
                    parsed_data_ids.append(parsed_data.id)
                    
                    # Adicionar parsed_data_id ao documento (para ChromaDB)
                    doc["parsed_data_id"] = parsed_data.id
            
            if raw_file and self.db:
                self.db.commit()
            
            # Completar lineage de parsing
            if lineage_parse:
                self.lineage_service.complete_operation(
                    lineage_parse,
                    result={
                        "rows_parsed": len(documents),
                        "parsed_data_ids": parsed_data_ids
                    }
                )
            
            # ============================================================
            # FASE 2: DESCOBRIR SCHEMA (Elasticidade de Nomes de Colunas)
            # ============================================================
            file_schema = None
            
            if raw_file and resource_format == "CSV" and hasattr(self, 'schema_discovery_service'):
                try:
                    logger.info(f"🔍 Discovering schema for: {resource_name}")
                    
                    file_schema = await self.schema_discovery_service.discover_schema(
                        raw_file=raw_file,
                        content=content,
                        delimiter=";"
                    )
                    
                    logger.info(
                        f"✅ Schema discovered: {file_schema.total_columns} columns, "
                        f"{file_schema.total_rows} rows"
                    )
                    
                    # Log schema para debug (formato LLM)
                    logger.debug(f"\n{file_schema.format_for_llm()}")
                    
                except Exception as e:
                    logger.error(f"⚠️ Schema discovery failed: {e}")
                    # Não falhar o processamento, apenas logar
            
            # ============================================================
            # FASE 1.4: GERAR EMBEDDINGS E ARMAZENAR NO CHROMADB
            # ============================================================
            collection_name = f"portal_{package_name}"
            
            await self.store_documents_in_chromadb(
                documents=documents,
                collection_name=collection_name,
                job_id=job_id,
                progress_file=progress_file,
                raw_file_id=raw_file.id if raw_file else None
            )
            
            logger.info(
                f"✅ Resource processed successfully",
                resource=resource_name,
                documents=len(documents),
                raw_file_id=raw_file.id if raw_file else None
            )
            
            return {
                "resource_name": resource_name,
                "status": "completed",
                "documents": len(documents),
                "raw_file_id": raw_file.id if raw_file else None,
                "parsed_data_count": len(parsed_data_ids),
                "file_schema_id": file_schema.id if file_schema else None
            }
            
        except Exception as e:
            logger.error(
                f"❌ Error processing resource",
                resource=resource_name,
                error=str(e)
            )
            
            # Registrar falha no lineage
            if lineage_download:
                self.lineage_service.fail_operation(
                    lineage_download,
                    error_message=str(e),
                    error_traceback=traceback.format_exc()
                )
            
            if lineage_parse:
                self.lineage_service.fail_operation(
                    lineage_parse,
                    error_message=str(e),
                    error_traceback=traceback.format_exc()
                )
            
            raise
    
    async def download_resource(self, url: str) -> str:
        """
        Faz download de um resource
        
        Args:
            url: URL do resource
            
        Returns:
            Conteúdo do arquivo como string
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Detectar encoding
                content = response.content.decode('utf-8', errors='ignore')
                
                return content
                
        except Exception as e:
            logger.error(f"Error downloading resource", url=url, error=str(e))
            raise
    
    async def store_documents_in_chromadb(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str,
        job_id: str = None,
        progress_file: str = None,
        raw_file_id: str = None
    ) -> None:
        """
        Armazena documentos no ChromaDB
        COM REGISTRO DE LINEAGE (Fase 1)
        
        Args:
            documents: Lista de documentos
            collection_name: Nome da collection
            job_id: ID do job (para atualizar progresso)
            progress_file: Arquivo de progresso
            raw_file_id: ID do raw file (para lineage)
        """
        lineage_embedding = None
        chromadb_ids = []
        
        try:
            # Registrar lineage de embedding
            if raw_file_id and self.db and hasattr(self, 'lineage_service'):
                lineage_embedding = self.lineage_service.start_operation(
                    raw_file_id=raw_file_id,
                    operation="generate_embedding",
                    operation_details={
                        "collection_name": collection_name,
                        "total_documents": len(documents)
                    }
                )
            
            # Batch processing (1000 docs por vez)
            batch_size = 1000
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Preparar dados para ChromaDB
                texts = []
                metadatas = []
                ids = []
                
                for idx, doc in enumerate(batch):
                    text = doc.get("content", "")
                    
                    # Metadados: priorizar structured_metadata, caso contrário usar campos base
                    if "structured_metadata" in doc and doc["structured_metadata"]:
                        # Usar metadados estruturados (indexáveis!)
                        metadata = doc["structured_metadata"].copy()
                        
                        # Adicionar metadados base que não estão nos structured
                        metadata["package_name"] = doc.get("package_name", "")
                        metadata["municipality_id"] = doc.get("municipality_id", "")
                        metadata["resource_name"] = doc.get("resource_name", "")
                        metadata["resource_url"] = doc.get("resource_url", "")
                        metadata["resource_format"] = doc.get("resource_format", "")
                        metadata["processed_at"] = doc.get("processed_at", "")
                        metadata["row_number"] = doc.get("row_number", 0)
                        metadata["metadata_quality"] = doc.get("metadata_quality", 0.0)
                        
                        # IMPORTANTE: ChromaDB requer que metadados sejam tipos simples
                        # Converter valores complexos para string
                        for key, value in metadata.items():
                            if isinstance(value, (dict, list)):
                                metadata[key] = json.dumps(value, ensure_ascii=False)
                            elif not isinstance(value, (str, int, float, bool)):
                                metadata[key] = str(value)
                    else:
                        # Fallback: metadados base (sem estruturação)
                        metadata = {}
                        for k, v in doc.items():
                            if k not in ["content", "fields", "structured_metadata"]:
                                # Converter para tipos simples
                                if isinstance(v, (dict, list)):
                                    metadata[k] = json.dumps(v, ensure_ascii=False)
                                else:
                                    metadata[k] = str(v) if v is not None else ""
                    
                    # ID único
                    doc_id = f"{collection_name}_{i + idx}"
                    
                    texts.append(text)
                    metadatas.append(metadata)
                    ids.append(doc_id)
                
                # Callback para atualizar progresso dos batches
                def update_batch_progress(current_batch: int, total_batches: int):
                    if progress_file and job_id:
                        try:
                            percentage = int((current_batch / total_batches) * 100)
                            message = f"Processando embeddings: batch {current_batch}/{total_batches}"
                            # Durante embeddings, não sabemos quantos docs foram inseridos
                            docs_inserted = 0
                            
                            with open(progress_file, 'w') as f:
                                f.write(f"{current_batch}|{total_batches}|{message}|{percentage}|{docs_inserted}")
                            
                            logger.debug(
                                f"Batch progress updated",
                                batch=current_batch,
                                total=total_batches,
                                percentage=percentage
                            )
                        except Exception as e:
                            logger.error(f"Failed to update batch progress: {e}")
                
                # Gerar embeddings (não é async) com callback de progresso
                embeddings = self.embedding_service.generate_embeddings_batch(
                    texts=texts,
                    progress_callback=update_batch_progress if progress_file else None
                )
                
                # Criar ou obter collection
                collection = self.vector_db.get_or_create_collection(collection_name)
                
                # Adicionar documentos
                collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                # Atualizar progresso APÓS inserção no ChromaDB
                if progress_file and job_id:
                    try:
                        # Total de documentos inseridos até agora
                        total_inserted = i + len(batch)
                        current_collection = self.vector_db.get_or_create_collection(collection_name)
                        actual_count = current_collection.count()
                        
                        message = f"Documentos inseridos no ChromaDB: {actual_count}"
                        
                        with open(progress_file, 'w') as f:
                            # Formato: current_batch|total_batches|message|percentage|documents_inserted
                            f.write(f"0|0|{message}|100|{actual_count}")
                        
                        logger.info(
                            f"Documents inserted in ChromaDB",
                            inserted=actual_count,
                            expected=total_inserted
                        )
                    except Exception as e:
                        logger.error(f"Failed to update final progress: {e}")
                
                logger.info(
                    f"Batch stored in ChromaDB",
                    collection=collection_name,
                    batch=f"{i}-{i + len(batch)}",
                    total=len(documents)
                )
            
            # Completar lineage de embedding
            if lineage_embedding:
                self.lineage_service.complete_operation(
                    lineage_embedding,
                    result={
                        "collection_name": collection_name,
                        "documents_inserted": len(documents),
                        "chromadb_ids": chromadb_ids[:10]  # Primeiros 10 IDs
                    },
                    embedding_model=settings.EMBEDDING_MODEL,
                    embedding_dimensions="384"
                )
            
        except Exception as e:
            logger.error(
                f"Error storing documents in ChromaDB",
                collection=collection_name,
                error=str(e)
            )
            
            # Registrar falha no lineage
            if lineage_embedding:
                self.lineage_service.fail_operation(
                    lineage_embedding,
                    error_message=str(e),
                    error_traceback=traceback.format_exc()
                )
            
            raise
    
    def get_job_status(self, job_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Obtém o status de um job
        
        Args:
            job_id: ID do job
            db: Sessão do banco de dados
            
        Returns:
            Status do job ou None se não encontrado
        """
        try:
            logger.debug(f"Querying job with id: {job_id}")
            
            job = db.query(PortalIngestionJob).filter(
                PortalIngestionJob.id == job_id
            ).first()
            
            if not job:
                logger.warning(f"Job not found in database: {job_id}")
                # Listar todos os jobs para debug
                all_jobs = db.query(PortalIngestionJob).all()
                logger.debug(f"Total jobs in database: {len(all_jobs)}")
                if all_jobs:
                    logger.debug(f"Sample job IDs: {[j.id[:8] + '...' for j in all_jobs[:3]]}")
                return None
            
            logger.debug(f"Job found: {job.id}, status: {job.status}")
            return job.to_dict()
            
        except Exception as e:
            logger.error(f"Error in get_job_status", job_id=job_id, error=str(e))
            raise
    
    def list_collections(self) -> List[str]:
        """
        Lista todas as collections do Portal no ChromaDB
        
        Returns:
            Lista de nomes de collections
        """
        try:
            all_collections = self.vector_db.list_collections()
            # all_collections já é uma lista de strings (nomes)
            portal_collections = [
                c for c in all_collections
                if c.startswith("portal_")
            ]
            return portal_collections
        except Exception as e:
            logger.error(f"Error listing collections", error=str(e))
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Deleta uma collection do ChromaDB
        
        Args:
            collection_name: Nome da collection
            
        Returns:
            True se deletada com sucesso
        """
        try:
            self.vector_db.delete_collection(collection_name)
            logger.info(f"Collection deleted", collection=collection_name)
            return True
        except Exception as e:
            logger.error(
                f"Error deleting collection",
                collection=collection_name,
                error=str(e)
            )
            return False

