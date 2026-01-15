"""
Model para Mensagem (histórico de chat)
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)  # 'user' ou 'assistant'
    content = Column(Text, nullable=False)
    structured_response = Column(JSON, nullable=True)  # Resposta estruturada do Gemini (JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processing_time_ms = Column(Integer, nullable=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(role='{self.role}', timestamp='{self.timestamp}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "structured_response": self.structured_response,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "processing_time_ms": self.processing_time_ms
        }

