"""
Schemas Pydantic para Requests (entrada da API)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Dict
from datetime import datetime


# ====================================
# Municipality Schemas
# ====================================

class MunicipalityCreate(BaseModel):
    """Schema para criar município"""
    name: str = Field(..., min_length=2, max_length=100, description="Nome do município")
    state: str = Field(..., min_length=2, max_length=2, description="Sigla do estado (UF)")
    year: int = Field(..., ge=2000, le=2100, description="Ano de referência")
    
    @validator('state')
    def state_uppercase(cls, v):
        return v.upper()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Fortaleza",
                "state": "CE",
                "year": 2023
            }
        }
    }


class MunicipalityResponse(BaseModel):
    """Schema para resposta de município"""
    id: str
    name: str
    state: str
    year: int
    created_at: str
    
    model_config = {
        "from_attributes": True
    }


# ====================================
# Document Schemas
# ====================================

class DocumentStatusResponse(BaseModel):
    """Status de processamento de um documento"""
    id: str
    type: str  # 'LOA' ou 'LDO'
    filename: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    upload_date: str
    processed_date: Optional[str] = None
    total_chunks: int = 0
    processed_batches: int = 0
    total_batches: int = 0
    error_message: Optional[str] = None
    
    model_config = {
        "from_attributes": True
    }


class MunicipalityDocumentsStatus(BaseModel):
    """Status dos documentos de um município"""
    municipality: MunicipalityResponse
    loa_processed: bool
    ldo_processed: bool
    loa_document: Optional[DocumentStatusResponse] = None
    ldo_document: Optional[DocumentStatusResponse] = None
    ready_for_chat: bool  # True se ambos LOA e LDO estão processados


# ====================================
# Chat Schemas
# ====================================

class OutputPreferences(BaseModel):
    """Preferências de output do usuário"""
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True
    max_length: str = "detailed"  # 'brief', 'detailed', 'comprehensive'


class ChatRequest(BaseModel):
    """Request para o chat"""
    message: str = Field(..., min_length=3, max_length=5000, description="Pergunta do usuário")
    session_id: Optional[str] = None  # Se None, cria nova sessão
    municipality_id: Optional[str] = None  # Pode ser omitido se session_id já existe
    output_preferences: Optional[OutputPreferences] = OutputPreferences()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Compare o orçamento de saúde previsto vs executado",
                "session_id": "uuid-v4-here",
                "municipality_id": "uuid-v4-here",
                "output_preferences": {
                    "include_charts": True,
                    "include_tables": True,
                    "include_summary": True,
                    "max_length": "detailed"
                }
            }
        }
    }


class ChatMessageResponse(BaseModel):
    """Resposta de uma mensagem do chat"""
    id: str
    session_id: str
    role: str  # 'user' ou 'assistant'
    content: str
    structured_response: Optional[dict] = None
    timestamp: str
    processing_time_ms: Optional[int] = None


class ChatHistoryResponse(BaseModel):
    """Histórico de mensagens de uma sessão"""
    session_id: str
    messages: list[ChatMessageResponse]
    total_messages: int


# ====================================
# Upload Schemas
# ====================================

class UploadResponse(BaseModel):
    """Resposta do upload de documento"""
    document_id: str
    filename: str
    file_size_bytes: int
    status: str
    message: str
    estimated_processing_time_minutes: Optional[int] = None
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "uuid-v4-here",
                "filename": "LOA_2023.pdf",
                "file_size_bytes": 2500000,
                "status": "pending",
                "message": "Documento enviado com sucesso e será processado em breve",
                "estimated_processing_time_minutes": 5
            }
        }
    }


# ====================================
# Portal Schemas
# ====================================

class PortalPackageInfo(BaseModel):
    """Informações resumidas de um package do portal"""
    id: str
    name: str
    title: str
    num_resources: int
    organization: Optional[str] = None


class PortalPackagesResponse(BaseModel):
    """Lista de packages do portal"""
    total: int
    packages: list[PortalPackageInfo]
    cached: bool = False


# ====================================
# Health Check Schemas
# ====================================

class HealthCheckResponse(BaseModel):
    """Resposta do health check"""
    status: str = "ok"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    version: str
    services: dict = {}
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "timestamp": "2026-01-05T10:30:00Z",
                "version": "1.0.0",
                "services": {
                    "database": "connected",
                    "chromadb": "connected",
                    "redis": "connected",
                    "gemini_api": "configured"
                }
            }
        }
    }


# ====================================
# Error Schemas
# ====================================

class ErrorResponse(BaseModel):
    """Schema de erro padronizado"""
    error: str
    message: str
    details: Optional[dict] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "message": "Dados inválidos fornecidos",
                "details": {"field": "year", "issue": "deve estar entre 2000 e 2100"},
                "timestamp": "2026-01-05T10:30:00Z"
            }
        }
    }


# ====================================
# Chat Schemas
# ====================================

class ChatSessionCreate(BaseModel):
    """Schema para criar sessão de chat"""
    municipality_id: str = Field(..., description="ID do município (UUID)")
    title: Optional[str] = Field(None, max_length=200, description="Título da sessão")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "municipality_id": "ae72ac06-c5ea-4c4f-a3b5-d418c6150005",
                "title": "Análise Orçamento 2023"
            }
        }
    }


class ChatSessionResponse(BaseModel):
    """Schema para resposta de sessão de chat"""
    id: str  # UUID
    municipality_id: str  # UUID
    title: str
    created_at: datetime
    message_count: int = 0
    
    model_config = {
        "from_attributes": True
    }


class MessageResponse(BaseModel):
    """Schema para resposta de mensagem"""
    id: str  # UUID
    session_id: str  # UUID
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime
    
    model_config = {
        "from_attributes": True
    }


class ChatRequest(BaseModel):
    """Schema para enviar mensagem no chat"""
    question: str = Field(..., min_length=3, max_length=2000, description="Pergunta do usuário")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Qual foi o orçamento total previsto para saúde em 2023?"
            }
        }
    }


class ResponseMetadata(BaseModel):
    """Metadados da resposta"""
    sources: List[str] = Field(default_factory=list, description="Fontes de dados utilizadas")
    confidence: str = Field("medium", description="Nível de confiança (high, medium, low)")
    processing_time_ms: int = Field(0, description="Tempo de processamento em ms")
    suggestions: List[str] = Field(default_factory=list, description="Sugestões de perguntas relacionadas")


class ResponseData(BaseModel):
    """Dados da resposta estruturada"""
    components: List[Any] = Field(default_factory=list, description="Componentes visuais")
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)


class GeminiResponse(BaseModel):
    """Resposta completa do Gemini"""
    session_id: str
    timestamp: str
    response: ResponseData
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "1",
                "timestamp": "2026-01-05T10:30:00Z",
                "response": {
                    "components": [
                        {
                            "type": "text",
                            "content": "## Orçamento Total 2023\\n\\nO orçamento total previsto foi de R$ 10,5 bilhões."
                        },
                        {
                            "type": "metric",
                            "label": "Orçamento Total",
                            "value": "R$ 10,5 bi"
                        }
                    ],
                    "metadata": {
                        "sources": ["LOA 2023 - Art. 1º"],
                        "confidence": "high",
                        "processing_time_ms": 1500,
                        "suggestions": ["Como está distribuído por área?"]
                    }
                }
            }
        }
    }

