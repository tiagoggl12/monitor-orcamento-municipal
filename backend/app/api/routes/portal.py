"""
Rotas da API para integração com o Portal da Transparência.

Este módulo expõe endpoints para consultar dados do Portal da Transparência
de Fortaleza, com cache automático usando Redis.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
import logging

from app.services.portal_client import PortalTransparenciaClient, get_portal_client
from app.services.cache_service import CacheService, get_cache_service
from app.schemas.portal_schemas import (
    PackageListResponse,
    PackageSearchRequest,
    PackageSearchResponse,
    PackageDetailSchema,
    PackageMetadataSchema,
    ResourceSchema,
    PackagesByTagRequest,
    PackagesByOrganizationRequest,
    PackagesByDateRangeRequest,
    PortalHealthResponse,
    CacheHealthResponse,
    CacheStatsResponse,
    CacheClearRequest,
    CacheClearResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Portal da Transparência"])


# ========== Dependências ==========

async def get_portal_client_dep() -> PortalTransparenciaClient:
    """Dependência para obter o cliente do portal."""
    return get_portal_client()


async def get_cache_service_dep() -> CacheService:
    """Dependência para obter o serviço de cache."""
    return await get_cache_service()


# ========== Endpoints de Listagem e Busca ==========

@router.get("/packages", response_model=PackageListResponse)
async def list_packages(
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
    cache_service: CacheService = Depends(get_cache_service_dep),
    use_cache: bool = Query(True, description="Se deve usar cache"),
):
    """
    Lista todos os packages disponíveis no Portal da Transparência.
    
    - **use_cache**: Se True, tenta recuperar do cache antes de consultar a API.
    """
    try:
        # Tentar recuperar do cache
        if use_cache:
            cached_packages = await cache_service.get_package_list()
            if cached_packages is not None:
                logger.info("Packages recuperados do cache")
                return PackageListResponse(
                    packages=cached_packages,
                    total=len(cached_packages)
                )
        
        # Consultar API
        logger.info("Consultando API do Portal da Transparência")
        packages = await portal_client.list_packages()
        
        # Armazenar no cache
        if use_cache:
            await cache_service.set_package_list(packages, ttl=3600)
        
        return PackageListResponse(
            packages=packages,
            total=len(packages)
        )
        
    except Exception as e:
        logger.error(f"Erro ao listar packages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar packages: {str(e)}"
        )


@router.post("/packages/search", response_model=PackageSearchResponse)
async def search_packages(
    request: PackageSearchRequest,
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
    cache_service: CacheService = Depends(get_cache_service_dep),
    use_cache: bool = Query(True, description="Se deve usar cache"),
):
    """
    Busca packages por query.
    
    - **query**: Termo de busca (ex: 'despesas').
    - **rows**: Número máximo de resultados (1-100).
    - **start**: Offset para paginação.
    - **sort**: Campo para ordenação (ex: 'metadata_modified desc').
    - **fq**: Filtros adicionais no formato SOLR.
    """
    try:
        search_params = request.model_dump()
        
        # Tentar recuperar do cache
        if use_cache:
            cached_results = await cache_service.get_search_results(search_params)
            if cached_results is not None:
                logger.info("Resultados de busca recuperados do cache")
                return PackageSearchResponse(**cached_results)
        
        # Consultar API
        logger.info(f"Buscando packages com query: {request.query}")
        results = await portal_client.search_packages(
            query=request.query,
            rows=request.rows,
            start=request.start,
            sort=request.sort,
            fq=request.fq,
        )
        
        # Construir resposta
        response_data = {
            "count": results.get("count", 0),
            "results": [
                PackageMetadataSchema(
                    id=pkg.get("id", ""),
                    name=pkg.get("name", ""),
                    title=pkg.get("title", ""),
                    notes=pkg.get("notes"),
                    author=pkg.get("author"),
                    maintainer=pkg.get("maintainer"),
                    license_title=pkg.get("license_title"),
                    tags=[tag.get("name") for tag in pkg.get("tags", [])],
                    organization=pkg.get("organization", {}).get("title") if pkg.get("organization") else None,
                    metadata_created=pkg.get("metadata_created"),
                    metadata_modified=pkg.get("metadata_modified"),
                    num_resources=pkg.get("num_resources", 0),
                )
                for pkg in results.get("results", [])
            ],
            "search_facets": results.get("search_facets"),
        }
        
        # Armazenar no cache
        if use_cache:
            await cache_service.set_search_results(search_params, response_data, ttl=1800)
        
        return PackageSearchResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar packages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar packages: {str(e)}"
        )


@router.get("/packages/{package_id}", response_model=PackageDetailSchema)
async def get_package_details(
    package_id: str,
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
    cache_service: CacheService = Depends(get_cache_service_dep),
    use_cache: bool = Query(True, description="Se deve usar cache"),
):
    """
    Obtém detalhes completos de um package específico.
    
    - **package_id**: ID ou nome do package.
    """
    try:
        # Tentar recuperar do cache
        if use_cache:
            cached_package = await cache_service.get_package_details(package_id)
            if cached_package is not None:
                logger.info(f"Package {package_id} recuperado do cache")
                return PackageDetailSchema(**cached_package)
        
        # Consultar API
        logger.info(f"Consultando detalhes do package: {package_id}")
        package = await portal_client.show_package(package_id)
        
        # Construir resposta
        package_data = {
            "id": package.get("id", ""),
            "name": package.get("name", ""),
            "title": package.get("title", ""),
            "notes": package.get("notes"),
            "author": package.get("author"),
            "maintainer": package.get("maintainer"),
            "license_title": package.get("license_title"),
            "tags": [tag.get("name") for tag in package.get("tags", [])],
            "organization": package.get("organization", {}).get("title") if package.get("organization") else None,
            "metadata_created": package.get("metadata_created"),
            "metadata_modified": package.get("metadata_modified"),
            "num_resources": package.get("num_resources", 0),
            "resources": [
                ResourceSchema(
                    id=res.get("id", ""),
                    name=res.get("name", ""),
                    description=res.get("description"),
                    format=res.get("format", ""),
                    url=res.get("url", ""),
                    size=res.get("size"),
                    mimetype=res.get("mimetype"),
                    created=res.get("created"),
                    last_modified=res.get("last_modified"),
                )
                for res in package.get("resources", [])
            ],
            "extras": {extra.get("key"): extra.get("value") for extra in package.get("extras", [])},
        }
        
        # Armazenar no cache
        if use_cache:
            await cache_service.set_package_details(package_id, package_data, ttl=3600)
        
        return PackageDetailSchema(**package_data)
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter detalhes do package: {str(e)}"
        )


@router.get("/packages/{package_id}/metadata", response_model=PackageMetadataSchema)
async def get_package_metadata(
    package_id: str,
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
):
    """
    Obtém apenas os metadados de um package (sem recursos).
    
    - **package_id**: ID ou nome do package.
    """
    try:
        logger.info(f"Consultando metadados do package: {package_id}")
        metadata = await portal_client.get_package_metadata(package_id)
        return PackageMetadataSchema(**metadata)
        
    except Exception as e:
        logger.error(f"Erro ao obter metadados do package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter metadados do package: {str(e)}"
        )


@router.get("/packages/{package_id}/resources", response_model=List[ResourceSchema])
async def get_package_resources(
    package_id: str,
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
):
    """
    Obtém apenas os recursos (arquivos/APIs) de um package.
    
    - **package_id**: ID ou nome do package.
    """
    try:
        logger.info(f"Consultando recursos do package: {package_id}")
        resources = await portal_client.get_package_resources(package_id)
        
        return [
            ResourceSchema(
                id=res.get("id", ""),
                name=res.get("name", ""),
                description=res.get("description"),
                format=res.get("format", ""),
                url=res.get("url", ""),
                size=res.get("size"),
                mimetype=res.get("mimetype"),
                created=res.get("created"),
                last_modified=res.get("last_modified"),
            )
            for res in resources
        ]
        
    except Exception as e:
        logger.error(f"Erro ao obter recursos do package {package_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao obter recursos do package: {str(e)}"
        )


# ========== Endpoints de Filtros Específicos ==========

@router.post("/packages/by-tag", response_model=PackageSearchResponse)
async def search_packages_by_tag(
    request: PackagesByTagRequest,
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
):
    """
    Busca packages por tag específica.
    
    - **tag**: Tag para filtrar (ex: 'despesas', 'receitas').
    """
    try:
        logger.info(f"Buscando packages com tag: {request.tag}")
        results = await portal_client.search_by_tag(request.tag, request.rows)
        
        return PackageSearchResponse(
            count=results.get("count", 0),
            results=[
                PackageMetadataSchema(
                    id=pkg.get("id", ""),
                    name=pkg.get("name", ""),
                    title=pkg.get("title", ""),
                    notes=pkg.get("notes"),
                    author=pkg.get("author"),
                    maintainer=pkg.get("maintainer"),
                    license_title=pkg.get("license_title"),
                    tags=[tag.get("name") for tag in pkg.get("tags", [])],
                    organization=pkg.get("organization", {}).get("title") if pkg.get("organization") else None,
                    metadata_created=pkg.get("metadata_created"),
                    metadata_modified=pkg.get("metadata_modified"),
                    num_resources=pkg.get("num_resources", 0),
                )
                for pkg in results.get("results", [])
            ],
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar packages por tag: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar packages por tag: {str(e)}"
        )


@router.get("/packages/recent", response_model=PackageSearchResponse)
async def get_recent_packages(
    rows: int = Query(10, ge=1, le=100, description="Número de packages a retornar"),
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
):
    """
    Obtém os packages mais recentes (ordenados por data de modificação).
    """
    try:
        logger.info(f"Buscando {rows} packages mais recentes")
        results = await portal_client.get_recent_packages(rows)
        
        return PackageSearchResponse(
            count=results.get("count", 0),
            results=[
                PackageMetadataSchema(
                    id=pkg.get("id", ""),
                    name=pkg.get("name", ""),
                    title=pkg.get("title", ""),
                    notes=pkg.get("notes"),
                    author=pkg.get("author"),
                    maintainer=pkg.get("maintainer"),
                    license_title=pkg.get("license_title"),
                    tags=[tag.get("name") for tag in pkg.get("tags", [])],
                    organization=pkg.get("organization", {}).get("title") if pkg.get("organization") else None,
                    metadata_created=pkg.get("metadata_created"),
                    metadata_modified=pkg.get("metadata_modified"),
                    num_resources=pkg.get("num_resources", 0),
                )
                for pkg in results.get("results", [])
            ],
        )
        
    except Exception as e:
        logger.error(f"Erro ao buscar packages recentes: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar packages recentes: {str(e)}"
        )


# ========== Endpoints de Saúde e Cache ==========

@router.get("/health", response_model=PortalHealthResponse)
async def portal_health_check(
    portal_client: PortalTransparenciaClient = Depends(get_portal_client_dep),
):
    """
    Verifica se a API do Portal da Transparência está acessível.
    """
    try:
        accessible = await portal_client.health_check()
        
        return PortalHealthResponse(
            status="healthy" if accessible else "unhealthy",
            accessible=accessible,
            timestamp=datetime.utcnow(),
            message="API do Portal da Transparência está acessível" if accessible else "Não foi possível acessar a API"
        )
        
    except Exception as e:
        logger.error(f"Erro no health check do portal: {str(e)}")
        return PortalHealthResponse(
            status="unhealthy",
            accessible=False,
            timestamp=datetime.utcnow(),
            message=f"Erro: {str(e)}"
        )


@router.get("/cache/health", response_model=CacheHealthResponse)
async def cache_health_check(
    cache_service: CacheService = Depends(get_cache_service_dep),
):
    """
    Verifica se o serviço de cache (Redis) está acessível.
    """
    try:
        accessible = await cache_service.health_check()
        
        return CacheHealthResponse(
            status="healthy" if accessible else "unhealthy",
            accessible=accessible,
            timestamp=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erro no health check do cache: {str(e)}")
        return CacheHealthResponse(
            status="unhealthy",
            accessible=False,
            timestamp=datetime.utcnow(),
        )


@router.post("/cache/clear", response_model=CacheClearResponse)
async def clear_cache(
    request: CacheClearRequest,
    cache_service: CacheService = Depends(get_cache_service_dep),
):
    """
    Limpa o cache do Portal da Transparência.
    
    - **pattern**: Padrão de chaves a limpar. Se None, limpa todo o cache do portal.
    """
    try:
        pattern = request.pattern or "portal:*"
        logger.info(f"Limpando cache com padrão: {pattern}")
        
        deleted_keys = await cache_service.clear_pattern(pattern)
        
        return CacheClearResponse(
            deleted_keys=deleted_keys,
            pattern=pattern,
            timestamp=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao limpar cache: {str(e)}"
        )

