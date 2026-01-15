"""
Orquestrador Gemini - Cérebro do sistema.

Este módulo coordena todo o processo de análise:
1. Busca contexto relevante (LOA/LDO) no ChromaDB
2. Identifica packages relevantes do Portal da Transparência
3. Cruza dados de múltiplas fontes
4. Chama o Gemini AI para análise
5. Gera resposta estruturada
"""

from typing import Dict, Any, Optional, List
import json
import time
import logging
import google.generativeai as genai

from app.core.config import settings
from app.services.prompt_builder import PromptBuilder
from app.services.response_builder import ResponseBuilder
from app.services.context_service import ContextService
from app.services.portal_client import PortalTransparenciaClient
from app.services.cache_service import CacheService
from app.services.vector_db import VectorDBService
from app.services.tools_registry import get_tools, get_tools_summary
from app.services.tools_executors import ToolsExecutor
from app.services.metadata_catalog_service import MetadataCatalogService
from app.schemas.request_schemas import GeminiResponse
from sqlalchemy.orm import Session

# FASE 3: Query Planning + Hybrid Search + Explainable AI
from app.services.query_planner_service import QueryPlannerService
from app.services.hybrid_search_service import HybridSearchService
from app.services.explainable_response_builder import ExplainableResponseBuilder

logger = logging.getLogger(__name__)


