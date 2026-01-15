"""
Serviço de Construção de Respostas Explicáveis (Fase 3)
Gera respostas com citações verificáveis e rastreáveis
"""

import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai

from app.core.config import settings
from app.services.hybrid_search_service import SearchResult
from app.services.query_planner_service import QueryPlan

logger = logging.getLogger(__name__)


class Citation:
    """Representa uma citação verificável"""
    
    def __init__(
        self,
        parsed_data_id: str,
        raw_file_id: str,
        filename: str,
        row_number: int,
        data: Dict[str, Any],
        text_content: str,
        raw_file_hash: str,
        score: float,
        match_type: str,
        matched_fields: List[str],
        verify_url: str
    ):
        self.parsed_data_id = parsed_data_id
        self.raw_file_id = raw_file_id
        self.filename = filename
        self.row_number = row_number
        self.data = data
        self.text_content = text_content
        self.raw_file_hash = raw_file_hash
        self.score = score
        self.match_type = match_type
        self.matched_fields = matched_fields
        self.verify_url = verify_url
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "parsed_data_id": self.parsed_data_id,
            "raw_file_id": self.raw_file_id,
            "filename": self.filename,
            "row_number": self.row_number,
            "data": self.data,
            "text_content": self.text_content[:500],  # Limitar tamanho
            "raw_file_hash": self.raw_file_hash,
            "score": round(self.score, 3),
            "match_type": self.match_type,
            "matched_fields": self.matched_fields,
            "verify_url": self.verify_url
        }


