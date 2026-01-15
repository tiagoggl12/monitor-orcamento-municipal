"""
Schemas Pydantic para os componentes de resposta do Gemini
Esses schemas definem a estrutura JSON que o Gemini deve retornar
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Union, Any
from datetime import datetime


# ====================================
# Base Component
# ====================================

class BaseComponent(BaseModel):
    """Base para todos os componentes"""
    type: str


# ====================================
# Text Component
# ====================================

class TextComponent(BaseComponent):
    """Componente de texto (Markdown ou plain)"""
    type: Literal["text"]
    content: str
    format: Literal["markdown", "plain"] = "markdown"


# ====================================
# Chart Component
# ====================================

class ChartDataset(BaseModel):
    """Dataset para gráficos"""
    label: str
    data: List[float]
    backgroundColor: Optional[List[str]] = None
    borderColor: Optional[str] = None


class ChartData(BaseModel):
    """Dados do gráfico"""
    labels: List[str]
    datasets: List[ChartDataset]


class ChartComponent(BaseComponent):
    """Componente de gráfico"""
    type: Literal["chart"]
    chart_type: Literal["bar", "line", "pie", "area", "doughnut"]
    title: str
    data: ChartData
    config: Optional[dict] = None  # Configurações extras (cores, etc)


# ====================================
# Table Component
# ====================================

class TableComponent(BaseComponent):
    """Componente de tabela"""
    type: Literal["table"]
    title: str
    columns: List[str]
    rows: List[List[str]]  # Lista de listas (cada linha)
    highlight_rows: Optional[List[int]] = None  # Índices de linhas para destacar


# ====================================
# Alert Component
# ====================================

class AlertComponent(BaseComponent):
    """Componente de alerta/notificação"""
    type: Literal["alert"]
    level: Literal["info", "warning", "error", "success"]
    message: str
    title: Optional[str] = None


# ====================================
# Metric Component
# ====================================

class MetricComponent(BaseComponent):
    """Componente de métrica individual"""
    type: Literal["metric"]
    label: str
    value: str
    change: Optional[str] = None  # Ex: "+12.5%", "-5.2%"
    trend: Optional[Literal["up", "down", "neutral"]] = None
    description: Optional[str] = None


# ====================================
# Comparison Component
# ====================================

class ComparisonItem(BaseModel):
    """Item de comparação"""
    label: str
    value: str
    percentage: Optional[float] = None


class ComparisonComponent(BaseComponent):
    """Componente de comparação lado a lado"""
    type: Literal["comparison"]
    title: str
    items: List[ComparisonItem]


# ====================================
# Timeline Component (futuro)
# ====================================

class TimelineEvent(BaseModel):
    """Evento na linha do tempo"""
    date: str
    title: str
    description: str
    type: Optional[str] = None  # 'milestone', 'event', etc


class TimelineComponent(BaseComponent):
    """Componente de linha do tempo"""
    type: Literal["timeline"]
    title: str
    events: List[TimelineEvent]


# ====================================
# Union de todos os componentes
# ====================================

ResponseComponent = Union[
    TextComponent,
    ChartComponent,
    TableComponent,
    AlertComponent,
    MetricComponent,
    ComparisonComponent,
    TimelineComponent
]


# ====================================
# Response Metadata
# ====================================

class ResponseMetadata(BaseModel):
    """Metadados da resposta"""
    sources: List[str] = Field(description="Fontes dos dados (LOA, LDO, packages)")
    confidence: Literal["high", "medium", "low"] = "high"
    processing_time_ms: int = 0


# ====================================
# Response Data
# ====================================

class ResponseData(BaseModel):
    """Estrutura da resposta do Gemini"""
    components: List[ResponseComponent] = Field(discriminator="type")
    metadata: ResponseMetadata


# ====================================
# Gemini Response
# ====================================

class GeminiResponse(BaseModel):
    """Resposta completa do sistema"""
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    response: ResponseData
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "uuid-v4-here",
                "timestamp": "2026-01-05T10:30:00Z",
                "response": {
                    "components": [
                        {
                            "type": "text",
                            "content": "## Análise de Gastos com Saúde",
                            "format": "markdown"
                        },
                        {
                            "type": "metric",
                            "label": "Total Previsto",
                            "value": "R$ 450,5 milhões",
                            "trend": "neutral"
                        },
                        {
                            "type": "chart",
                            "chart_type": "bar",
                            "title": "Previsto vs Executado",
                            "data": {
                                "labels": ["Previsto", "Executado"],
                                "datasets": [{
                                    "label": "R$ (milhões)",
                                    "data": [450.5, 398.2]
                                }]
                            }
                        }
                    ],
                    "metadata": {
                        "sources": ["LOA 2023 - Fortaleza", "Portal: dados-saude"],
                        "confidence": "high",
                        "processing_time_ms": 2340
                    }
                }
            }
        }
    }

