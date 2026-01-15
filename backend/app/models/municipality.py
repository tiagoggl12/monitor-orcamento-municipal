"""
Model para Município
"""

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Municipality(Base):
    __tablename__ = "municipalities"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    state = Column(String(2), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="municipality", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="municipality", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Municipality(name='{self.name}', state='{self.state}', year={self.year})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "year": self.year,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

