"""
Vector Database Service - Integração com ChromaDB
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import structlog
import hashlib

from app.core.config import settings

logger = structlog.get_logger()


class VectorDBService:
    """
    Serviço para gerenciar embeddings no ChromaDB
    """
    
    def __init__(self):
        self.logger = logger
        self.client = None
        self._connected = False
    
    def _ensure_connection(self) -> None:
        """
        Garante que existe uma conexão com o ChromaDB (lazy connection)
        """
        if self._connected and self.client is not None:
            return
            
        try:
            # Usar HttpClient simples sem settings customizadas para evitar conflitos
            import chromadb
            
            # Usar o HttpClient padrão SEM tenant/database/settings
            self.client = chromadb.HttpClient(
                host=settings.CHROMADB_HOST,
                port=settings.CHROMADB_PORT
            )
            
            # Testar conexão
            self.client.heartbeat()
            
            self._connected = True
            
            self.logger.info(
                "Connected to ChromaDB",
                host=settings.CHROMADB_HOST,
                port=settings.CHROMADB_PORT
            )
            
        except Exception as e:
            self.logger.warning(
                "Failed to connect to ChromaDB - will retry on next operation",
                error=str(e),
                host=settings.CHROMADB_HOST
            )
            self.client = None
            self._connected = False
            raise
    
    def create_collection(
        self,
        collection_name: str,
        metadata: Dict = None
    ) -> str:
        """
        Cria uma collection no ChromaDB
        
        Args:
            collection_name: Nome da collection
            metadata: Metadados da collection
            
        Returns:
            ID da collection criada
        """
        try:
            self._ensure_connection()
            self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata or {}
            )
            
            self.logger.info(
                "Collection created",
                collection_name=collection_name
            )
            
            return collection_name
            
        except Exception as e:
            self.logger.error(
                "Failed to create collection",
                collection_name=collection_name,
                error=str(e)
            )
            raise
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Verifica se uma collection existe no ChromaDB
        
        Args:
            collection_name: Nome da collection
            
        Returns:
            True se a collection existe, False caso contrário
        """
        try:
            self._ensure_connection()
            collections = self.client.list_collections()
            return any(col.name == collection_name for col in collections)
        except Exception as e:
            self.logger.error(
                "Failed to check collection existence",
                collection_name=collection_name,
                error=str(e)
            )
            return False
    
    def add_embeddings(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict] = None,
        ids: List[str] = None
    ) -> int:
        """
        Adiciona embeddings à collection
        
        Args:
            collection_name: Nome da collection
            embeddings: Lista de vetores de embeddings
            texts: Lista de textos correspondentes
            metadatas: Lista de metadados (opcional)
            ids: Lista de IDs (gerados automaticamente se não fornecidos)
            
        Returns:
            Número de embeddings adicionados
        """
        try:
            self._ensure_connection()
            collection = self.client.get_or_create_collection(name=collection_name)
            
            # Gerar IDs se não fornecidos
            if not ids:
                ids = [self._generate_id(text, i) for i, text in enumerate(texts)]
            
            # Garantir que metadatas está no formato correto
            if not metadatas:
                metadatas = [{} for _ in texts]
            
            # Adicionar embeddings
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(
                "Embeddings added to collection",
                collection_name=collection_name,
                count=len(embeddings)
            )
            
            return len(embeddings)
            
        except Exception as e:
            self.logger.error(
                "Failed to add embeddings",
                collection_name=collection_name,
                error=str(e)
            )
            raise
    
    def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> Dict:
        """
        Busca documentos similares na collection
        
        Args:
            collection_name: Nome da collection
            query_embeddings: Vetores de query
            n_results: Número de resultados a retornar
            where: Filtros de metadados
            where_document: Filtros de documento
            
        Returns:
            Resultados da busca
        """
        try:
            self._ensure_connection()
            collection = self.client.get_or_create_collection(name=collection_name)
            
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )
            
            self.logger.info(
                "Query executed",
                collection_name=collection_name,
                n_results=n_results
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Query failed",
                collection_name=collection_name,
                error=str(e)
            )
            raise
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Deleta uma collection
        
        Args:
            collection_name: Nome da collection
            
        Returns:
            True se deletada com sucesso
        """
        try:
            self._ensure_connection()
            self.client.delete_collection(name=collection_name)
            
            self.logger.info(
                "Collection deleted",
                collection_name=collection_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete collection",
                collection_name=collection_name,
                error=str(e)
            )
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Obtém informações sobre uma collection
        
        Args:
            collection_name: Nome da collection
            
        Returns:
            Informações da collection
        """
        try:
            self._ensure_connection()
            collection = self.client.get_collection(name=collection_name)
            
            return {
                "name": collection.name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get collection info",
                collection_name=collection_name,
                error=str(e)
            )
            return {
                "name": collection_name,
                "count": 0,
                "metadata": {},
                "error": str(e)
            }
    
    def list_collections(self) -> List[str]:
        """
        Lista todas as collections
        
        Returns:
            Lista de nomes de collections
        """
        try:
            self._ensure_connection()
            collections = self.client.list_collections()
            return [c.name for c in collections]
            
        except Exception as e:
            self.logger.error("Failed to list collections", error=str(e))
            return []
    
    def _generate_id(self, text: str, index: int) -> str:
        """
        Gera ID único para um embedding
        
        Args:
            text: Texto do chunk
            index: Índice do chunk
            
        Returns:
            ID único
        """
        # Hash do texto + índice
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{index}_{text_hash}"
    
    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Dict = None
    ):
        """
        Obtém uma collection existente ou cria uma nova
        
        Args:
            collection_name: Nome da collection
            metadata: Metadados da collection
            
        Returns:
            Collection do ChromaDB
        """
        try:
            self._ensure_connection()
            
            # ChromaDB requer pelo menos um campo de metadata
            if not metadata or len(metadata) == 0:
                metadata = {"source": "portal", "type": "transparency"}
            
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata
            )
            
            self.logger.debug(
                "Collection retrieved or created",
                collection_name=collection_name
            )
            
            return collection
            
        except Exception as e:
            self.logger.error(
                "Failed to get or create collection",
                collection_name=collection_name,
                error=str(e)
            )
            raise
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Deleta uma collection do ChromaDB
        
        Args:
            collection_name: Nome da collection
        """
        try:
            self._ensure_connection()
            self.client.delete_collection(name=collection_name)
            
            self.logger.info(
                "Collection deleted",
                collection_name=collection_name
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to delete collection",
                collection_name=collection_name,
                error=str(e)
            )
            raise
    
    def health_check(self) -> bool:
        """
        Verifica se ChromaDB está acessível
        
        Returns:
            True se saudável
        """
        try:
            self._ensure_connection()
            self.client.heartbeat()
            return True
        except Exception as e:
            self.logger.error("ChromaDB health check failed", error=str(e))
            return False

