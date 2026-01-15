"""
Cliente HTTP para interagir com o Portal da Transparência de Fortaleza.

Este módulo fornece uma interface para consumir a API CKAN do portal
dados.fortaleza.ce.gov.br, incluindo listagem de packages, busca e
detalhamento de datasets.
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class PortalTransparenciaClient:
    """Cliente para interagir com a API do Portal da Transparência."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Inicializa o cliente do Portal da Transparência.

        Args:
            base_url: URL base da API. Se None, usa o valor de settings.
            timeout: Timeout para requisições HTTP em segundos.
        """
        self.base_url = base_url or settings.portal_api_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True,
        )

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP para a API.

        Args:
            endpoint: Endpoint da API (ex: 'package_list').
            params: Parâmetros da query string.

        Returns:
            Resposta JSON da API.

        Raises:
            httpx.HTTPError: Se a requisição falhar.
        """
        # Como base_url já contém /api/3/action, usar apenas o endpoint
        url = f"/{endpoint}"
        
        try:
            logger.info(f"Fazendo requisição para {self.base_url}{url} com params: {params}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # CKAN retorna estrutura: {"success": true, "result": {...}}
            if not data.get("success", False):
                error_msg = data.get("error", {}).get("message", "Erro desconhecido")
                logger.error(f"API retornou erro: {error_msg}")
                raise ValueError(f"API Error: {error_msg}")
            
            logger.info(f"Requisição bem-sucedida para {url}")
            return data.get("result", {})
            
        except httpx.HTTPError as e:
            logger.error(f"Erro HTTP ao acessar {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao acessar {url}: {str(e)}")
            raise

    async def list_packages(self) -> List[str]:
        """
        Lista todos os packages (datasets) disponíveis.

        Returns:
            Lista com os IDs/nomes dos packages.

        Example:
            >>> client = PortalTransparenciaClient()
            >>> packages = await client.list_packages()
            >>> print(packages[:5])
            ['despesas-2023', 'receitas-2023', ...]
        """
        result = await self._make_request("package_list")
        return result if isinstance(result, list) else []

    async def search_packages(
        self,
        query: str,
        rows: int = 10,
        start: int = 0,
        sort: Optional[str] = None,
        fq: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Busca packages por query.

        Args:
            query: Termo de busca (ex: 'despesas').
            rows: Número máximo de resultados.
            start: Offset para paginação.
            sort: Campo para ordenação (ex: 'metadata_modified desc').
            fq: Filtros adicionais no formato SOLR.

        Returns:
            Dicionário com resultados da busca:
            {
                "count": int,
                "results": [...]
            }

        Example:
            >>> results = await client.search_packages("despesas", rows=5)
            >>> print(f"Encontrados {results['count']} datasets")
        """
        params = {
            "q": query,
            "rows": rows,
            "start": start,
        }
        
        if sort:
            params["sort"] = sort
        if fq:
            params["fq"] = fq
        
        result = await self._make_request("package_search", params)
        return result

    async def show_package(self, package_id: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um package.

        Args:
            package_id: ID ou nome do package.

        Returns:
            Dicionário com todos os metadados e recursos do package.

        Example:
            >>> package = await client.show_package("despesas-2023")
            >>> print(package['title'])
            >>> for resource in package['resources']:
            ...     print(resource['name'], resource['url'])
        """
        params = {"id": package_id}
        result = await self._make_request("package_show", params)
        return result

    async def get_package_resources(self, package_id: str) -> List[Dict[str, Any]]:
        """
        Obtém apenas os recursos (arquivos/APIs) de um package.

        Args:
            package_id: ID ou nome do package.

        Returns:
            Lista de recursos disponíveis no package.

        Example:
            >>> resources = await client.get_package_resources("despesas-2023")
            >>> for resource in resources:
            ...     print(f"{resource['name']}: {resource['format']}")
        """
        package = await self.show_package(package_id)
        return package.get("resources", [])

    async def search_by_tag(self, tag: str, rows: int = 10) -> Dict[str, Any]:
        """
        Busca packages por tag.

        Args:
            tag: Tag para filtrar (ex: 'despesas', 'receitas').
            rows: Número máximo de resultados.

        Returns:
            Resultados da busca.
        """
        fq = f"tags:{tag}"
        return await self.search_packages("*:*", rows=rows, fq=fq)

    async def search_by_organization(
        self, organization: str, rows: int = 10
    ) -> Dict[str, Any]:
        """
        Busca packages por organização.

        Args:
            organization: Nome ou ID da organização.
            rows: Número máximo de resultados.

        Returns:
            Resultados da busca.
        """
        fq = f"organization:{organization}"
        return await self.search_packages("*:*", rows=rows, fq=fq)

    async def get_recent_packages(self, rows: int = 10) -> Dict[str, Any]:
        """
        Obtém os packages mais recentes.

        Args:
            rows: Número de packages a retornar.

        Returns:
            Packages ordenados por data de modificação.
        """
        return await self.search_packages(
            "*:*", rows=rows, sort="metadata_modified desc"
        )

    async def search_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        query: str = "*:*",
        rows: int = 10,
    ) -> Dict[str, Any]:
        """
        Busca packages em um intervalo de datas.

        Args:
            start_date: Data inicial.
            end_date: Data final.
            query: Query de busca.
            rows: Número máximo de resultados.

        Returns:
            Resultados da busca filtrados por data.
        """
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        fq = f"metadata_modified:[{start_str} TO {end_str}]"
        
        return await self.search_packages(query, rows=rows, fq=fq)

    async def get_package_metadata(self, package_id: str) -> Dict[str, Any]:
        """
        Obtém apenas os metadados principais de um package (sem recursos).

        Args:
            package_id: ID ou nome do package.

        Returns:
            Metadados do package (título, descrição, tags, etc).
        """
        package = await self.show_package(package_id)
        
        return {
            "id": package.get("id"),
            "name": package.get("name"),
            "title": package.get("title"),
            "notes": package.get("notes"),
            "author": package.get("author"),
            "maintainer": package.get("maintainer"),
            "license_title": package.get("license_title"),
            "tags": [tag.get("name") for tag in package.get("tags", [])],
            "organization": package.get("organization", {}).get("title"),
            "metadata_created": package.get("metadata_created"),
            "metadata_modified": package.get("metadata_modified"),
            "num_resources": package.get("num_resources", 0),
        }

    async def health_check(self) -> bool:
        """
        Verifica se a API está acessível.

        Returns:
            True se a API está respondendo, False caso contrário.
        """
        try:
            await self.list_packages()
            return True
        except Exception as e:
            logger.error(f"Health check falhou: {str(e)}")
            return False


# Singleton para reutilização
_portal_client: Optional[PortalTransparenciaClient] = None


def get_portal_client() -> PortalTransparenciaClient:
    """
    Obtém uma instância singleton do cliente do Portal da Transparência.

    Returns:
        Instância do PortalTransparenciaClient.
    """
    global _portal_client
    if _portal_client is None:
        _portal_client = PortalTransparenciaClient()
    return _portal_client


async def close_portal_client():
    """Fecha o cliente singleton."""
    global _portal_client
    if _portal_client is not None:
        await _portal_client.close()
        _portal_client = None

