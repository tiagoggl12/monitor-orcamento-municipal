"""
Serviço de Busca Híbrida (Fase 3)
Combina busca estruturada (PostgreSQL) + semântica (ChromaDB)
"""

import logging
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.parsed_data import ParsedData
from app.models.raw_file import RawFile
from app.models.file_schema import FileSchema
from app.services.vector_db import VectorDBService
from app.services.embedding_service import EmbeddingService
from app.services.data_lineage_service import DataLineageService
from app.services.query_planner_service import QueryPlan

logger = logging.getLogger(__name__)


class SearchResult:
    """Representa um resultado de busca"""
    
    def __init__(
        self,
        parsed_data: ParsedData,
        raw_file: RawFile,
        score: float,
        match_type: str,  # "structured" | "semantic" | "hybrid"
        matched_fields: List[str] = None
    ):
        self.parsed_data = parsed_data
        self.raw_file = raw_file
        self.score = score
        self.match_type = match_type
        self.matched_fields = matched_fields or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_data_id": self.parsed_data.id,
            "raw_file_id": self.raw_file.id,
            "filename": self.raw_file.filename,
            "row_number": self.parsed_data.row_number,
            "data": self.parsed_data.data,
            "text_content": self.parsed_data.text_content,
            "score": self.score,
            "match_type": self.match_type,
            "matched_fields": self.matched_fields,
            "raw_file_hash": self.raw_file.sha256_hash
        }


