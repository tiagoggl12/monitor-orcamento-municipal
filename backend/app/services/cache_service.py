"""
Serviço de cache usando Redis para otimizar consultas ao Portal da Transparência.

Este módulo fornece funções para armazenar e recuperar dados em cache,
reduzindo a carga na API externa e melhorando a performance.
"""

import json
import hashlib
from typing import Any, Optional
from datetime import timedelta
import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Serviço para gerenciar cache com Redis."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Inicializa o serviço de cache.

        Args:
            redis_url: URL de conexão do Redis. Se None, usa o valor de settings.
        """
        self.redis_url = redis_url or settings.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hora em segundos

    async def connect(self):
        """Estabelece conexão com o Redis."""
        if self.redis_client is None:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Testa a conexão
                await self.redis_client.ping()
                logger.info("Conectado ao Redis com sucesso")
            except Exception as e:
                logger.error(f"Erro ao conectar ao Redis: {str(e)}")
                raise

    async def close(self):
        """Fecha a conexão com o Redis."""
        if self.redis_client is not None:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Conexão com Redis fechada")

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    def _generate_key(self, prefix: str, identifier: str) -> str:
        """
        Gera uma chave única para o cache.

        Args:
            prefix: Prefixo da chave (ex: 'package', 'search').
            identifier: Identificador único (pode ser hash de parâmetros).

        Returns:
            Chave formatada para o Redis.
        """
        return f"portal:{prefix}:{identifier}"

    def _hash_params(self, params: dict) -> str:
        """
        Gera um hash dos parâmetros para usar como identificador.

        Args:
            params: Dicionário de parâmetros.

        Returns:
            Hash MD5 dos parâmetros.
        """
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """
        Recupera um valor do cache.

        Args:
            key: Chave do cache.

        Returns:
            Valor armazenado ou None se não existir/expirado.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            value = await self.redis_client.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {str(e)}")
            return None

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Armazena um valor no cache.

        Args:
            key: Chave do cache.
            value: Valor a ser armazenado (será serializado como JSON).
            ttl: Tempo de vida em segundos. Se None, usa default_ttl.

        Returns:
            True se armazenado com sucesso, False caso contrário.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            ttl = ttl or self.default_ttl
            value_json = json.dumps(value)
            await self.redis_client.setex(key, ttl, value_json)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.

        Args:
            key: Chave do cache.

        Returns:
            True se removido com sucesso, False caso contrário.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            deleted = await self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Erro ao deletar do cache: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Remove todas as chaves que correspondem ao padrão.

        Args:
            pattern: Padrão de busca (ex: 'portal:package:*').

        Returns:
            Número de chaves removidas.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cache CLEAR: {deleted} chaves removidas para padrão {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Erro ao limpar cache por padrão: {str(e)}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Verifica se uma chave existe no cache.

        Args:
            key: Chave do cache.

        Returns:
            True se existe, False caso contrário.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            exists = await self.redis_client.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência no cache: {str(e)}")
            return False

    async def get_ttl(self, key: str) -> int:
        """
        Obtém o tempo de vida restante de uma chave.

        Args:
            key: Chave do cache.

        Returns:
            TTL em segundos, -1 se a chave não tem TTL, -2 se não existe.
        """
        if self.redis_client is None:
            await self.connect()

        try:
            ttl = await self.redis_client.ttl(key)
            return ttl
        except Exception as e:
            logger.error(f"Erro ao obter TTL: {str(e)}")
            return -2

    # Métodos específicos para o Portal da Transparência

    async def get_package_list(self) -> Optional[list]:
        """Recupera lista de packages do cache."""
        key = self._generate_key("package", "list")
        return await self.get(key)

    async def set_package_list(self, packages: list, ttl: int = 3600) -> bool:
        """Armazena lista de packages no cache."""
        key = self._generate_key("package", "list")
        return await self.set(key, packages, ttl)

    async def get_package_details(self, package_id: str) -> Optional[dict]:
        """Recupera detalhes de um package do cache."""
        key = self._generate_key("package", package_id)
        return await self.get(key)

    async def set_package_details(
        self, package_id: str, details: dict, ttl: int = 3600
    ) -> bool:
        """Armazena detalhes de um package no cache."""
        key = self._generate_key("package", package_id)
        return await self.set(key, details, ttl)

    async def get_search_results(self, search_params: dict) -> Optional[dict]:
        """Recupera resultados de busca do cache."""
        params_hash = self._hash_params(search_params)
        key = self._generate_key("search", params_hash)
        return await self.get(key)

    async def set_search_results(
        self, search_params: dict, results: dict, ttl: int = 1800
    ) -> bool:
        """Armazena resultados de busca no cache (TTL menor: 30 min)."""
        params_hash = self._hash_params(search_params)
        key = self._generate_key("search", params_hash)
        return await self.set(key, results, ttl)

    async def clear_all_portal_cache(self) -> int:
        """Limpa todo o cache relacionado ao Portal da Transparência."""
        return await self.clear_pattern("portal:*")

    async def health_check(self) -> bool:
        """
        Verifica se o Redis está acessível.

        Returns:
            True se o Redis está respondendo, False caso contrário.
        """
        try:
            if self.redis_client is None:
                await self.connect()
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Health check do Redis falhou: {str(e)}")
            return False


# Singleton para reutilização
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """
    Obtém uma instância singleton do serviço de cache.

    Returns:
        Instância do CacheService.
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.connect()
    return _cache_service


async def close_cache_service():
    """Fecha o serviço de cache singleton."""
    global _cache_service
    if _cache_service is not None:
        await _cache_service.close()
        _cache_service = None

