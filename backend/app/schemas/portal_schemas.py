"""
Schemas Pydantic para o Portal da Transparência.

Define estruturas de dados para requisições e respostas relacionadas
ao Portal da Transparência de Fortaleza.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


# ========== Schemas de Recursos (Resources) ==========

class ResourceSchema(BaseModel):
    """Schema para um recurso (arquivo/API) de um package."""
    
    id: str = Field(..., description="ID único do recurso")
    name: str = Field(..., description="Nome do recurso")
    description: Optional[str] = Field(None, description="Descrição do recurso")
    format: str = Field(..., description="Formato do recurso (CSV, JSON, etc)")
    url: str = Field(..., description="URL para acessar o recurso")
    size: Optional[int] = Field(None, description="Tamanho do arquivo em bytes")
    mimetype: Optional[str] = Field(None, description="MIME type do recurso")
    created: Optional[datetime] = Field(None, description="Data de criação")
    last_modified: Optional[datetime] = Field(None, description="Data da última modificação")


# ========== Schemas de Packages ==========

class PackageMetadataSchema(BaseModel):
    """Schema para metadados básicos de um package."""
    
    id: str = Field(..., description="ID único do package")
    name: str = Field(..., description="Nome identificador do package")
    title: str = Field(..., description="Título do package")
    notes: Optional[str] = Field(None, description="Descrição/notas do package")
    author: Optional[str] = Field(None, description="Autor do package")
    maintainer: Optional[str] = Field(None, description="Mantenedor do package")
    license_title: Optional[str] = Field(None, description="Licença do package")
    tags: List[str] = Field(default_factory=list, description="Tags associadas")
    organization: Optional[str] = Field(None, description="Organização responsável")
    metadata_created: Optional[datetime] = Field(None, description="Data de criação dos metadados")
    metadata_modified: Optional[datetime] = Field(None, description="Data de modificação dos metadados")
    num_resources: int = Field(0, description="Número de recursos disponíveis")


class PackageDetailSchema(PackageMetadataSchema):
    """Schema para detalhes completos de um package (incluindo recursos)."""
    
    resources: List[ResourceSchema] = Field(
        default_factory=list,
        description="Lista de recursos disponíveis no package"
    )
    extras: Optional[Dict[str, Any]] = Field(
        None,
        description="Campos extras/customizados do package"
    )


# ========== Schemas de Busca ==========

class PackageSearchRequest(BaseModel):
    """Schema para requisição de busca de packages."""
    
    query: str = Field(
        ...,
        description="Termo de busca",
        example="despesas"
    )
    rows: int = Field(
        10,
        ge=1,
        le=100,
        description="Número máximo de resultados"
    )
    start: int = Field(
        0,
        ge=0,
        description="Offset para paginação"
    )
    sort: Optional[str] = Field(
        None,
        description="Campo para ordenação (ex: 'metadata_modified desc')",
        example="metadata_modified desc"
    )
    fq: Optional[str] = Field(
        None,
        description="Filtros adicionais no formato SOLR",
        example="tags:despesas"
    )


class PackageSearchResponse(BaseModel):
    """Schema para resposta de busca de packages."""
    
    count: int = Field(..., description="Número total de resultados encontrados")
    results: List[PackageMetadataSchema] = Field(
        default_factory=list,
        description="Lista de packages encontrados"
    )
    search_facets: Optional[Dict[str, Any]] = Field(
        None,
        description="Facetas de busca (agregações)"
    )


# ========== Schemas de Listagem ==========

class PackageListResponse(BaseModel):
    """Schema para resposta de listagem de packages."""
    
    packages: List[str] = Field(
        default_factory=list,
        description="Lista com IDs/nomes dos packages"
    )
    total: int = Field(..., description="Número total de packages")


# ========== Schemas de Filtros Específicos ==========

class PackagesByTagRequest(BaseModel):
    """Schema para busca de packages por tag."""
    
    tag: str = Field(..., description="Tag para filtrar", example="despesas")
    rows: int = Field(10, ge=1, le=100, description="Número máximo de resultados")


class PackagesByOrganizationRequest(BaseModel):
    """Schema para busca de packages por organização."""
    
    organization: str = Field(
        ...,
        description="Nome ou ID da organização",
        example="prefeitura-fortaleza"
    )
    rows: int = Field(10, ge=1, le=100, description="Número máximo de resultados")


class PackagesByDateRangeRequest(BaseModel):
    """Schema para busca de packages por intervalo de datas."""
    
    start_date: datetime = Field(
        ...,
        description="Data inicial do intervalo"
    )
    end_date: datetime = Field(
        ...,
        description="Data final do intervalo"
    )
    query: str = Field(
        "*:*",
        description="Query de busca adicional"
    )
    rows: int = Field(10, ge=1, le=100, description="Número máximo de resultados")


# ========== Schemas de Saúde e Status ==========

class PortalHealthResponse(BaseModel):
    """Schema para resposta de health check do Portal."""
    
    status: str = Field(..., description="Status da API", example="healthy")
    accessible: bool = Field(..., description="Se a API está acessível")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp da verificação"
    )
    message: Optional[str] = Field(None, description="Mensagem adicional")


class CacheHealthResponse(BaseModel):
    """Schema para resposta de health check do Cache."""
    
    status: str = Field(..., description="Status do Redis", example="healthy")
    accessible: bool = Field(..., description="Se o Redis está acessível")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp da verificação"
    )


# ========== Schemas de Cache ==========

class CacheStatsResponse(BaseModel):
    """Schema para estatísticas do cache."""
    
    total_keys: int = Field(..., description="Número total de chaves no cache")
    portal_keys: int = Field(..., description="Número de chaves relacionadas ao portal")
    memory_usage: Optional[str] = Field(None, description="Uso de memória")


class CacheClearRequest(BaseModel):
    """Schema para requisição de limpeza de cache."""
    
    pattern: Optional[str] = Field(
        None,
        description="Padrão de chaves a limpar (ex: 'portal:package:*'). Se None, limpa tudo do portal."
    )


class CacheClearResponse(BaseModel):
    """Schema para resposta de limpeza de cache."""
    
    deleted_keys: int = Field(..., description="Número de chaves deletadas")
    pattern: str = Field(..., description="Padrão usado para limpeza")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp da operação"
    )