class HybridSearchService:
    """
    Executa busca híbrida combinando:
    - Busca estruturada no PostgreSQL (campo/valor exato)
    - Busca semântica no ChromaDB (similaridade de embeddings)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.vector_db = VectorDBService()
        self.embedding_service = EmbeddingService()
        self.lineage_service = DataLineageService(db)
    
    async def execute_search(
        self,
        query_plan: QueryPlan,
        user_question: str,
        limit: int = 20,
        message_id: Optional[str] = None,
        chat_session_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Executa busca híbrida baseada no query plan
        
        Args:
            query_plan: Plano gerado pelo QueryPlanner
            user_question: Pergunta original do usuário
            limit: Limite de resultados
            message_id: ID da mensagem (para lineage)
            chat_session_id: ID da sessão (para lineage)
        
        Returns:
            Lista de resultados ranqueados
        """
        try:
            logger.info(f"🔍 Executing hybrid search: {query_plan.strategy}")
            
            results = []
            
            # Executar busca baseada na estratégia
            if query_plan.strategy == "structured":
                results = await self._structured_search(query_plan, limit)
            
            elif query_plan.strategy == "semantic":
                results = await self._semantic_search(
                    query_plan.semantic_query,
                    limit
                )
            
            elif query_plan.strategy == "hybrid":
                # AMBAS as buscas
                structured_results = await self._structured_search(query_plan, limit // 2)
                semantic_results = await self._semantic_search(
                    query_plan.semantic_query,
                    limit // 2
                )
                
                # Combinar e deduplic
                results = self._merge_and_deduplicate(
                    structured_results,
                    semantic_results
                )
            
            # Limitar resultados
            results = results[:limit]
            
            # Registrar lineage (para auditoria)
            if message_id and chat_session_id and results:
                parsed_data_ids = [r.parsed_data.id for r in results]
                retrieval_scores = {r.parsed_data.id: r.score for r in results}
                
                self.lineage_service.log_chat_retrieval(
                    parsed_data_ids=parsed_data_ids,
                    chat_session_id=chat_session_id,
                    message_id=message_id,
                    retrieval_scores=retrieval_scores
                )
            
            logger.info(f"✅ Search completed: {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error executing hybrid search: {e}")
            logger.exception(e)
            return []
    
    async def _structured_search(
        self,
        query_plan: QueryPlan,
        limit: int
    ) -> List[SearchResult]:
        """
        Busca estruturada no PostgreSQL
        Usa field_mappings e filters do query_plan
        """
        try:
            logger.info("   Executing structured search...")
            
            if not query_plan.filters and not query_plan.field_mappings:
                logger.warning("   No filters for structured search")
                return []
            
            # Construir query PostgreSQL
            query = self.db.query(ParsedData)
            
            # Aplicar filtros
            conditions = []
            matched_fields = []
            
            for filter_def in query_plan.filters:
                file_name = filter_def.get("file_name")
                column_name = filter_def.get("column_name")
                operator = filter_def.get("operator", "equals")
                value = filter_def.get("value")
                
                if not all([file_name, column_name, value]):
                    continue
                
                # Buscar raw_file_id do arquivo
                raw_file = self.db.query(RawFile).filter(
                    RawFile.filename == file_name
                ).first()
                
                if not raw_file:
                    logger.warning(f"   File not found: {file_name}")
                    continue
                
                # Condição: data->>column_name operator value
                if operator == "equals":
                    condition = ParsedData.data[column_name].as_string() == str(value)
                elif operator == "contains":
                    condition = ParsedData.data[column_name].as_string().contains(str(value))
                # Adicionar mais operadores conforme necessário
                
                conditions.append(ParsedData.raw_file_id == raw_file.id)
                conditions.append(condition)
                matched_fields.append(column_name)
            
            if not conditions:
                return []
            
            # Executar query
            query = query.filter(and_(*conditions))
            parsed_data_list = query.limit(limit).all()
            
            logger.info(f"   Structured search: {len(parsed_data_list)} results")
            
            # Converter para SearchResult
            results = []
            for parsed_data in parsed_data_list:
                raw_file = self.db.query(RawFile).filter(
                    RawFile.id == parsed_data.raw_file_id
                ).first()
                
                result = SearchResult(
                    parsed_data=parsed_data,
                    raw_file=raw_file,
                    score=1.0,  # Structured = match exato
                    match_type="structured",
                    matched_fields=matched_fields
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"   Error in structured search: {e}")
            logger.exception(e)
            return []
    
    async def _semantic_search(
        self,
        query_text: str,
        limit: int
    ) -> List[SearchResult]:
        """
        Busca semântica no ChromaDB
        Usa embeddings para similaridade
        """
        try:
            logger.info("   Executing semantic search...")
            
            # Gerar embedding da query
            query_embedding = self.embedding_service.generate(query_text)
            
            # Buscar no ChromaDB
            # Buscar em todas as collections de portal
            all_results = []
            
            # Listar collections
            collections = self.vector_db.client.list_collections()
            portal_collections = [
                c for c in collections
                if c.name.startswith("portal_")
            ]
            
            logger.info(f"   Searching in {len(portal_collections)} collections")
            
            for collection in portal_collections:
                try:
                    chroma_collection = self.vector_db.client.get_collection(
                        name=collection.name
                    )
                    
                    results = chroma_collection.query(
                        query_embeddings=[query_embedding],
                        n_results=limit,
                        include=["metadatas", "distances", "documents"]
                    )
                    
                    if results and results["ids"] and results["ids"][0]:
                        for i, doc_id in enumerate(results["ids"][0]):
                            metadata = results["metadatas"][0][i]
                            distance = results["distances"][0][i]
                            
                            # Converter distance para score (0-1)
                            # Distance menor = mais similar
                            score = 1.0 / (1.0 + distance)
                            
                            # Buscar parsed_data_id do metadata
                            parsed_data_id = metadata.get("parsed_data_id")
                            
                            if parsed_data_id:
                                all_results.append({
                                    "parsed_data_id": parsed_data_id,
                                    "score": score,
                                    "collection": collection.name
                                })
                
                except Exception as e:
                    logger.warning(f"   Error searching collection {collection.name}: {e}")
                    continue
            
            # Ordenar por score
            all_results.sort(key=lambda x: x["score"], reverse=True)
            all_results = all_results[:limit]
            
            logger.info(f"   Semantic search: {len(all_results)} results")
            
            # Buscar dados completos do PostgreSQL
            search_results = []
            
            for result in all_results:
                parsed_data = self.db.query(ParsedData).filter(
                    ParsedData.id == result["parsed_data_id"]
                ).first()
                
                if not parsed_data:
                    continue
                
                raw_file = self.db.query(RawFile).filter(
                    RawFile.id == parsed_data.raw_file_id
                ).first()
                
                if not raw_file:
                    continue
                
                search_result = SearchResult(
                    parsed_data=parsed_data,
                    raw_file=raw_file,
                    score=result["score"],
                    match_type="semantic",
                    matched_fields=[]
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"   Error in semantic search: {e}")
            logger.exception(e)
            return []
    
    def _merge_and_deduplicate(
        self,
        structured_results: List[SearchResult],
        semantic_results: List[SearchResult]
    ) -> List[SearchResult]:
        """
        Combina e deduplicamresultados
        - Remove duplicatas (mesmo parsed_data_id)
        - Prioriza structured (mais preciso)
        - Mantém score mais alto
        """
        logger.info("   Merging and deduplicating results...")
        
        # Usar dict para deduplic
        results_dict: Dict[str, SearchResult] = {}
        
        # Adicionar structured (prioridade)
        for result in structured_results:
            parsed_id = result.parsed_data.id
            
            if parsed_id not in results_dict:
                # Marcar como hybrid se veio de structured
                result.match_type = "hybrid"
                results_dict[parsed_id] = result
        
        # Adicionar semantic (se não duplicado)
        for result in semantic_results:
            parsed_id = result.parsed_data.id
            
            if parsed_id in results_dict:
                # Já existe (structured), aumentar score
                existing = results_dict[parsed_id]
                existing.score = (existing.score + result.score) / 2
                existing.match_type = "hybrid"
            else:
                results_dict[parsed_id] = result
        
        # Converter para lista e ordenar por score
        merged_results = list(results_dict.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"   Merged: {len(merged_results)} unique results")
        
        return merged_results

