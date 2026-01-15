"""
Model para ParsedData - Dados parseados estruturados (linha/coluna)
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class ParsedData(Base):
    """
    Representa UMA LINHA de dados parseados de um arquivo
    Mantém estrutura original (campo → valor)
    """
    __tablename__ = "parsed_data"
    
    # Identificação
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Referência ao arquivo original (SOURCE OF TRUTH)
    raw_file_id = Column(String, ForeignKey("raw_files.id"), nullable=False, index=True)
    
    # Posição no arquivo original
    row_number = Column(Integer, nullable=False)
    # Linha exata no arquivo (para auditabilidade)
    
    # Dados parseados
    data = Column(JSON, nullable=False)
    # Estrutura: {"EDITAL N°": "10367", "ORIGEM": "SEINF", ...}
    # Mantém nomes ORIGINAIS das colunas
    
    # Dados normalizados (para busca)
    data_normalized = Column(JSON, nullable=True)
    # Estrutura: {"edital_n": 10367, "origem": "SEINF", ...}
    # Nomes normalizados para facilitar queries
    
    # Conteúdo textual completo (para embedding)
    text_content = Column(Text, nullable=False)
    # Ex: "EDITAL N°: 10367 | ORIGEM: SEINF | MODALIDADE: CE | ..."
    # Usado para busca semântica no ChromaDB
    
    # Timestamps
    parsed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    raw_file = relationship("RawFile", back_populates="parsed_data")
    lineage_entries = relationship("DataLineage", back_populates="parsed_data")
    
    # Índices compostos para queries comuns
    __table_args__ = (
        Index('idx_raw_file_row', 'raw_file_id', 'row_number'),
    )
    
    def __repr__(self):
        return f"<ParsedData(raw_file_id='{self.raw_file_id}', row={self.row_number})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "raw_file_id": self.raw_file_id,
            "row_number": self.row_number,
            "data": self.data,
            "text_content": self.text_content,
            "parsed_at": self.parsed_at.isoformat() if self.parsed_at else None
        }
    
    def to_dict_with_lineage(self):
        """
        Retorna dados + lineage completo (para verificação judicial)
        """
        return {
            **self.to_dict(),
            "raw_file": self.raw_file.to_dict() if self.raw_file else None,
            "lineage": [entry.to_dict() for entry in self.lineage_entries]
        }

