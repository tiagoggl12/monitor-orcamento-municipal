"""
Model para DataLineage - Rastreamento completo de transformações
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class DataLineage(Base):
    """
    Registra TODA transformação de dados
    Permite rastreamento completo: origem → parsing → embedding → resposta
    """
    __tablename__ = "data_lineage"
    
    # Identificação
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Referências
    raw_file_id = Column(String, ForeignKey("raw_files.id"), nullable=False, index=True)
    parsed_data_id = Column(String, ForeignKey("parsed_data.id"), nullable=True, index=True)
    
    # Tipo de operação
    operation = Column(String(50), nullable=False, index=True)
    # 'file_upload' | 'file_download' | 'parse_csv' | 'parse_pdf' | 
    # 'generate_embedding' | 'store_chromadb' | 'chat_retrieval' | 
    # 'data_transformation'
    
    # Status da operação
    status = Column(String(20), nullable=False, index=True)
    # 'started' | 'completed' | 'failed'
    
    # Detalhes da operação
    operation_details = Column(JSON, nullable=True)
    # Ex: {
    #   "parser": "csv_parser",
    #   "delimiter": ";",
    #   "encoding": "utf-8",
    #   "rows_processed": 1000
    # }
    
    # Resultado da operação
    result = Column(JSON, nullable=True)
    # Ex: {
    #   "chunks_created": 10,
    #   "chromadb_ids": ["id1", "id2"],
    #   "collection_name": "portal_resultados..."
    # }
    
    # Para embeddings
    embedding_model = Column(String(100), nullable=True)
    embedding_dimensions = Column(String(10), nullable=True)
    
    # Para retrieval (quando usado em chat)
    chat_session_id = Column(String, nullable=True, index=True)
    message_id = Column(String, nullable=True, index=True)
    retrieval_score = Column(String(20), nullable=True)  # Similaridade
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Erro (se houver)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Metadados adicionais
    extra_metadata = Column(JSON, nullable=True)
    
    # Relationships
    raw_file = relationship("RawFile", back_populates="lineage_entries")
    parsed_data = relationship("ParsedData", back_populates="lineage_entries")
    
    # Índices compostos
    __table_args__ = (
        Index('idx_lineage_operation', 'operation', 'status'),
        Index('idx_lineage_chat', 'chat_session_id', 'message_id'),
        Index('idx_lineage_timeline', 'raw_file_id', 'started_at'),
    )
    
    def __repr__(self):
        return f"<DataLineage(operation='{self.operation}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "raw_file_id": self.raw_file_id,
            "parsed_data_id": self.parsed_data_id,
            "operation": self.operation,
            "status": self.status,
            "operation_details": self.operation_details,
            "result": self.result,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }
    
    def calculate_duration_seconds(self):
        """Calcula duração da operação"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