class GeminiOrchestrator:
    """Orquestrador principal que coordena análise com Gemini AI."""

    def __init__(self):
        """Inicializa o orquestrador."""
        # Configurar Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # Serviços
        self.prompt_builder = PromptBuilder()
        self.response_builder = ResponseBuilder()
        self.context_service = ContextService()
        self.portal_client = PortalTransparenciaClient()
        self.cache_service: Optional[CacheService] = None
        self.vector_db = VectorDBService()
        
        # Novos serviços para Function Calling
        self.tools_executor = ToolsExecutor()
        self.metadata_catalog = MetadataCatalogService()
        
        # FASE 3: Serviços de busca híbrida e respostas explicáveis
        self.query_planner: Optional[QueryPlannerService] = None
        self.hybrid_search: Optional[HybridSearchService] = None
        self.explainable_builder = ExplainableResponseBuilder()

        logger.info(f"GeminiOrchestrator inicializado com modelo: {settings.GEMINI_MODEL}")
        logger.info("Function Calling habilitado com ferramentas de busca estruturada")
        logger.info("FASE 3: Query Planning + Hybrid Search + Explainable AI disponível")

    async def _get_cache_service(self) -> CacheService:
        """Obtém ou cria instância do serviço de cache."""
        if self.cache_service is None:
            from app.services.cache_service import get_cache_service
            self.cache_service = await get_cache_service()
        return self.cache_service

    async def process_question(
        self,
        question: str,
        session_id: str,
        municipality_data: Dict[str, Any],
        chat_history: Optional[List[Dict[str, str]]] = None,
        db: Optional[Session] = None,
        use_function_calling: bool = True,
        use_phase3: bool = True,
        message_id: Optional[str] = None
    ) -> GeminiResponse:
        """
        Processa uma pergunta do usuário.

        Args:
            question: Pergunta do usuário
            session_id: ID da sessão de chat
            municipality_data: Dados do município (name, state, year, id)
            chat_history: Histórico de mensagens anteriores (role, content)

        Returns:
            GeminiResponse estruturada
        """
        start_time = time.time()
        
        if chat_history is None:
            chat_history = []
        
        try:
            logger.info(f"Processando pergunta: {question[:100]}...")
            logger.info(f"Município: {municipality_data.get('name')} - {municipality_data.get('state')}")

            municipality_id = municipality_data.get("id")
            municipality_name = municipality_data.get("name", "Desconhecido")
            state = municipality_data.get("state", "")
            year = municipality_data.get("year", 2023)

            # 🚀 FASE 3: Query Planning + Hybrid Search + Explainable AI
            if use_phase3 and db is not None:
                logger.info("🚀 Usando FASE 3: Query Planning + Hybrid Search + Explainable AI")
                try:
                    return await self._process_with_phase3(
                        question=question,
                        session_id=session_id,
                        municipality_id=municipality_id,
                        chat_history=chat_history,
                        db=db,
                        message_id=message_id
                    )
                except Exception as e:
                    logger.error(f"❌ Erro na Fase 3, fallback para function calling: {e}")
                    # Continuar para function calling se Fase 3 falhar

            # 🆕 FUNCTION CALLING: Usar busca estruturada com agentes
            if use_function_calling and db is not None:
                logger.info("🤖 Usando Function Calling com busca estruturada")
                try:
                    return await self._process_with_function_calling(
                        question=question,
                        session_id=session_id,
                        municipality_data=municipality_data,
                        chat_history=chat_history,
                        db=db
                    )
                except Exception as e:
                    logger.error(f"Erro no function calling, fallback para abordagem clássica: {e}")
                    # Continua para o fluxo normal abaixo

            # 1. Verificar se há documentos processados
            has_docs = self.context_service.has_documents(municipality_id)
            
            if not has_docs:
                logger.warning(f"Nenhum documento processado para município {municipality_id}")
                return self.response_builder.build_no_data_response(
                    session_id=session_id,
                    message=f"""## Documentos Não Encontrados

Não encontrei documentos LOA ou LDO processados para **{municipality_name} - {state}**.

### Como proceder:
1. Faça upload dos documentos PDF da LOA e LDO
2. Aguarde o processamento (pode levar alguns minutos)
3. Depois poderá fazer perguntas sobre o orçamento

### Enquanto isso:
Posso consultar apenas dados do Portal da Transparência, sem cruzamento com LOA/LDO.
"""
                )

            # 2. Buscar contexto relevante no ChromaDB
            logger.info("Buscando contexto nos documentos...")
            context_data = await self.context_service.search_all_context(
                query=question,
                municipality_id=municipality_id,
                n_results_per_source=5,
                min_similarity=0.4
            )
            
            loa_context = context_data.get("loa", [])
            ldo_context = context_data.get("ldo", [])
            
            logger.info(f"Contexto LOA: {len(loa_context)} trechos, LDO: {len(ldo_context)} trechos")
            
            # 2.5 Buscar contexto dos packages ingeridos do Portal
            logger.info("Buscando contexto nos packages ingeridos do Portal...")
            portal_ingested_context = await self.get_portal_ingested_context(
                question=question,
                municipality_id=municipality_id,
                n_results=5
            )
            logger.info(f"Contexto Portal Ingerido: {len(portal_ingested_context)} trechos")

            # 3. Identificar packages relevantes do Portal
            logger.info("Identificando packages relevantes do Portal...")
            portal_packages = await self._identify_relevant_packages(
                question, municipality_name
            )
            
            logger.info(f"Packages identificados: {len(portal_packages)}")

            # 4. Buscar dados do portal (se houver packages relevantes)
            portal_data = []
            if portal_packages:
                logger.info("Buscando dados do Portal da Transparência...")
                portal_data = await self._fetch_portal_data(portal_packages[:3])
                logger.info(f"Dados obtidos de {len(portal_data)} packages")

            # 5. Construir prompt completo
            logger.info("Construindo prompt para Gemini...")
            prompt = self.prompt_builder.build_analysis_prompt(
                question=question,
                municipality=municipality_name,
                state=state,
                year=year,
                loa_context=loa_context,
                ldo_context=ldo_context,
                portal_packages=portal_packages,
                portal_data=portal_data,
                portal_ingested_context=portal_ingested_context,
                chat_history=chat_history
            )

            # 6. Chamar Gemini
            logger.info("Chamando Gemini AI...")
            response = await self._call_gemini(prompt)

            # 7. Parse da resposta
            logger.info("Processando resposta do Gemini...")
            gemini_response = await self._parse_gemini_response(
                response, session_id
            )

            # 8. Calcular tempo de processamento
            processing_time = int((time.time() - start_time) * 1000)
            gemini_response.response.metadata.processing_time_ms = processing_time

            logger.info(f"Pergunta processada com sucesso em {processing_time}ms")
            return gemini_response

        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {str(e)}", exc_info=True)
            processing_time = int((time.time() - start_time) * 1000)
            
            return self.response_builder.build_error_response(
                session_id=session_id,
                error_message=f"Erro ao processar sua pergunta: {str(e)}"
            )

    async def _identify_relevant_packages(
        self,
        question: str,
        municipality: str
    ) -> List[str]:
        """
        Identifica packages relevantes do Portal da Transparência.

        Args:
            question: Pergunta do usuário
            municipality: Nome do município

        Returns:
            Lista de package IDs relevantes
        """
        try:
            # Buscar lista de packages (com cache)
            cache_service = await self._get_cache_service()
            packages = await cache_service.get_package_list()
            
            if not packages:
                packages = await self.portal_client.list_packages()
                await cache_service.set_package_list(packages, ttl=3600)

            if not packages or len(packages) == 0:
                logger.warning("Nenhum package disponível no Portal")
                return []

            # Construir prompt para identificação
            prompt = self.prompt_builder.build_package_identification_prompt(
                question=question,
                available_packages=packages,
                municipality=municipality
            )

            # Chamar Gemini para identificar
            response = await self._call_gemini(prompt, temperature=0.3)

            # Parse da resposta
            try:
                response_json = json.loads(response)
                relevant_packages = response_json.get("relevant_packages", [])
                logger.info(f"Gemini identificou {len(relevant_packages)} packages relevantes")
                return relevant_packages[:5]  # Máximo 5
            except json.JSONDecodeError:
                logger.warning("Resposta do Gemini não é JSON válido para identificação de packages")
                # Fallback: usar busca por palavras-chave
                return self._fallback_package_search(question, packages)

        except Exception as e:
            logger.error(f"Erro ao identificar packages: {str(e)}")
            return []

    def _fallback_package_search(self, question: str, packages: List[str]) -> List[str]:
        """
        Busca fallback por palavras-chave quando Gemini falha.

        Args:
            question: Pergunta do usuário
            packages: Lista de packages disponíveis

        Returns:
            Lista de packages relevantes
        """
        keywords = ["despesa", "receita", "contrato", "licitação", "folha", "pagamento"]
        question_lower = question.lower()
        
        relevant = []
        for package in packages:
            package_lower = package.lower()
            if any(keyword in package_lower or keyword in question_lower for keyword in keywords):
                relevant.append(package)
                if len(relevant) >= 5:
                    break
        
        logger.info(f"Fallback search encontrou {len(relevant)} packages")
        return relevant

    async def _fetch_portal_data(
        self,
        package_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Busca dados dos packages do Portal da Transparência.

        Args:
            package_ids: Lista de IDs de packages

        Returns:
            Lista de dados dos packages
        """
        portal_data = []
        
        for package_id in package_ids:
            try:
                package = await self.portal_client.show_package(package_id)
                portal_data.append(package)
            except Exception as e:
                logger.warning(f"Erro ao buscar package {package_id}: {str(e)}")
                continue
        
        return portal_data

    async def _call_gemini(
        self,
        prompt: str,
        temperature: float = 0.7
    ) -> str:
        """
        Chama a API do Gemini.

        Args:
            prompt: Prompt para o Gemini
            temperature: Temperatura (0-1, maior = mais criativo)

        Returns:
            Resposta do Gemini como string
        """
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=4096,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text

        except Exception as e:
            logger.error(f"Erro ao chamar Gemini: {str(e)}")
            raise

    async def _parse_gemini_response(
        self,
        response_text: str,
        session_id: str
    ) -> GeminiResponse:
        """
        Faz parse da resposta do Gemini.

        Args:
            response_text: Texto da resposta do Gemini
            session_id: ID da sessão

        Returns:
            GeminiResponse estruturada
        """
        try:
            # Tentar extrair JSON da resposta
            # Gemini pode retornar JSON entre ```json e ```
            json_text = response_text
            
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_text = response_text[start:end].strip()

            # Parse JSON
            response_data = json.loads(json_text)

            # Validar e construir GeminiResponse
            components = response_data.get("components", [])
            sources = response_data.get("sources", [])
            confidence = response_data.get("confidence", "medium")
            suggestions = response_data.get("suggestions", [])

            # Construir resposta usando ResponseBuilder
            builder = ResponseBuilder()
            
            for component in components:
                comp_type = component.get("type")
                
                if comp_type == "text":
                    builder.add_text(component.get("content", ""))
                elif comp_type == "metric":
                    builder.add_metric(
                        label=component.get("label", ""),
                        value=component.get("value", ""),
                        change=component.get("change"),
                        trend=component.get("trend")
                    )
                elif comp_type == "chart":
                    builder.add_chart(
                        chart_type=component.get("chart_type", "bar"),
                        title=component.get("title", ""),
                        data=component.get("data", {})
                    )
                elif comp_type == "table":
                    builder.add_table(
                        title=component.get("title", ""),
                        columns=component.get("columns", []),
                        rows=component.get("rows", [])
                    )
                elif comp_type == "alert":
                    builder.add_alert(
                        level=component.get("level", "info"),
                        message=component.get("message", "")
                    )
                elif comp_type == "comparison":
                    builder.add_comparison(
                        title=component.get("title", ""),
                        items=component.get("items", [])
                    )
                elif comp_type == "timeline":
                    builder.add_timeline(
                        title=component.get("title", ""),
                        events=component.get("events", [])
                    )

            builder.add_sources(sources)
            builder.add_suggestions(suggestions)
            builder.set_confidence(confidence)

            return builder.build(session_id)

        except json.JSONDecodeError as e:
            logger.error(f"Resposta do Gemini não é JSON válido: {str(e)}")
            logger.debug(f"Resposta raw: {response_text[:500]}")
            
            # Fallback: criar resposta com o texto raw
            builder = ResponseBuilder()
            builder.add_text(response_text)
            builder.add_alert("warning", "Resposta não estruturada")
            builder.set_confidence("low")
            return builder.build(session_id)

        except Exception as e:
            logger.error(f"Erro ao fazer parse da resposta: {str(e)}")
            raise
    
    async def get_portal_ingested_context(
        self,
        question: str,
        municipality_id: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca contexto relevante dos packages ingeridos do Portal.
        
        Args:
            question: Pergunta do usuário
            municipality_id: ID do município
            n_results: Número de resultados por collection
            
        Returns:
            Lista de resultados relevantes
        """
        try:
            # Listar todas as collections do portal
            all_collections = self.vector_db.list_collections()
            # all_collections já é uma lista de strings (nomes)
            portal_collections = [
                c for c in all_collections
                if c.startswith("portal_")
            ]
            
            if not portal_collections:
                logger.info("Nenhuma collection do Portal encontrada")
                return []
            
            logger.info(f"Buscando em {len(portal_collections)} collections do Portal")
            
            # Buscar em cada collection
            results = []
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            
            # Gerar embedding da query
            query_embedding = embedding_service.generate_query_embedding(question)
            
            for collection_name in portal_collections:
                try:
                    # Query na collection
                    collection_obj = self.vector_db.client.get_collection(name=collection_name)
                    
                    # Extrair termos-chave da pergunta para filtros
                    # Buscar por órgãos, números de edital, etc
                    import re
                    where_filters = []
                    
                    # Detectar números de edital (ex: 10365, 10367)
                    edital_numbers = re.findall(r'\b\d{4,5}\b', question)
                    
                    # Detectar nomes de órgãos (SEINF, SMS, SME, IJF, etc)
                    orgaos = re.findall(r'\b(SEINF|SMS|SME|IJF|SEPOG|SECULTFOR|SDHDS|URBFOR|AMC|GMF)\b', question.upper())
                    
                    # Se encontrou termos específicos, fazer busca híbrida
                    # Aumentar n_results para busca semântica pegar mais documentos
                    semantic_n_results = n_results * 3  # Buscar 3x mais para ter diversidade
                    
                    query_results = collection_obj.query(
                        query_embeddings=[query_embedding],
                        n_results=semantic_n_results,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    # Processar resultados e aplicar filtros pós-busca
                    if query_results and query_results.get("documents"):
                        for i, doc in enumerate(query_results["documents"][0]):
                            metadata = query_results["metadatas"][0][i] if query_results.get("metadatas") else {}
                            distance = query_results["distances"][0][i] if query_results.get("distances") else None
                            
                            # Filtro pós-busca: Se há termos específicos, priorizar docs que os contêm
                            bonus_score = 0.0
                            doc_upper = doc.upper()
                            
                            # Bonus para órgãos mencionados
                            for orgao in orgaos:
                                if orgao in doc_upper:
                                    bonus_score += 0.3  # Grande boost
                            
                            # Bonus para números de edital mencionados
                            for edital_num in edital_numbers:
                                if edital_num in doc:
                                    bonus_score += 0.2  # Boost médio
                            
                            # Calcular similaridade ajustada
                            base_similarity = 1 - distance if distance is not None else 0
                            adjusted_similarity = min(1.0, base_similarity + bonus_score)
                            
                            results.append({
                                "text": doc,
                                "source": collection_name,
                                "metadata": metadata,
                                "similarity": adjusted_similarity
                            })
                    
                    logger.debug(f"Encontrados {len(query_results.get('documents', [[]])[0])} docs em {collection_name}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao buscar em {collection_name}: {str(e)}")
                    continue
            
            # Ordenar por similaridade
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            # Retornar top results
            top_results = results[:n_results * 2]  # Pegar mais resultados pois vêm de várias collections
            
            logger.info(f"Contexto do Portal: {len(top_results)} resultados de {len(portal_collections)} collections")
            
            return top_results
            
        except Exception as e:
            logger.error(f"Erro ao buscar contexto do Portal ingerido: {str(e)}")
            return []
    
    async def _process_with_phase3(
        self,
        question: str,
        session_id: str,
        municipality_id: str,
        chat_history: List[Dict[str, str]],
        db: Session,
        message_id: Optional[str] = None
    ) -> GeminiResponse:
        """
        Processa pergunta usando FASE 3:
        1. Query Planning (LLM gera plano otimizado)
        2. Hybrid Search (structured + semantic)
        3. Explainable Response (citações verificáveis)
        """
        start_time = time.time()
        
        try:
            # Inicializar serviços da Fase 3 (se necessário)
            if self.query_planner is None:
                self.query_planner = QueryPlannerService(db)
            
            if self.hybrid_search is None:
                self.hybrid_search = HybridSearchService(db)
            
            # 1. QUERY PLANNING: LLM analisa e gera plano
            logger.info("   [1/3] Query Planning...")
            query_plan = await self.query_planner.plan_query(
                user_question=question,
                municipality_id=municipality_id,
                chat_history=chat_history
            )
            
            logger.info(f"   Strategy: {query_plan.strategy} (confidence: {query_plan.confidence})")
            
            # 2. HYBRID SEARCH: Executar busca
            logger.info("   [2/3] Hybrid Search...")
            search_results = await self.hybrid_search.execute_search(
                query_plan=query_plan,
                user_question=question,
                limit=20,
                message_id=message_id,
                chat_session_id=session_id
            )
            
            logger.info(f"   Found {len(search_results)} results")
            
            # 3. EXPLAINABLE RESPONSE: Construir resposta
            logger.info("   [3/3] Building Explainable Response...")
            explainable_response = await self.explainable_builder.build_response(
                user_question=question,
                query_plan=query_plan,
                search_results=search_results,
                chat_history=chat_history
            )
            
            # Construir GeminiResponse
            elapsed_time = time.time() - start_time
            
            response = GeminiResponse(
                session_id=session_id,
                answer=explainable_response["answer"],
                components=[],  # Não usado na Fase 3
                sources=[],  # Substituído por citations
                processing_time=round(elapsed_time, 2),
                model_used=settings.GEMINI_MODEL,
                context_used={
                    "search_strategy": explainable_response["search_strategy"],
                    "citations_count": explainable_response["citations_count"],
                    "confidence": explainable_response["confidence"],
                    "data_sources": explainable_response["data_sources"],
                    "query_plan_explanation": explainable_response["query_plan_explanation"]
                },
                metadata={
                    "phase": "3",
                    "citations": explainable_response["citations"],
                    "verification_info": explainable_response["verification_info"],
                    "query_plan": query_plan.to_dict()
                }
            )
            
            logger.info(f"✅ Fase 3 completed in {elapsed_time:.2f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in _process_with_phase3: {e}")
            logger.exception(e)
            raise
    
    async def _process_with_function_calling(
        self,
        question: str,
        session_id: str,
        municipality_data: Dict[str, Any],
        chat_history: List[Dict[str, str]],
        db: Session,
        max_iterations: int = 5
    ) -> GeminiResponse:
        """
        Processa pergunta usando Function Calling (Agents)
        
        Loop:
        1. Obtém catálogo de metadados
        2. Envia pergunta + ferramentas + catálogo para Gemini
        3. Se Gemini chama ferramenta → executa
        4. Envia resultado de volta
        5. Repete até Gemini decidir responder
        6. Retorna resposta final
        """
        start_time = time.time()
        
        municipality_id = municipality_data.get("id")
        municipality_name = municipality_data.get("name", "Desconhecido")
        
        try:
            # 1. Obter catálogo de metadados
            logger.info("📊 Obtendo catálogo de metadados...")
            catalog = await self.metadata_catalog.get_full_catalog(municipality_id, db)
            
            # 2. Construir system prompt com awareness do catálogo
            system_prompt = f"""Você é um assistente especializado em análise de dados governamentais.

MUNICÍPIO: {municipality_name} - {municipality_data.get('state')}

📊 DADOS DISPONÍVEIS NO SISTEMA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Portal da Transparência:
- Total de documentos: {catalog['portal_transparency']['total_documents']}
- Órgãos disponíveis: {', '.join(catalog['portal_transparency']['organs'][:10])}
- Modalidades: {', '.join(catalog['portal_transparency']['modalities'])}
- Intervalo de editais: {catalog['portal_transparency']['editals_range']}
- Período: {catalog['portal_transparency']['date_range']}

LOA (Orçamento):
- Documentos: {catalog['loa']['total_documents']}
- Anos disponíveis: {catalog['loa']['years']}

LDO (Diretrizes):
- Documentos: {catalog['ldo']['total_documents']}
- Anos disponíveis: {catalog['ldo']['years']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ FERRAMENTAS DISPONÍVEIS:

{get_tools_summary()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ REGRAS IMPORTANTES:

1. SEMPRE use filtros específicos quando o usuário mencionar:
   - Nome de órgão (ex: SEINF, SME) → use filtro "origem"
   - Número de edital → use filtro "edital"
   - Período/data → use filtros de data
   
2. Se o usuário perguntar sobre um órgão específico:
   - ❌ NÃO retorne dados de outros órgãos
   - ✅ USE o filtro "origem" na ferramenta
   
3. Para análises comparativas ou cruzamentos:
   - Use a ferramenta "cross_reference"
   - Ou chame múltiplas ferramentas sequencialmente

4. Baseie suas decisões no catálogo acima
   - Se não há dados do Portal, não tente buscar lá
   - Se não há LOA/LDO, informe ao usuário

5. Seja preciso e detalhado nas respostas
   - Cite números de editais, valores, datas
   - Mencione as fontes dos dados
"""

            # 3. Preparar ferramentas no formato do Gemini
            gemini_tools = [{
                "function_declarations": get_tools()
            }]
            
            # 4. Criar modelo com ferramentas
            model_with_tools = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                tools=gemini_tools,
                system_instruction=system_prompt
            )
            
            # 5. Iniciar conversação
            chat = model_with_tools.start_chat(history=[])
            
            # Adicionar histórico anterior se houver
            for msg in chat_history[-5:]:  # Últimas 5 mensagens
                role = "user" if msg.get("role") == "user" else "model"
                chat.history.append({
                    "role": role,
                    "parts": [msg.get("content", "")]
                })
            
            # 6. Loop de agent
            current_question = question
            iteration = 0
            tool_calls_made = []
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"🔄 Iteração {iteration}/{max_iterations}")
                
                # Enviar pergunta/continuação
                response = chat.send_message(current_question)
                
                # Verificar se há function call
                if not response.candidates:
                    logger.warning("Gemini não retornou candidatos")
                    break
                
                candidate = response.candidates[0]
                
                # Verificar se há chamada de ferramenta
                if candidate.content.parts[0].function_call:
                    function_call = candidate.content.parts[0].function_call
                    tool_name = function_call.name
                    tool_args = dict(function_call.args)
                    
                    logger.info(f"🛠️ Gemini chamou ferramenta: {tool_name}")
                    logger.info(f"📋 Argumentos: {json.dumps(tool_args, indent=2)}")
                    
                    # Executar ferramenta
                    tool_result = await self.tools_executor.execute_tool(
                        tool_name=tool_name,
                        tool_arguments=tool_args,
                        municipality_id=municipality_id,
                        db=db
                    )
                    
                    tool_calls_made.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result_summary": {
                            "success": tool_result.get("success"),
                            "results_count": tool_result.get("results_count", 0)
                        }
                    })
                    
                    logger.info(f"✅ Ferramenta executada: {tool_result.get('results_count', 0)} resultados")
                    
                    # Enviar resultado de volta para Gemini
                    current_question = [{
                        "function_response": {
                            "name": tool_name,
                            "response": tool_result
                        }
                    }]
                    
                else:
                    # Gemini decidiu responder (não chamou mais ferramentas)
                    logger.info("✅ Gemini finalizou com resposta")
                    final_response = candidate.content.parts[0].text
                    
                    processing_time = time.time() - start_time
                    
                    # Construir resposta estruturada
                    return self.response_builder.build_success_response(
                        session_id=session_id,
                        answer=final_response,
                        sources=[],  # Tools já fornecem fonte
                        components=[],  # Pode ser estendido futuramente
                        processing_time=processing_time,
                        metadata={
                            "used_function_calling": True,
                            "tool_calls": tool_calls_made,
                            "iterations": iteration,
                            "catalog_summary": catalog.get("summary", {})
                        }
                    )
            
            # Se chegou ao limite de iterações
            logger.warning(f"⚠️ Limite de iterações atingido ({max_iterations})")
            return self.response_builder.build_error_response(
                session_id=session_id,
                error="MaxIterationsReached",
                message="O assistente atingiu o limite de iterações. Tente reformular a pergunta."
            )
            
        except Exception as e:
            logger.error(f"❌ Erro no function calling: {str(e)}", exc_info=True)
            processing_time = time.time() - start_time
            
            return self.response_builder.build_error_response(
                session_id=session_id,
                error=str(e),
                message="Erro ao processar pergunta com function calling",
                metadata={"processing_time": processing_time}
            )


# Singleton para reutilização
_orchestrator: Optional[GeminiOrchestrator] = None


def get_gemini_orchestrator() -> GeminiOrchestrator:
    """
    Obtém uma instância singleton do orquestrador.

    Returns:
        Instância do GeminiOrchestrator
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GeminiOrchestrator()
    return _orchestrator

