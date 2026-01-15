"""
Model para Documento (LOA/LDO)
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    municipality_id = Column(String, ForeignKey("municipalities.id"), nullable=False, index=True)
    type = Column(String(10), nullable=False, index=True)  # 'LOA' ou 'LDO'
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger)
    upload_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Status: 'pending', 'processing', 'completed', 'failed'
    chromadb_collection_id = Column(String(100), nullable=True)
    total_chunks = Column(Integer, default=0)
    processed_batches = Column(Integer, default=0)  # Batches já processados
    total_batches = Column(Integer, default=0)  # Total de batches a processar
    error_message = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    # Relationships
    municipality = relationship("Municipality", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(type='{self.type}', status='{self.status}', version={self.version})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "municipality_id": self.municipality_id,
            "type": self.type,
            "filename": self.filename,
            "file_size_bytes": self.file_size_bytes,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "processed_date": self.processed_date.isoformat() if self.processed_date else None,
            "status": self.status,
            "chromadb_collection_id": self.chromadb_collection_id,
            "total_chunks": self.total_chunks,
            "processed_batches": self.processed_batches or 0,
            "total_batches": self.total_batches or 0,
            "error_message": self.error_message,
            "version": self.version
        }

