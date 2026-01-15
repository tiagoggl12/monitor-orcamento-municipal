"""
Model para FileSchema - Schema descoberto de arquivos
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class FileSchema(Base):
    """
    Armazena schema descoberto de um arquivo
    Permite que o LLM saiba exatamente quais colunas existem
    """
    __tablename__ = "file_schemas"
    
    # Identificação
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Referência ao raw file
    raw_file_id = Column(String, ForeignKey("raw_files.id"), nullable=False, index=True)
    
    # Informações do arquivo
    filename = Column(String(500), nullable=False)
    file_format = Column(String(50), nullable=False)  # CSV, JSON, etc
    
    # Schema descoberto
    columns_info = Column(JSON, nullable=False)
    # Estrutura: [
    #   {
    #     "original_name": "EDITAL N°",
    #     "normalized_name": "edital_n",
    #     "display_name": "Edital N",
    #     "semantic_aliases": ["edital", "numero_edital", ...],
    #     "data_type": "integer",
    #     "sample_values": [9741, 10260, ...],
    #     "unique_values": null,  # ou ["SEINF", "SME", ...] para categorias
    #     "content_signature": "numeric_sequential"
    #   },
    #   ...
    # ]
    
    # Estatísticas
    total_rows = Column(Integer, nullable=True)
    total_columns = Column(Integer, nullable=False)
    
    # Metadados adicionais
    discovery_metadata = Column(JSON, nullable=True)
    # Ex: {
    #   "delimiter": ";",
    #   "encoding": "utf-8",
    #   "has_header": true,
    #   "discovery_method": "pandas",
    #   "discovery_version": "1.0"
    # }
    
    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Status
    status = Column(String(20), nullable=False, default="active", index=True)
    # 'active' | 'outdated' | 'deprecated'
    
    # Relationships
    raw_file = relationship("RawFile")
    
    def __repr__(self):
        return f"<FileSchema(filename='{self.filename}', columns={self.total_columns})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "raw_file_id": self.raw_file_id,
            "filename": self.filename,
            "file_format": self.file_format,
            "columns_info": self.columns_info,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "discovery_metadata": self.discovery_metadata,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "status": self.status
        }
    
    def get_column_by_name(self, column_name: str):
        """Busca coluna por nome original"""
        for col in self.columns_info:
            if col["original_name"] == column_name:
                return col
        return None
    
    def get_column_by_alias(self, alias: str):
        """Busca coluna por alias semântico"""
        alias_lower = alias.lower().strip()
        
        for col in self.columns_info:
            # Verificar aliases
            if alias_lower in [a.lower() for a in col.get("semantic_aliases", [])]:
                return col
            
            # Verificar nome normalizado
            if alias_lower == col.get("normalized_name", "").lower():
                return col
            
            # Verificar nome original
            if alias_lower == col.get("original_name", "").lower():
                return col
        
        return None
    
    def search_columns_by_type(self, data_type: str):
        """Busca colunas por tipo de dados"""
        return [
            col for col in self.columns_info
            if col.get("data_type") == data_type
        ]
    
    def get_categorical_columns(self):
        """Retorna colunas categóricas (com unique_values)"""
        return [
            col for col in self.columns_info
            if col.get("unique_values") is not None
        ]
    
    def format_for_llm(self) -> str:
        """
        Formata schema de forma legível para LLM
        """
        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"ARQUIVO: {self.filename}",
            f"ID: {self.id}",
            f"Total de linhas: {self.total_rows or 'desconhecido'}",
            f"Total de colunas: {self.total_columns}",
            f"",
            f"COLUNAS:"
        ]
        
        for col in self.columns_info:
            lines.append(f"")
            lines.append(f"  📋 Coluna: \"{col['original_name']}\"")
            lines.append(f"     Tipo: {col['data_type']}")
            
            aliases = col.get('semantic_aliases', [])
            if aliases:
                lines.append(f"     Aliases: {', '.join(aliases[:5])}")
            
            samples = col.get('sample_values', [])
            if samples:
                lines.append(f"     Exemplos: {samples}")
            
            unique = col.get('unique_values')
            if unique:
                lines.append(f"     Valores únicos: {unique}")
        
        return "\n".join(lines)


class SchemaAlias(Base):
    """
    Índice de busca reversa: alias → coluna
    Acelera busca de colunas por aliases
    """
    __tablename__ = "schema_aliases"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    
    # Referência ao schema
    file_schema_id = Column(String, ForeignKey("file_schemas.id"), nullable=False, index=True)
    
    # Alias (normalizado, lowercase)
    alias = Column(String(200), nullable=False, index=True)
    
    # Nome original da coluna
    original_column_name = Column(String(200), nullable=False)
    
    # Tipo de match
    match_type = Column(String(50), nullable=False)
    # 'exact' | 'normalized' | 'semantic' | 'fuzzy'
    
    # Confiança do match (0.0 a 1.0)
    confidence = Column(String(10), nullable=False, default="1.0")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<SchemaAlias(alias='{self.alias}' → '{self.original_column_name}')>"