class ExplainableResponseBuilder:
    """
    Constrói respostas explicáveis com citações verificáveis
    """
    
    def __init__(self):
        # Configurar Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def build_response(
        self,
        user_question: str,
        query_plan: QueryPlan,
        search_results: List[SearchResult],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Constrói resposta explicável
        
        Args:
            user_question: Pergunta do usuário
            query_plan: Plano de query executado
            search_results: Resultados da busca
            chat_history: Histórico do chat
        
        Returns:
            Dict com resposta + citações + explicação
        """
        try:
            logger.info(f"📝 Building explainable response for: '{user_question}'")
            
            if not search_results:
                return self._build_no_results_response(user_question)
            
            # 1. Criar citações
            citations = self._create_citations(search_results)
            
            logger.info(f"   Created {len(citations)} citations")
            
            # 2. Preparar contexto para LLM
            context = self._format_context_for_llm(
                search_results=search_results,
                query_plan=query_plan
            )
            
            # 3. Gerar resposta com LLM
            answer = await self._generate_answer_with_llm(
                user_question=user_question,
                context=context,
                query_plan=query_plan,
                chat_history=chat_history
            )
            
            # 4. Construir resposta final
            response = {
                "answer": answer,
                "citations": [c.to_dict() for c in citations],
                "citations_count": len(citations),
                "search_strategy": query_plan.strategy,
                "query_plan_explanation": query_plan.explanation,
                "confidence": self._calculate_overall_confidence(
                    search_results,
                    query_plan
                ),
                "data_sources": self._summarize_sources(search_results),
                "verification_info": {
                    "message": "Todos os dados são rastreáveis e verificáveis",
                    "audit_endpoint": "/api/audit/lineage/message/{message_id}",
                    "integrity_check": "SHA256 hash disponível para cada fonte"
                }
            }
            
            logger.info(f"✅ Response built with {len(citations)} citations")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error building response: {e}")
            logger.exception(e)
            return self._build_error_response(user_question, str(e))
    
    def _create_citations(
        self,
        search_results: List[SearchResult]
    ) -> List[Citation]:
        """Cria citações a partir dos resultados"""
        citations = []
        
        for result in search_results:
            # Gerar URL de verificação
            verify_url = f"/api/audit/raw-file/{result.raw_file.id}/verify-integrity"
            
            citation = Citation(
                parsed_data_id=result.parsed_data.id,
                raw_file_id=result.raw_file.id,
                filename=result.raw_file.filename,
                row_number=result.parsed_data.row_number,
                data=result.parsed_data.data,
                text_content=result.parsed_data.text_content,
                raw_file_hash=result.raw_file.sha256_hash,
                score=result.score,
                match_type=result.match_type,
                matched_fields=result.matched_fields,
                verify_url=verify_url
            )
            
            citations.append(citation)
        
        return citations
    
    def _format_context_for_llm(
        self,
        search_results: List[SearchResult],
        query_plan: QueryPlan
    ) -> str:
        """Formata contexto para o LLM"""
        context_lines = [
            "DADOS ENCONTRADOS:",
            ""
        ]
        
        for i, result in enumerate(search_results[:10], 1):  # Top 10
            context_lines.append(f"[{i}] Fonte: {result.raw_file.filename} (linha {result.parsed_data.row_number})")
            context_lines.append(f"    Score: {result.score:.3f} | Match: {result.match_type}")
            
            if result.matched_fields:
                context_lines.append(f"    Campos matched: {', '.join(result.matched_fields)}")
            
            context_lines.append(f"    Dados:")
            
            # Mostrar dados estruturados
            for key, value in result.parsed_data.data.items():
                if value:
                    context_lines.append(f"      - {key}: {value}")
            
            context_lines.append("")
        
        if len(search_results) > 10:
            context_lines.append(f"... e mais {len(search_results) - 10} resultados")
        
        return "\n".join(context_lines)
    
    async def _generate_answer_with_llm(
        self,
        user_question: str,
        context: str,
        query_plan: QueryPlan,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Gera resposta usando LLM"""
        
        # Formatar histórico
        history_text = ""
        if chat_history:
            history_text = "\n\nHISTÓRICO DA CONVERSA:\n"
            for msg in chat_history[-3:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:300]
                history_text += f"- {role}: {content}\n"
        
        prompt = f"""Você é um assistente especializado em análise de dados governamentais.

PERGUNTA DO USUÁRIO:
"{user_question}"
{history_text}
PLANO DE BUSCA EXECUTADO:
{query_plan.explanation}

{context}

INSTRUÇÕES:
1. Responda à pergunta usando APENAS os dados fornecidos acima
2. Cite as fontes (ex: "Segundo o arquivo X, linha Y...")
3. Se os dados não responderem completamente, diga o que está faltando
4. Seja preciso e objetivo
5. Use formatação markdown para melhor legibilidade
6. NUNCA invente informações

IMPORTANTE:
- Todos os dados são rastreáveis e verificáveis
- Você está respondendo para jornalistas/auditores
- A precisão é CRÍTICA

Responda:"""
        
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.2)
        )
        
        return response.text
    
    def _calculate_overall_confidence(
        self,
        search_results: List[SearchResult],
        query_plan: QueryPlan
    ) -> float:
        """Calcula confiança geral da resposta"""
        if not search_results:
            return 0.0
        
        # Média dos scores dos top 5 resultados
        top_results = search_results[:5]
        avg_score = sum(r.score for r in top_results) / len(top_results)
        
        # Combinar com confiança do query plan
        overall_confidence = (avg_score + query_plan.confidence) / 2
        
        return round(overall_confidence, 3)
    
    def _summarize_sources(
        self,
        search_results: List[SearchResult]
    ) -> Dict[str, Any]:
        """Sumariza fontes dos dados"""
        files = {}
        
        for result in search_results:
            filename = result.raw_file.filename
            
            if filename not in files:
                files[filename] = {
                    "filename": filename,
                    "raw_file_id": result.raw_file.id,
                    "sha256_hash": result.raw_file.sha256_hash,
                    "results_count": 0
                }
            
            files[filename]["results_count"] += 1
        
        return {
            "total_files": len(files),
            "files": list(files.values())
        }
    
    def _build_no_results_response(
        self,
        user_question: str
    ) -> Dict[str, Any]:
        """Resposta quando não há resultados"""
        return {
            "answer": f"""Desculpe, não encontrei informações específicas sobre: "{user_question}".

Isso pode significar:
1. Os dados ainda não foram processados
2. A informação não está disponível nos arquivos do portal da transparência
3. A pergunta precisa ser reformulada

Sugestões:
- Verifique se os packages foram processados
- Tente usar termos diferentes
- Consulte os schemas disponíveis: /api/schemas/""",
            "citations": [],
            "citations_count": 0,
            "search_strategy": "no_results",
            "confidence": 0.0,
            "data_sources": {"total_files": 0, "files": []},
            "verification_info": {
                "message": "Nenhum dado encontrado para verificar"
            }
        }
    
    def _build_error_response(
        self,
        user_question: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Resposta quando ocorre erro"""
        return {
            "answer": f"Ocorreu um erro ao processar sua pergunta. Por favor, tente novamente.",
            "citations": [],
            "citations_count": 0,
            "search_strategy": "error",
            "confidence": 0.0,
            "error": error_message,
            "data_sources": {"total_files": 0, "files": []},
            "verification_info": {
                "message": "Erro no processamento"
            }
        }

