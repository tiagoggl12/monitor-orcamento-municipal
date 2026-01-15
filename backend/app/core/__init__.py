"""
Core module - Configurações centrais da aplicação
"""

from app.core.config import settings, get_settings
from app.core.database import get_db, init_db

__all__ = ["settings", "get_settings", "get_db", "init_db"]

