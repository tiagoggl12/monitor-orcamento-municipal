"""
Tools Executors
===============

Implementa os executores para cada ferramenta definida no tools_registry.
Quando o Gemini decide usar uma ferramenta, o executor correspondente é chamado.
"""

from typing import Dict, Any, List, Optional
import structlog
from sqlalchemy.orm import Session

from app.services.vector_db import VectorDBService
from app.services.embedding_service import EmbeddingService
from app.models.document import Document

logger = structlog.get_logger(__name__)


class ToolsExecutor:
    """
    Classe que executa as ferramentas (tools) chamadas pelo Gemini
    """
    
    def __init__(self):
        self.vector_db = VectorDBService()
        self.embedding_service = EmbeddingService()
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_arguments: Dict[str, Any],
        municipality_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Executa uma ferramenta específica
        
        Args:
            tool_name: Nome da ferramenta
            tool_arguments: Argumentos da ferramenta
            municipality_id: ID do município
            db: Sessão do banco de dados
            
        Returns:
            Resultado da execução
        """
        logger.info(
            f"Executing tool: {tool_name}",
            tool_name=tool_name,
            arguments=tool_arguments
        )
        
        try:
            if tool_name == "search_licitacoes":
                return await self.search_licitacoes(tool_arguments, municipality_id)
            elif tool_name == "search_loa":
                return await self.search_loa(tool_arguments, municipality_id, db)
            elif tool_name == "search_ldo":
                return await self.search_ldo(tool_arguments, municipality_id, db)
            elif tool_name == "cross_reference":
                return await self.cross_reference(tool_arguments, municipality_id, db)
            elif tool_name == "analyze_budget_execution":
                return await self.analyze_budget_execution(tool_arguments, municipality_id, db)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    async def search_licitacoes(
        self,
        arguments: Dict[str, Any],
        municipality_id: str
    ) -> Dict[str, Any]:
        """
        Busca licitações do Portal da Transparência com filtros
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        
        # Construir filtro WHERE do ChromaDB
        where_filter = {}
        
        # Filtro por órgão (CRÍTICO para precisão)
        if "origem" in arguments and arguments["origem"]:
            where_filter["origem"] = arguments["origem"].upper().strip()
        
        # Filtro por edital
        if "edital" in arguments and arguments["edital"]:
            where_filter["edital"] = int(arguments["edital"])
        elif "edital_min" in arguments or "edital_max" in arguments:
            where_filter["edital"] = {}
            if "edital_min" in arguments:
                where_filter["edital"]["$gte"] = int(arguments["edital_min"])
            if "edital_max" in arguments:
                where_filter["edital"]["$lte"] = int(arguments["edital_max"])
        
        # Filtro por modalidade
        if "modalidade" in arguments and arguments["modalidade"]:
            where_filter["modalidade"] = arguments["modalidade"].upper().strip()
        
        # Filtro por data
        if "data_inicio" in arguments or "data_fim" in arguments:
            where_filter["data_abertura_timestamp"] = {}
            if "data_inicio" in arguments:
                where_filter["data_abertura_timestamp"]["$gte"] = arguments["data_inicio"]
            if "data_fim" in arguments:
                where_filter["data_abertura_timestamp"]["$lte"] = arguments["data_fim"]
        
        # Filtro por valor
        if "valor_min" in arguments or "valor_max" in arguments:
            where_filter["valor_total"] = {}
            if "valor_min" in arguments:
                where_filter["valor_total"]["$gte"] = float(arguments["valor_min"])
            if "valor_max" in arguments:
                where_filter["valor_total"]["$lte"] = float(arguments["valor_max"])
        
        logger.info(f"Searching licitações with filters", where_filter=where_filter, query=query)
        
        # Gerar embedding da query
        query_embedding = self.embedding_service.generate_embeddings_batch([query])[0]
        
        # Buscar em todas as collections do portal
        all_collections = self.vector_db.client.list_collections()
        portal_collections = [c.name for c in all_collections if c.name.startswith("portal_")]
        
        results = []
        
        for collection_name in portal_collections:
            try:
                collection = self.vector_db.client.get_collection(name=collection_name)
                
                # Query com filtros estruturados
                query_result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit * 2,  # Buscar mais para garantir diversidade
                    where=where_filter if where_filter else None,
                    include=["documents", "metadatas", "distances"]
                )
                
                if query_result and query_result.get("documents"):
                    for i, doc_content in enumerate(query_result["documents"][0]):
                        metadata = query_result["metadatas"][0][i] if query_result.get("metadatas") else {}
                        distance = query_result["distances"][0][i] if query_result.get("distances") else None
                        
                        results.append({
                            "content": doc_content,
                            "metadata": metadata,
                            "similarity": 1 - distance if distance is not None else 0,
                            "collection": collection_name
                        })
                
            except Exception as e:
                logger.warning(f"Error searching collection {collection_name}: {e}")
                continue
        
        # Ordenar por similaridade e limitar
        results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = results[:limit]
        
        logger.info(f"Found {len(top_results)} licitações")
        
        return {
            "success": True,
            "tool": "search_licitacoes",
            "query": query,
            "filters": where_filter,
            "results_count": len(top_results),
            "results": top_results
        }
    
    async def search_loa(
        self,
        arguments: Dict[str, Any],
        municipality_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Busca dados na LOA (Lei Orçamentária Anual)
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        
        # Buscar documentos LOA do município
        loa_docs = db.query(Document).filter(
            Document.municipality_id == municipality_id,
            Document.document_type == "loa"
        )
        
        # Filtrar por ano se especificado
        if "ano" in arguments and arguments["ano"]:
            loa_docs = loa_docs.filter(Document.year == int(arguments["ano"]))
        
        loa_docs = loa_docs.all()
        
        if not loa_docs:
            return {
                "success": True,
                "tool": "search_loa",
                "query": query,
                "results_count": 0,
                "results": [],
                "message": "Nenhum documento LOA encontrado para este município"
            }
        
        # Gerar embedding da query
        query_embedding = self.embedding_service.generate_embeddings_batch([query])[0]
        
        results = []
        
        # Buscar em cada collection LOA
        for doc in loa_docs:
            collection_name = f"doc_{doc.id}"
            
            try:
                collection = self.vector_db.client.get_collection(name=collection_name)
                
                # Query semântica
                query_result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
                
                if query_result and query_result.get("documents"):
                    for i, doc_content in enumerate(query_result["documents"][0]):
                        metadata = query_result["metadatas"][0][i] if query_result.get("metadatas") else {}
                        distance = query_result["distances"][0][i] if query_result.get("distances") else None
                        
                        results.append({
                            "content": doc_content,
                            "metadata": metadata,
                            "similarity": 1 - distance if distance is not None else 0,
                            "document_id": doc.id,
                            "document_name": doc.file_name,
                            "year": doc.year
                        })
                
            except Exception as e:
                logger.warning(f"Error searching LOA collection {collection_name}: {e}")
                continue
        
        # Ordenar por similaridade
        results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = results[:limit]
        
        logger.info(f"Found {len(top_results)} LOA results")
        
        return {
            "success": True,
            "tool": "search_loa",
            "query": query,
            "filters": arguments,
            "results_count": len(top_results),
            "results": top_results
        }
    
    async def search_ldo(
        self,
        arguments: Dict[str, Any],
        municipality_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Busca dados na LDO (Lei de Diretrizes Orçamentárias)
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        
        # Buscar documentos LDO do município
        ldo_docs = db.query(Document).filter(
            Document.municipality_id == municipality_id,
            Document.document_type == "ldo"
        )
        
        # Filtrar por ano se especificado
        if "ano" in arguments and arguments["ano"]:
            ldo_docs = ldo_docs.filter(Document.year == int(arguments["ano"]))
        
        ldo_docs = ldo_docs.all()
        
        if not ldo_docs:
            return {
                "success": True,
                "tool": "search_ldo",
                "query": query,
                "results_count": 0,
                "results": [],
                "message": "Nenhum documento LDO encontrado para este município"
            }
        
        # Gerar embedding da query
        query_embedding = self.embedding_service.generate_embeddings_batch([query])[0]
        
        results = []
        
        # Buscar em cada collection LDO
        for doc in ldo_docs:
            collection_name = f"doc_{doc.id}"
            
            try:
                collection = self.vector_db.client.get_collection(name=collection_name)
                
                # Query semântica
                query_result = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
                
                if query_result and query_result.get("documents"):
                    for i, doc_content in enumerate(query_result["documents"][0]):
                        metadata = query_result["metadatas"][0][i] if query_result.get("metadatas") else {}
                        distance = query_result["distances"][0][i] if query_result.get("distances") else None
                        
                        results.append({
                            "content": doc_content,
                            "metadata": metadata,
                            "similarity": 1 - distance if distance is not None else 0,
                            "document_id": doc.id,
                            "document_name": doc.file_name,
                            "year": doc.year
                        })
                
            except Exception as e:
                logger.warning(f"Error searching LDO collection {collection_name}: {e}")
                continue
        
        # Ordenar por similaridade
        results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = results[:limit]
        
        logger.info(f"Found {len(top_results)} LDO results")
        
        return {
            "success": True,
            "tool": "search_ldo",
            "query": query,
            "filters": arguments,
            "results_count": len(top_results),
            "results": top_results
        }
    
    async def cross_reference(
        self,
        arguments: Dict[str, Any],
        municipality_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Cruza dados entre Portal, LOA e LDO
        """
        analysis_type = arguments.get("analysis_type")
        orgao = arguments.get("orgao")
        ano = arguments.get("ano")
        
        logger.info(f"Cross-reference analysis: {analysis_type}", orgao=orgao, ano=ano)
        
        # Esta é uma análise complexa que envolve múltiplas buscas
        # Por ora, vamos implementar a análise básica de órgão completo
        
        if analysis_type == "orgao_completo" and orgao:
            # Buscar licitações do órgão
            licitacoes_result = await self.search_licitacoes(
                {"query": "licitações contratos", "origem": orgao, "limit": 10},
                municipality_id
            )
            
            # Buscar orçamento do órgão na LOA
            loa_result = await self.search_loa(
                {"query": f"despesas orçamento {orgao}", "ano": ano, "limit": 5},
                municipality_id,
                db
            )
            
            return {
                "success": True,
                "tool": "cross_reference",
                "analysis_type": analysis_type,
                "orgao": orgao,
                "ano": ano,
                "licitacoes": licitacoes_result.get("results", []),
                "orcamento_loa": loa_result.get("results", []),
                "summary": {
                    "licitacoes_count": licitacoes_result.get("results_count", 0),
                    "orcamento_entries": loa_result.get("results_count", 0)
                }
            }
        
        # Outras análises podem ser implementadas aqui
        return {
            "success": True,
            "tool": "cross_reference",
            "analysis_type": analysis_type,
            "message": "Análise específica ainda não implementada"
        }
    
    async def analyze_budget_execution(
        self,
        arguments: Dict[str, Any],
        municipality_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Analisa execução orçamentária
        """
        orgao = arguments.get("orgao")
        ano = arguments.get("ano")
        
        logger.info(f"Analyzing budget execution", orgao=orgao, ano=ano)
        
        # Buscar dados de execução no Portal
        execucao_query = f"empenho liquidado pago {orgao if orgao else ''}"
        
        # Buscar licitações/contratos
        licitacoes_result = await self.search_licitacoes(
            {"query": execucao_query, "origem": orgao if orgao else None, "limit": 10},
            municipality_id
        )
        
        # Buscar dotação prevista na LOA
        loa_result = await self.search_loa(
            {"query": f"dotação prevista {orgao if orgao else ''}", "ano": ano, "limit": 5},
            municipality_id,
            db
        )
        
        return {
            "success": True,
            "tool": "analyze_budget_execution",
            "orgao": orgao,
            "ano": ano,
            "execucao_data": licitacoes_result.get("results", []),
            "dotacao_prevista": loa_result.get("results", []),
            "summary": {
                "execucao_count": licitacoes_result.get("results_count", 0),
                "orcamento_count": loa_result.get("results_count", 0)
            }
        }

