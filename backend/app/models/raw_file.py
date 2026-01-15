"""
Model para RawFile - Armazena arquivo original (source of truth)
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, LargeBinary, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import hashlib

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class RawFile(Base):
    """
    Armazena arquivo ORIGINAL (imutável)
    É a SOURCE OF TRUTH - nunca deletado, apenas versionado
    """
    __tablename__ = "raw_files"
    
    # Identificação
    id = Column(String, primary_key=True, default=generate_uuid)
    municipality_id = Column(String, ForeignKey("municipalities.id"), nullable=False, index=True)
    
    # Origem do arquivo
    source_type = Column(String(50), nullable=False, index=True)
    # 'portal_transparency' | 'loa_upload' | 'ldo_upload' | 'manual'
    
    source_identifier = Column(String(500), nullable=True, index=True)
    # Se portal: package_name + resource_id
    # Se upload: filename original
    
    # Dados do arquivo original
    filename = Column(String(500), nullable=False)
    file_format = Column(String(50), nullable=False)  # CSV, PDF, JSON, XML
    mime_type = Column(String(100), nullable=True)
    
    # Conteúdo (para arquivos pequenos < 10MB)
    file_content = Column(LargeBinary, nullable=True)
    
    # Para arquivos grandes, caminho no filesystem/S3
    file_path = Column(String(1000), nullable=True)
    
    file_size_bytes = Column(BigInteger, nullable=False)
    
    # Integridade
    sha256_hash = Column(String(64), nullable=False, unique=True, index=True)
    # Hash garante que arquivo NUNCA será duplicado
    
    md5_hash = Column(String(32), nullable=True)
    
    # Metadados adicionais
    extra_metadata = Column(JSON, nullable=True)
    # Ex: {"url": "...", "download_date": "...", "package_name": "..."}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Status
    status = Column(String(20), nullable=False, default="stored", index=True)
    # 'stored' | 'parsing' | 'parsed' | 'failed'
    
    error_message = Column(Text, nullable=True)
    
    # Relationships
    municipality = relationship("Municipality")
    parsed_data = relationship("ParsedData", back_populates="raw_file")
    lineage_entries = relationship("DataLineage", back_populates="raw_file")
    
    @staticmethod
    def calculate_sha256(content: bytes) -> str:
        """Calcula hash SHA256 do conteúdo"""
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def calculate_md5(content: bytes) -> str:
        """Calcula hash MD5 do conteúdo"""
        return hashlib.md5(content).hexdigest()
    
    def __repr__(self):
        return f"<RawFile(filename='{self.filename}', format='{self.file_format}', hash='{self.sha256_hash[:8]}...')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "municipality_id": self.municipality_id,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "filename": self.filename,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "sha256_hash": self.sha256_hash,
            "extra_metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "error_message": self.error_message
        }

