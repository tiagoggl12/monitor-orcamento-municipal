"""
Construtor de respostas estruturadas.

Este módulo facilita a criação de respostas com múltiplos componentes
visuais (texto, gráficos, tabelas, métricas, etc).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from app.schemas.component_schemas import (
    TextComponent,
    ChartComponent,
    TableComponent,
    AlertComponent,
    MetricComponent,
    ComparisonComponent,
    TimelineComponent,
)
from app.schemas.request_schemas import GeminiResponse, ResponseData, ResponseMetadata


class ResponseBuilder:
    """Builder para construir respostas estruturadas."""

    def __init__(self):
        """Inicializa o builder."""
        self.components: List[Any] = []
        self.sources: List[str] = []
        self.suggestions: List[str] = []
        self.confidence: str = "high"
        self.processing_time_ms: int = 0

    def add_text(self, content: str) -> "ResponseBuilder":
        """
        Adiciona um componente de texto (Markdown).

        Args:
            content: Conteúdo em Markdown

        Returns:
            Self para chaining
        """
        self.components.append(
            TextComponent(
                type="text",
                content=content
            )
        )
        return self

    def add_metric(
        self,
        label: str,
        value: str,
        change: Optional[str] = None,
        trend: Optional[str] = None
    ) -> "ResponseBuilder":
        """
        Adiciona uma métrica.

        Args:
            label: Rótulo da métrica
            value: Valor formatado
            change: Mudança percentual (ex: "+15%")
            trend: Tendência ("up", "down", "neutral")

        Returns:
            Self para chaining
        """
        self.components.append(
            MetricComponent(
                type="metric",
                label=label,
                value=value,
                change=change,
                trend=trend
            )
        )
        return self

    def add_chart(
        self,
        chart_type: str,
        title: str,
        data: Dict[str, Any]
    ) -> "ResponseBuilder":
        """
        Adiciona um gráfico.

        Args:
            chart_type: Tipo do gráfico ("bar", "line", "pie", "area")
            title: Título do gráfico
            data: Dados do gráfico (labels e datasets)

        Returns:
            Self para chaining
        """
        self.components.append(
            ChartComponent(
                type="chart",
                chart_type=chart_type,
                title=title,
                data=data
            )
        )
        return self

    def add_table(
        self,
        title: str,
        columns: List[str],
        rows: List[List[str]]
    ) -> "ResponseBuilder":
        """
        Adiciona uma tabela.

        Args:
            title: Título da tabela
            columns: Nomes das colunas
            rows: Linhas de dados

        Returns:
            Self para chaining
        """
        self.components.append(
            TableComponent(
                type="table",
                title=title,
                columns=columns,
                rows=rows
            )
        )
        return self

    def add_alert(
        self,
        level: str,
        message: str
    ) -> "ResponseBuilder":
        """
        Adiciona um alerta.

        Args:
            level: Nível do alerta ("info", "warning", "error", "success")
            message: Mensagem do alerta

        Returns:
            Self para chaining
        """
        self.components.append(
            AlertComponent(
                type="alert",
                level=level,
                message=message
            )
        )
        return self

    def add_comparison(
        self,
        title: str,
        items: List[Dict[str, Any]]
    ) -> "ResponseBuilder":
        """
        Adiciona uma comparação.

        Args:
            title: Título da comparação
            items: Itens para comparar (label, value, percentage)

        Returns:
            Self para chaining
        """
        self.components.append(
            ComparisonComponent(
                type="comparison",
                title=title,
                items=items
            )
        )
        return self

    def add_timeline(
        self,
        title: str,
        events: List[Dict[str, str]]
    ) -> "ResponseBuilder":
        """
        Adiciona uma linha do tempo.

        Args:
            title: Título da timeline
            events: Eventos (date, title, description)

        Returns:
            Self para chaining
        """
        self.components.append(
            TimelineComponent(
                type="timeline",
                title=title,
                events=events
            )
        )
        return self

    def add_source(self, source: str) -> "ResponseBuilder":
        """
        Adiciona uma fonte de dados.

        Args:
            source: Descrição da fonte

        Returns:
            Self para chaining
        """
        if source not in self.sources:
            self.sources.append(source)
        return self

    def add_sources(self, sources: List[str]) -> "ResponseBuilder":
        """
        Adiciona múltiplas fontes de dados.

        Args:
            sources: Lista de fontes

        Returns:
            Self para chaining
        """
        for source in sources:
            self.add_source(source)
        return self

    def add_suggestion(self, suggestion: str) -> "ResponseBuilder":
        """
        Adiciona uma sugestão de pergunta relacionada.

        Args:
            suggestion: Sugestão de pergunta

        Returns:
            Self para chaining
        """
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
        return self

    def add_suggestions(self, suggestions: List[str]) -> "ResponseBuilder":
        """
        Adiciona múltiplas sugestões.

        Args:
            suggestions: Lista de sugestões

        Returns:
            Self para chaining
        """
        for suggestion in suggestions:
            self.add_suggestion(suggestion)
        return self

    def set_confidence(self, confidence: str) -> "ResponseBuilder":
        """
        Define o nível de confiança da resposta.

        Args:
            confidence: Nível de confiança ("high", "medium", "low")

        Returns:
            Self para chaining
        """
        self.confidence = confidence
        return self

    def set_processing_time(self, time_ms: int) -> "ResponseBuilder":
        """
        Define o tempo de processamento.

        Args:
            time_ms: Tempo em milissegundos

        Returns:
            Self para chaining
        """
        self.processing_time_ms = time_ms
        return self

    def build(self, session_id: str) -> GeminiResponse:
        """
        Constrói a resposta final.

        Args:
            session_id: ID da sessão de chat

        Returns:
            GeminiResponse completa
        """
        return GeminiResponse(
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            response=ResponseData(
                components=self.components,
                metadata=ResponseMetadata(
                    sources=self.sources,
                    confidence=self.confidence,
                    processing_time_ms=self.processing_time_ms,
                    suggestions=self.suggestions
                )
            )
        )

    def build_error_response(
        self,
        session_id: str,
        error_message: str,
        error_type: str = "error"
    ) -> GeminiResponse:
        """
        Constrói uma resposta de erro.

        Args:
            session_id: ID da sessão
            error_message: Mensagem de erro
            error_type: Tipo do erro ("error", "warning")

        Returns:
            GeminiResponse com erro
        """
        self.components = []
        self.add_text(f"## Erro ao processar sua pergunta\n\n{error_message}")
        self.add_alert(error_type, error_message)
        self.set_confidence("low")
        return self.build(session_id)

    def build_no_data_response(
        self,
        session_id: str,
        message: Optional[str] = None
    ) -> GeminiResponse:
        """
        Constrói uma resposta quando não há dados suficientes.

        Args:
            session_id: ID da sessão
            message: Mensagem customizada

        Returns:
            GeminiResponse indicando falta de dados
        """
        self.components = []
        
        default_message = """## Dados Insuficientes

Não encontrei dados suficientes para responder sua pergunta com precisão.

### Possíveis motivos:
- Os documentos LOA/LDO ainda não foram carregados
- O Portal da Transparência não possui dados para este período
- A pergunta pode estar relacionada a informações não disponíveis

### Sugestões:
1. Verifique se os documentos LOA e LDO foram carregados
2. Tente fazer uma pergunta mais específica
3. Consulte o administrador do sistema
"""
        
        self.add_text(message or default_message)
        self.add_alert("warning", "Dados insuficientes para responder")
        self.set_confidence("low")
        
        self.add_suggestions([
            "Quais documentos estão disponíveis?",
            "Como carregar os documentos LOA e LDO?",
            "Que tipo de perguntas posso fazer?"
        ])
        
        return self.build(session_id)

    def clear(self) -> "ResponseBuilder":
        """
        Limpa todos os componentes e reinicia o builder.

        Returns:
            Self para chaining
        """
        self.components = []
        self.sources = []
        self.suggestions = []
        self.confidence = "high"
        self.processing_time_ms = 0
        return self


# Função auxiliar para criar instância
def get_response_builder() -> ResponseBuilder:
    """Retorna uma nova instância do ResponseBuilder."""
    return ResponseBuilder()

