"""
Serviço de contexto para buscar informações relevantes no ChromaDB.

Este módulo busca trechos relevantes dos documentos LOA e LDO
baseado na pergunta do usuário, usando busca semântica.
"""

from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.services.vector_db import VectorDBService
from app.services.embedding_service import EmbeddingService
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document

logger = logging.getLogger(__name__)


class ContextService:
    """Serviço para buscar contexto relevante dos documentos."""

    def __init__(self):
        """Inicializa o serviço de contexto."""
        self.vector_db = VectorDBService()
        self.embedding_service = EmbeddingService()
    
    def _get_document_collections(self, municipality_id: str, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca as collections dos documentos processados no banco de dados.
        
        Args:
            municipality_id: ID do município (UUID)
            doc_type: Tipo do documento ('LOA' ou 'LDO'), None para ambos
            
        Returns:
            Lista de dicionários com informações dos documentos e suas collections
        """
        db = SessionLocal()
        try:
            query = db.query(Document).filter(
                Document.municipality_id == municipality_id,
                Document.status == "completed",
                Document.chromadb_collection_id.isnot(None)
            )
            
            if doc_type:
                query = query.filter(Document.type == doc_type.upper())
            
            documents = query.all()
            
            return [
                {
                    "document_id": doc.id,
                    "type": doc.type,
                    "collection_name": doc.chromadb_collection_id,
                    "total_chunks": doc.total_chunks,
                    "filename": doc.filename
                }
                for doc in documents
            ]
        finally:
            db.close()

    async def search_loa_context(
        self,
        query: str,
        municipality_id: str,
        n_results: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Busca contexto relevante da LOA.

        Args:
            query: Pergunta/query do usuário
            municipality_id: ID do município (UUID)
            n_results: Número máximo de resultados
            min_similarity: Similaridade mínima (0-1)

        Returns:
            Lista de trechos relevantes com metadados
        """
        try:
            logger.info(f"Buscando contexto LOA para query: {query[:50]}...")
            
            # Buscar documentos LOA processados no banco
            documents = self._get_document_collections(municipality_id, doc_type="LOA")
            
            if not documents:
                logger.warning(f"Nenhum documento LOA encontrado para município {municipality_id}")
                return []
            
            all_contexts = []
            
            # Buscar em todos os documentos LOA
            for doc_info in documents:
                collection_name = doc_info["collection_name"]
                logger.info(f"Buscando em collection LOA: {collection_name}")

                # Gerar embedding da query
                query_embedding = self.embedding_service.generate_embedding(query)

                # Buscar no ChromaDB
                results = self.vector_db.query(
                    collection_name=collection_name,
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )

                # Processar resultados
                if results and "documents" in results and len(results["documents"]) > 0:
                    documents_texts = results["documents"][0]
                    metadatas = results.get("metadatas", [[]])[0]
                    distances = results.get("distances", [[]])[0]

                    for i, doc_text in enumerate(documents_texts):
                        # Converter distância para similaridade (0-1)
                        # Distância menor = mais similar
                        similarity = 1 - (distances[i] if i < len(distances) else 1)

                        if similarity >= min_similarity:
                            context = {
                                "content": doc_text,
                                "similarity": round(similarity, 3),
                                "metadata": metadatas[i] if i < len(metadatas) else {},
                                "source": "LOA",
                                "document": doc_info["filename"]
                            }
                            all_contexts.append(context)
                            logger.debug(f"LOA context found with similarity: {similarity:.3f}")

            # Ordenar por similaridade (maior primeiro) e limitar resultados
            all_contexts.sort(key=lambda x: x["similarity"], reverse=True)
            all_contexts = all_contexts[:n_results]
            
            logger.info(f"Encontrados {len(all_contexts)} trechos relevantes da LOA")
            return all_contexts

        except Exception as e:
            logger.error(f"Erro ao buscar contexto LOA: {str(e)}")
            return []

    async def search_ldo_context(
        self,
        query: str,
        municipality_id: str,
        n_results: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Busca contexto relevante da LDO.

        Args:
            query: Pergunta/query do usuário
            municipality_id: ID do município (UUID)
            n_results: Número máximo de resultados
            min_similarity: Similaridade mínima (0-1)

        Returns:
            Lista de trechos relevantes com metadados
        """
        try:
            logger.info(f"Buscando contexto LDO para query: {query[:50]}...")
            
            # Buscar documentos LDO processados no banco
            documents = self._get_document_collections(municipality_id, doc_type="LDO")
            
            if not documents:
                logger.warning(f"Nenhum documento LDO encontrado para município {municipality_id}")
                return []
            
            all_contexts = []
            
            # Buscar em todos os documentos LDO
            for doc_info in documents:
                collection_name = doc_info["collection_name"]
                logger.info(f"Buscando em collection LDO: {collection_name}")

                # Gerar embedding da query
                query_embedding = self.embedding_service.generate_embedding(query)

                # Buscar no ChromaDB
                results = self.vector_db.query(
                    collection_name=collection_name,
                    query_embeddings=[query_embedding],
                    n_results=n_results
                )

                # Processar resultados
                if results and "documents" in results and len(results["documents"]) > 0:
                    documents_texts = results["documents"][0]
                    metadatas = results.get("metadatas", [[]])[0]
                    distances = results.get("distances", [[]])[0]

                    for i, doc_text in enumerate(documents_texts):
                        similarity = 1 - (distances[i] if i < len(distances) else 1)

                        if similarity >= min_similarity:
                            context = {
                                "content": doc_text,
                                "similarity": round(similarity, 3),
                                "metadata": metadatas[i] if i < len(metadatas) else {},
                                "source": "LDO",
                                "document": doc_info["filename"]
                            }
                            all_contexts.append(context)
                            logger.debug(f"LDO context found with similarity: {similarity:.3f}")

            # Ordenar por similaridade (maior primeiro) e limitar resultados
            all_contexts.sort(key=lambda x: x["similarity"], reverse=True)
            all_contexts = all_contexts[:n_results]
            
            logger.info(f"Encontrados {len(all_contexts)} trechos relevantes da LDO")
            return all_contexts

        except Exception as e:
            logger.error(f"Erro ao buscar contexto LDO: {str(e)}")
            return []

    async def search_all_context(
        self,
        query: str,
        municipality_id: int,
        n_results_per_source: int = 5,
        min_similarity: float = 0.5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Busca contexto em todas as fontes (LOA e LDO).

        Args:
            query: Pergunta/query do usuário
            municipality_id: ID do município
            n_results_per_source: Número de resultados por fonte
            min_similarity: Similaridade mínima

        Returns:
            Dicionário com contextos de cada fonte
        """
        logger.info(f"Buscando contexto em todas as fontes para: {query[:50]}...")

        # Buscar em paralelo (await para cada um)
        loa_contexts = await self.search_loa_context(
            query, municipality_id, n_results_per_source, min_similarity
        )
        
        ldo_contexts = await self.search_ldo_context(
            query, municipality_id, n_results_per_source, min_similarity
        )

        return {
            "loa": loa_contexts,
            "ldo": ldo_contexts,
            "total_results": len(loa_contexts) + len(ldo_contexts)
        }

    def get_collection_stats(self, municipality_id: int) -> Dict[str, Any]:
        """
        Obtém estatísticas das coleções de um município.

        Args:
            municipality_id: ID do município

        Returns:
            Estatísticas das coleções
        """
        stats = {
            "municipality_id": municipality_id,
            "loa": {
                "exists": False,
                "document_count": 0
            },
            "ldo": {
                "exists": False,
                "document_count": 0
            }
        }

        try:
            # LOA
            loa_collection_name = f"loa_{municipality_id}"
            if self.vector_db.collection_exists(loa_collection_name):
                stats["loa"]["exists"] = True
                # Tentar obter contagem
                try:
                    collection = self.vector_db.client.get_collection(loa_collection_name)
                    stats["loa"]["document_count"] = collection.count()
                except:
                    pass

            # LDO
            ldo_collection_name = f"ldo_{municipality_id}"
            if self.vector_db.collection_exists(ldo_collection_name):
                stats["ldo"]["exists"] = True
                try:
                    collection = self.vector_db.client.get_collection(ldo_collection_name)
                    stats["ldo"]["document_count"] = collection.count()
                except:
                    pass

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")

        return stats

    def has_documents(self, municipality_id: str) -> bool:
        """
        Verifica se há documentos processados para o município.

        Args:
            municipality_id: ID do município (UUID)

        Returns:
            True se há documentos, False caso contrário
        """
        documents = self._get_document_collections(municipality_id)
        has_docs = len(documents) > 0
        
        if has_docs:
            doc_types = [d["type"] for d in documents]
            logger.info(f"Município {municipality_id} tem {len(documents)} documento(s): {', '.join(doc_types)}")
        else:
            logger.warning(f"Município {municipality_id} não tem documentos processados")
        
        return has_docs

    async def get_sample_questions(
        self,
        municipality_id: int,
        max_questions: int = 5
    ) -> List[str]:
        """
        Gera perguntas exemplo baseadas nos documentos disponíveis.

        Args:
            municipality_id: ID do município
            max_questions: Número máximo de perguntas

        Returns:
            Lista de perguntas exemplo
        """
        questions = []

        stats = self.get_collection_stats(municipality_id)

        if stats["loa"]["exists"]:
            questions.extend([
                "Qual foi o orçamento total previsto?",
                "Quanto foi destinado para a área da saúde?",
                "Como está distribuído o orçamento por secretaria?"
            ])

        if stats["ldo"]["exists"]:
            questions.extend([
                "Quais são as metas e prioridades estabelecidas?",
                "Quais os principais objetivos fiscais?"
            ])

        if stats["loa"]["exists"] and stats["ldo"]["exists"]:
            questions.extend([
                "Compare o planejado na LDO com o orçado na LOA",
                "As metas da LDO estão alinhadas com a LOA?"
            ])

        return questions[:max_questions]


# Singleton para reutilização
_context_service: Optional[ContextService] = None


def get_context_service() -> ContextService:
    """
    Obtém uma instância singleton do serviço de contexto.

    Returns:
        Instância do ContextService
    """
    global _context_service
    if _context_service is None:
        _context_service = ContextService()
    return _context_service

