"""
Configuração da aplicação.
Todas as variáveis de ambiente são carregadas do arquivo .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union
from functools import lru_cache


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas do .env
    """
    
    # ====================================
    # Informações da Aplicação
    # ====================================
    APP_NAME: str = "Monitor de Orçamento Público Municipal"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # ====================================
    # API Keys
    # ====================================
    GEMINI_API_KEY: str  # OBRIGATÓRIO
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    
    # ====================================
    # Servidor
    # ====================================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    BACKEND_PORT: int = 4001  # Porta externa (host)
    
    # ====================================
    # CORS
    # ====================================
    CORS_ORIGINS: Union[List[str], str] = "http://localhost:4000,http://127.0.0.1:4000"
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # ====================================
    # Banco de Dados
    # ====================================
    DATABASE_URL: str = "sqlite:///data/app.db"
    
    # ====================================
    # ChromaDB
    # ====================================
    CHROMADB_HOST: str = "chromadb"
    CHROMADB_PORT: int = 8000
    CHROMADB_PERSIST_DIRECTORY: str = "/chroma/chroma"
    
    @property
    def chromadb_url(self) -> str:
        return f"http://{self.CHROMADB_HOST}:{self.CHROMADB_PORT}"
    
    # ====================================
    # Redis
    # ====================================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ====================================
    # Celery
    # ====================================
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # ====================================
    # Portal da Transparência
    # ====================================
    PORTAL_BASE_URL: str = "https://dados.fortaleza.ce.gov.br"
    PORTAL_API_VERSION: int = 3
    PORTAL_TIMEOUT: int = 30
    PORTAL_MAX_RETRIES: int = 3
    
    @property
    def portal_api_url(self) -> str:
        return f"{self.PORTAL_BASE_URL}/api/{self.PORTAL_API_VERSION}/action"
    
    # ====================================
    # Upload de Arquivos
    # ====================================
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    UPLOAD_DIR: str = "/app/data/uploads"
    
    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # ====================================
    # Processamento de PDFs
    # ====================================
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    BATCH_SIZE: int = 10
    
    # ====================================
    # Cache
    # ====================================
    CACHE_TTL_PACKAGES: int = 3600  # 1 hora
    CACHE_TTL_RESPONSES: int = 600   # 10 minutos
    
    # ====================================
    # Rate Limiting
    # ====================================
    RATE_LIMIT_PER_MINUTE: int = 10
    
    # ====================================
    # Logging
    # ====================================
    LOG_LEVEL: str = "INFO"
    
    # ====================================
    # Segurança
    # ====================================
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    
    # ====================================
    # Dados Padrão
    # ====================================
    DEFAULT_MUNICIPALITY: str = "Fortaleza"
    DEFAULT_STATE: str = "CE"
    DEFAULT_YEAR: int = 2023
    
    # Configuração do Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def get_cors_origins(self) -> List[str]:
        """
        Retorna lista de origens permitidas para CORS
        """
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
        return self.CORS_ORIGINS
    
    def validate_api_keys(self) -> None:
        """
        Valida se as API keys obrigatórias estão configuradas
        """
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY não configurada! "
                "Por favor, configure no arquivo .env"
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    Usa lru_cache para evitar recarregar o .env a cada chamada.
    """
    settings = Settings()
    
    # Validar API keys no startup
    if settings.ENVIRONMENT == "production":
        settings.validate_api_keys()
    
    return settings


# Instância global das configurações
settings = get_settings()

