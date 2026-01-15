"""
Pydantic Schemas para validação de dados
"""

from app.schemas.component_schemas import (
    TextComponent,
    ChartComponent,
    TableComponent,
    AlertComponent,
    MetricComponent,
    ComparisonComponent,
    TimelineComponent,
    ResponseComponent,
    ResponseMetadata,
    ResponseData,
    GeminiResponse
)

from app.schemas.request_schemas import (
    MunicipalityCreate,
    MunicipalityResponse,
    DocumentStatusResponse,
    MunicipalityDocumentsStatus,
    ChatRequest,
    OutputPreferences,
    ChatMessageResponse,
    ChatHistoryResponse,
    UploadResponse,
    PortalPackageInfo,
    PortalPackagesResponse,
    HealthCheckResponse,
    ErrorResponse
)

__all__ = [
    # Component schemas
    "TextComponent",
    "ChartComponent",
    "TableComponent",
    "AlertComponent",
    "MetricComponent",
    "ComparisonComponent",
    "TimelineComponent",
    "ResponseComponent",
    "ResponseMetadata",
    "ResponseData",
    "GeminiResponse",
    # Request/Response schemas
    "MunicipalityCreate",
    "MunicipalityResponse",
    "DocumentStatusResponse",
    "MunicipalityDocumentsStatus",
    "ChatRequest",
    "OutputPreferences",
    "ChatMessageResponse",
    "ChatHistoryResponse",
    "UploadResponse",
    "PortalPackageInfo",
    "PortalPackagesResponse",
    "HealthCheckResponse",
    "ErrorResponse"
]

