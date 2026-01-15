"""
Serviço de Planejamento de Queries (Fase 3)
LLM analisa schemas e gera plano de busca otimizado
"""

import logging
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.core.config import settings
from app.services.schema_discovery_service import SchemaDiscoveryService
from app.services.semantic_field_mapper import SemanticFieldMapper, FieldMapping
from app.models.file_schema import FileSchema

logger = logging.getLogger(__name__)


class QueryPlan:
    """Representa um plano de query gerado pelo LLM"""
    
    def __init__(
        self,
        strategy: str,
        relevant_files: List[str],
        field_mappings: List[Dict[str, Any]],
        semantic_query: str,
        filters: List[Dict[str, Any]],
        explanation: str,
        confidence: float
    ):
        self.strategy = strategy  # "structured" | "semantic" | "hybrid"
        self.relevant_files = relevant_files
        self.field_mappings = field_mappings
        self.semantic_query = semantic_query
        self.filters = filters
        self.explanation = explanation
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "relevant_files": self.relevant_files,
            "field_mappings": self.field_mappings,
            "semantic_query": self.semantic_query,
            "filters": self.filters,
            "explanation": self.explanation,
            "confidence": self.confidence
        }


class QueryPlannerService:
    """
    Planeja queries usando LLM com awareness completo dos schemas
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.schema_service = SchemaDiscoveryService(db)
        self.field_mapper = SemanticFieldMapper(db)
        
        # Configurar Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def plan_query(
        self,
        user_question: str,
        municipality_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> QueryPlan:
        """
        Gera plano de query usando LLM
        
        Args:
            user_question: Pergunta do usuário
            municipality_id: ID do município (para filtrar schemas)
            chat_history: Histórico do chat (para contexto)
        
        Returns:
            QueryPlan gerado pelo LLM
        """
        try:
            logger.info(f"🤔 Planning query: '{user_question}'")
            
            # 1. Obter schemas disponíveis
            available_schemas = self._get_relevant_schemas(municipality_id)
            
            if not available_schemas:
                logger.warning("No schemas available for planning")
                return self._fallback_semantic_plan(user_question)
            
            logger.info(f"   Schemas disponíveis: {len(available_schemas)}")
            
            # 2. Obter mapeamentos iniciais (pre-analysis)
            initial_mappings = self.field_mapper.map_user_query_to_fields(
                user_question,
                file_schemas=available_schemas
            )
            
            logger.info(f"   Mapeamentos iniciais: {len(initial_mappings)}")
            
            # 3. Formatar schemas para LLM
            schemas_description = self._format_schemas_for_llm(available_schemas)
            
            # 4. Gerar prompt para LLM
            prompt = self._build_planning_prompt(
                user_question=user_question,
                schemas_description=schemas_description,
                initial_mappings=initial_mappings,
                chat_history=chat_history
            )
            
            # 5. Chamar LLM
            logger.debug("   Chamando Gemini para planejamento...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
            
            # 6. Parsear resposta
            plan_data = json.loads(response.text)
            
            query_plan = QueryPlan(
                strategy=plan_data.get("strategy", "hybrid"),
                relevant_files=plan_data.get("relevant_files", []),
                field_mappings=plan_data.get("field_mappings", []),
                semantic_query=plan_data.get("semantic_query", user_question),
                filters=plan_data.get("filters", []),
                explanation=plan_data.get("explanation", ""),
                confidence=float(plan_data.get("confidence", 0.8))
            )
            
            logger.info(f"✅ Query plan generated: {query_plan.strategy} (confidence: {query_plan.confidence})")
            logger.debug(f"   Explanation: {query_plan.explanation}")
            
            return query_plan
            
        except Exception as e:
            logger.error(f"❌ Error planning query: {e}")
            logger.exception(e)
            return self._fallback_semantic_plan(user_question)
    
    def _get_relevant_schemas(
        self,
        municipality_id: Optional[str] = None
    ) -> List[FileSchema]:
        """Obtém schemas relevantes"""
        # Por enquanto, retornar todos os schemas ativos
        # TODO: Filtrar por municipality_id quando disponível
        return self.schema_service.get_all_active_schemas()
    
    def _format_schemas_for_llm(
        self,
        schemas: List[FileSchema]
    ) -> str:
        """Formata schemas de forma legível para LLM"""
        formatted = []
        
        for schema in schemas[:10]:  # Limitar a 10 schemas para não ultrapassar token limit
            formatted.append(schema.format_for_llm())
            formatted.append("")
        
        if len(schemas) > 10:
            formatted.append(f"... e mais {len(schemas) - 10} arquivos disponíveis")
        
        return "\n".join(formatted)
    
    def _build_planning_prompt(
        self,
        user_question: str,
        schemas_description: str,
        initial_mappings: List[FieldMapping],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Constrói prompt para o LLM planejar a query"""
        
        # Formatar mapeamentos iniciais
        mappings_text = ""
        if initial_mappings:
            mappings_text = "\n\nMAPEAMENTOS DETECTADOS:\n"
            for m in initial_mappings[:5]:
                mappings_text += f"- '{m.query_text}' → Coluna '{m.column_name}' ({m.filename}) [confiança: {m.confidence:.2f}]\n"
        
        # Formatar histórico
        history_text = ""
        if chat_history:
            history_text = "\n\nHISTÓRICO DA CONVERSA:\n"
            for msg in chat_history[-3:]:  # Últimas 3 mensagens
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]  # Limitar tamanho
                history_text += f"- {role}: {content}\n"
        
        prompt = f"""Você é um assistente especializado em análise de dados governamentais.

Sua tarefa é PLANEJAR uma busca otimizada para responder à pergunta do usuário.

PERGUNTA DO USUÁRIO:
"{user_question}"
{history_text}
ARQUIVOS DISPONÍVEIS E SUAS ESTRUTURAS:

{schemas_description}
{mappings_text}

INSTRUÇÕES:
1. Analise a pergunta e os schemas disponíveis
2. Identifique quais arquivos são relevantes
3. Determine a melhor estratégia de busca:
   - "structured": Busca estruturada (SQL) se há mapeamentos claros de campos
   - "semantic": Busca semântica (embeddings) se é uma pergunta aberta
   - "hybrid": Ambas (recomendado quando há dúvida)

4. Para cada termo da pergunta, identifique:
   - Qual arquivo contém a informação
   - Qual coluna usar (nome EXATO da coluna)
   - Qual valor buscar
   - Qual operador (equals, contains, greater_than, etc)

5. Gere uma query semântica otimizada (para busca por embeddings)

IMPORTANTE:
- Use os nomes EXATOS das colunas (ex: "EDITAL N°", não "edital")
- O usuário pode usar nomes informais, mas você deve mapear para os nomes reais
- Priorize busca structured quando possível (mais precisa)
- Use hybrid para ter certeza de não perder informações

RETORNE APENAS JSON (sem markdown, sem ```):
{{
    "strategy": "hybrid",
    "relevant_files": ["nome_arquivo_1.csv", "nome_arquivo_2.csv"],
    "field_mappings": [
        {{
            "user_term": "edital",
            "file_name": "01_dados_gerais.csv",
            "column_name": "EDITAL N°",
            "value": 10367,
            "operator": "equals",
            "confidence": 0.95
        }}
    ],
    "filters": [
        {{
            "file_name": "01_dados_gerais.csv",
            "column_name": "ORIGEM",
            "operator": "equals",
            "value": "SEINF"
        }}
    ],
    "semantic_query": "informações sobre licitação edital 10367 SEINF",
    "explanation": "Explicação breve do plano de busca",
    "confidence": 0.9
}}
"""
        
        return prompt
    
    def _fallback_semantic_plan(self, user_question: str) -> QueryPlan:
        """Plano fallback (apenas busca semântica)"""
        logger.warning("Using fallback semantic plan")
        
        return QueryPlan(
            strategy="semantic",
            relevant_files=[],
            field_mappings=[],
            semantic_query=user_question,
            filters=[],
            explanation="Fallback: usando apenas busca semântica (schemas não disponíveis)",
            confidence=0.5
        )

