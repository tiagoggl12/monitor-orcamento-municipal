"""
Embedding Service - Gera embeddings usando Google Gemini
"""

import google.generativeai as genai
from typing import List, Dict
import structlog
import time

from app.core.config import settings

logger = structlog.get_logger()


class EmbeddingService:
    """
    Serviço para gerar embeddings de texto usando Gemini
    """
    
    def __init__(self):
        self.logger = logger
        self.model_name = "models/embedding-001"
        self._configure()
    
    def _configure(self) -> None:
        """
        Configura Google Gemini API
        """
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.logger.info("Gemini API configured for embeddings")
            
        except Exception as e:
            self.logger.error("Failed to configure Gemini API", error=str(e))
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um único texto
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            Vetor de embedding
        """
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            
            return result['embedding']
            
        except Exception as e:
            self.logger.error(
                "Failed to generate embedding",
                error=str(e),
                text_length=len(text)
            )
            raise
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = None,
        progress_callback = None,
        document_id: str = None
    ) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em batches
        
        Args:
            texts: Lista de textos
            batch_size: Tamanho do batch (padrão do settings)
            
        Returns:
            Lista de vetores de embeddings
        """
        if not batch_size:
            batch_size = settings.BATCH_SIZE
        
        self.logger.info(
            "Generating embeddings in batches",
            total_texts=len(texts),
            batch_size=batch_size
        )
        
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            self.logger.info(
                "Processing batch",
                batch=batch_num,
                total_batches=total_batches,
                batch_size=len(batch)
            )
            
            try:
                # Gerar embeddings para o batch
                batch_embeddings = []
                for text in batch:
                    embedding = self.generate_embedding(text)
                    batch_embeddings.append(embedding)
                    
                    # Pequeno delay para não sobrecarregar API
                    time.sleep(0.1)
                
                all_embeddings.extend(batch_embeddings)
                
                self.logger.info(
                    "Batch processed successfully",
                    batch=batch_num,
                    embeddings_count=len(batch_embeddings)
                )
                
                # Salvar progresso em arquivo se document_id fornecido
                if document_id:
                    try:
                        progress_file = f"/tmp/processing_{document_id}.txt"
                        with open(progress_file, 'w') as f:
                            f.write(str(batch_num))
                    except:
                        pass  # Silenciar erros de escrita
                
                # Chamar callback de progresso se fornecido
                if progress_callback:
                    progress_callback(batch_num, total_batches)
                
            except Exception as e:
                self.logger.error(
                    "Batch processing failed",
                    batch=batch_num,
                    error=str(e)
                )
                # Continuar com próximo batch mesmo se um falhar
                # Adicionar embeddings vazios para manter índices
                all_embeddings.extend([[] for _ in batch])
        
        successful_embeddings = sum(1 for e in all_embeddings if e)
        
        self.logger.info(
            "Batch embedding generation completed",
            total_texts=len(texts),
            successful=successful_embeddings,
            failed=len(texts) - successful_embeddings
        )
        
        return all_embeddings
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Gera embedding para uma query de busca
        
        Args:
            query: Texto da query
            
        Returns:
            Vetor de embedding
        """
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"  # Tipo diferente para queries
            )
            
            return result['embedding']
            
        except Exception as e:
            self.logger.error(
                "Failed to generate query embedding",
                error=str(e)
            )
            raise
    
    def embed_chunks(
        self,
        chunks: List[Dict[str, any]],
        progress_callback = None,
        document_id: str = None
    ) -> List[Dict[str, any]]:
        """
        Gera embeddings para lista de chunks
        
        Args:
            chunks: Lista de chunks com texto
            
        Returns:
            Chunks com embeddings adicionados
        """
        self.logger.info("Embedding chunks", total_chunks=len(chunks))
        
        # Extrair textos (usar texto com contexto se disponível)
        texts = [
            chunk.get("text_with_context", chunk.get("text", ""))
            for chunk in chunks
        ]
        
        # Gerar embeddings
        embeddings = self.generate_embeddings_batch(
            texts,
            progress_callback=progress_callback,
            document_id=document_id
        )
        
        # Adicionar embeddings aos chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
            chunk["embedding_dim"] = len(embedding) if embedding else 0
        
        # Filtrar chunks que falharam
        successful_chunks = [c for c in chunks if c.get("embedding")]
        
        self.logger.info(
            "Chunk embedding completed",
            total=len(chunks),
            successful=len(successful_chunks),
            failed=len(chunks) - len(successful_chunks)
        )
        
        return successful_chunks

