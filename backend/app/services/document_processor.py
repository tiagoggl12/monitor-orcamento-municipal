"""
Document Processor - Orquestra o processamento completo de documentos
"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict
import structlog

from app.models import Document, Municipality
from app.services.pdf_parser import PDFParser
from app.services.text_chunker import TextChunker
from app.services.embedding_service import EmbeddingService
from app.services.vector_db import VectorDBService

logger = structlog.get_logger()


class DocumentProcessor:
    """
    Orquestra o processamento completo de um documento:
    1. Extração de texto do PDF
    2. Chunking inteligente
    3. Geração de embeddings
    4. Armazenamento no ChromaDB
    """
    
    def __init__(self):
        self.logger = logger
        self.pdf_parser = PDFParser()
        self.text_chunker = TextChunker()
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDBService()
    
    async def process_document(
        self,
        document_id: str,
        db: Session
    ) -> bool:
        """
        Processa um documento completo
        
        Args:
            document_id: ID do documento
            db: Sessão do banco de dados
            
        Returns:
            True se processado com sucesso
        """
        self.logger.info("Starting document processing", document_id=document_id)
        
        # 1. Buscar documento no banco e extrair dados necessários
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            self.logger.error("Document not found", document_id=document_id)
            return False
        
        # 2. Buscar município para metadados
        municipality = db.query(Municipality).filter(
            Municipality.id == document.municipality_id
        ).first()
        
        if not municipality:
            self.logger.error("Municipality not found", municipality_id=document.municipality_id)
            return False
        
        # Salvar dados necessários em variáveis locais
        file_path = document.file_path
        doc_type = document.type
        doc_filename = document.filename
        municipality_name = municipality.name
        municipality_state = municipality.state
        municipality_year = municipality.year
        
        # FECHAR conexão para não segurar lock durante processamento
        db.close()
        
        self.logger.info(
            "Database connection closed, starting heavy processing",
            document_id=document_id
        )
        
        try:
            # 3. Extrair texto do PDF (SEM conexão ao banco)
            self.logger.info("Extracting text from PDF", document_id=document_id)
            extraction_result = self.pdf_parser.extract_text(file_path)
            
            if not extraction_result.get("text"):
                raise Exception("No text extracted from PDF")
            
            text = extraction_result["text"]
            
            # 4. Criar chunks
            self.logger.info("Creating text chunks", document_id=document_id)
            
            document_metadata = {
                "document_id": document_id,
                "document_type": doc_type,
                "municipality": municipality_name,
                "state": municipality_state,
                "year": municipality_year,
                "filename": doc_filename
            }
            
            chunks = self.text_chunker.chunk_text(
                text=text,
                document_type=doc_type,
                metadata=document_metadata
            )
            
            if not chunks:
                raise Exception("No chunks created from text")
            
            # Adicionar contexto aos chunks
            chunks = self.text_chunker.add_context_to_chunks(
                chunks=chunks,
                document_metadata=document_metadata
            )
            
            # 5. Gerar embeddings
            self.logger.info(
                "Generating embeddings",
                document_id=document_id,
                chunk_count=len(chunks)
            )
            
            # Calcular total de batches (apenas para logs)
            total_batches = (len(chunks) + 9) // 10  # 10 chunks por batch
            
            self.logger.info(
                "Starting embeddings generation",
                document_id=document_id,
                total_chunks=len(chunks),
                total_batches=total_batches
            )
            
            # Gerar embeddings - progresso salvo em arquivo
            chunks_with_embeddings = self.embedding_service.embed_chunks(
                chunks,
                document_id=document_id
            )
            
            if not chunks_with_embeddings:
                raise Exception("Failed to generate embeddings")
            
            # 6. Criar collection no ChromaDB
            collection_name = f"doc_{document_id}"
            
            self.logger.info(
                "Creating ChromaDB collection",
                document_id=document_id,
                collection_name=collection_name
            )
            
            self.vector_db.create_collection(
                collection_name=collection_name,
                metadata={
                    "document_id": document_id,
                    "document_type": doc_type,
                    "municipality": municipality_name,
                    "state": municipality_state,
                    "year": municipality_year
                }
            )
            
            # 7. Adicionar embeddings ao ChromaDB
            self.logger.info(
                "Adding embeddings to ChromaDB",
                document_id=document_id,
                embedding_count=len(chunks_with_embeddings)
            )
            
            embeddings = [c["embedding"] for c in chunks_with_embeddings]
            texts = [c["text"] for c in chunks_with_embeddings]
            metadatas = [c["metadata"] for c in chunks_with_embeddings]
            ids = [f"{document_id}_chunk_{c['id']}" for c in chunks_with_embeddings]
            
            self.vector_db.add_embeddings(
                collection_name=collection_name,
                embeddings=embeddings,
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            # 8. Reabrir conexão e atualizar documento (APENAS NO FINAL)
            self.logger.info(
                "Reopening database connection to save results",
                document_id=document_id
            )
            
            # Buscar documento novamente com sessão fresca
            document = db.query(Document).filter(Document.id == document_id).first()
            
            if document:
                document.status = "completed"
                document.processed_date = datetime.utcnow()
                document.chromadb_collection_id = collection_name
                document.total_chunks = len(chunks_with_embeddings)
                document.total_batches = total_batches
                document.processed_batches = total_batches
                document.error_message = None
                
                # Único commit - no final do processamento
                db.commit()
            else:
                self.logger.error(
                    "Document not found when saving results",
                    document_id=document_id
                )
            
            self.logger.info(
                "Document processing completed successfully",
                document_id=document_id,
                total_chunks=len(chunks_with_embeddings),
                collection_name=collection_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Document processing failed",
                document_id=document_id,
                error=str(e),
                exc_info=True
            )
            
            # Buscar documento novamente antes de atualizar erro
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = "failed"
                    document.error_message = str(e)
                    db.commit()
            except Exception as commit_error:
                self.logger.error(
                    "Failed to update error status",
                    document_id=document_id,
                    error=str(commit_error)
                )
            
            return False
    
    def get_processing_stats(self, document_id: str, db: Session) -> Dict:
        """
        Obtém estatísticas do processamento de um documento
        
        Args:
            document_id: ID do documento
            db: Sessão do banco
            
        Returns:
            Dicionário com estatísticas
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            return {"error": "Document not found"}
        
        stats = {
            "document_id": document.id,
            "status": document.status,
            "total_chunks": document.total_chunks,
            "processed_date": document.processed_date.isoformat() if document.processed_date else None,
            "upload_date": document.upload_date.isoformat() if document.upload_date else None,
        }
        
        # Se processado, adicionar info do ChromaDB
        if document.status == "completed" and document.chromadb_collection_id:
            try:
                collection_info = self.vector_db.get_collection_info(
                    document.chromadb_collection_id
                )
                stats["chromadb_info"] = collection_info
            except Exception as e:
                stats["chromadb_error"] = str(e)
        
        return stats

