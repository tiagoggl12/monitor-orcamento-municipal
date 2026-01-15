"""
Modelo para Jobs de Ingestão do Portal da Transparência
"""
from sqlalchemy import Column, String, Integer, DateTime, Text, BigInteger
from datetime import datetime
from app.core.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class PortalIngestionJob(Base):
    """
    Modelo para rastrear jobs de ingestão de packages do Portal
    """
    __tablename__ = "portal_ingestion_jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    municipality_id = Column(String, nullable=False, index=True)
    packages = Column(Text, nullable=False)  # JSON array de package names
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Status: 'pending', 'processing', 'completed', 'failed', 'cancelled'
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    total_packages = Column(Integer, default=0)
    processed_packages = Column(Integer, default=0)
    failed_packages = Column(Integer, default=0)
    
    total_resources = Column(Integer, default=0)
    processed_resources = Column(Integer, default=0)
    
    total_documents = Column(BigInteger, default=0)
    
    current_package = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PortalIngestionJob(id='{self.id}', status='{self.status}', packages={self.total_packages})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "municipality_id": self.municipality_id,
            "packages": self.packages,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_packages": self.total_packages,
            "processed_packages": self.processed_packages,
            "failed_packages": self.failed_packages,
            "total_resources": self.total_resources,
            "processed_resources": self.processed_resources,
            "total_documents": self.total_documents,
            "current_package": self.current_package,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

