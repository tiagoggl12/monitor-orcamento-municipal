"""
Model para Sessão de Chat
"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    municipality_id = Column(String, ForeignKey("municipalities.id"), nullable=False, index=True)
    title = Column(String(200), nullable=True)  # Título da sessão
    user_id = Column(String, nullable=True, index=True)  # NULL para versão sem autenticação
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    municipality = relationship("Municipality", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id='{self.id}', municipality_id='{self.municipality_id}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "municipality_id": self.municipality_id,
            "title": self.title or f"Chat - {self.created_at.strftime('%d/%m/%Y %H:%M') if self.created_at else 'Sem data'}",
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "message_count": len(self.messages) if hasattr(self, 'messages') else 0
        }

