"""
Dependencies para injeção nas rotas
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.models import Municipality


def get_current_settings():
    """
    Dependency para obter settings
    """
    return settings


async def get_municipality_or_404(
    municipality_id: str,
    db: Session = Depends(get_db)
) -> Municipality:
    """
    Busca município por ID ou retorna 404
    """
    municipality = db.query(Municipality).filter(Municipality.id == municipality_id).first()
    
    if not municipality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município com ID '{municipality_id}' não encontrado"
        )
    
    return municipality


async def get_municipality_by_params(
    name: str,
    state: str,
    year: int,
    db: Session = Depends(get_db)
) -> Optional[Municipality]:
    """
    Busca município por nome, estado e ano
    """
    municipality = db.query(Municipality).filter(
        Municipality.name == name,
        Municipality.state == state.upper(),
        Municipality.year == year
    ).first()
    
    return municipality

