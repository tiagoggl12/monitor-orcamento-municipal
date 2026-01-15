"""
Serviço para gerenciar arquivos RAW (source of truth)
"""

import logging
from typing import Optional, Dict, Any, List, BinaryIO
from datetime import datetime
from sqlalchemy.orm import Session
from io import BytesIO

from app.models.raw_file import RawFile
from app.models.data_lineage import DataLineage

logger = logging.getLogger(__name__)


class RawFileService:
    """
    Gerencia arquivos RAW (imutáveis)
    - Armazena arquivo original
    - Calcula hashes
    - Registra lineage
    - Garante unicidade (evita duplicação)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def store_raw_file(
        self,
        content: bytes,
        filename: str,
        file_format: str,
        municipality_id: str,
        source_type: str,
        source_identifier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None
    ) -> RawFile:
        """
        Armazena arquivo RAW
        
        Args:
            content: Conteúdo do arquivo em bytes
            filename: Nome do arquivo
            file_format: Formato (CSV, PDF, JSON, etc)
            municipality_id: ID do município
            source_type: Tipo de fonte (portal_transparency, loa_upload, etc)
            source_identifier: Identificador da fonte (package_name, etc)
            metadata: Metadados adicionais
            file_path: Caminho se arquivo grande (> 10MB)
        
        Returns:
            RawFile: Objeto RawFile criado
        """
        try:
            # 1. Calcular hashes
            sha256_hash = RawFile.calculate_sha256(content)
            md5_hash = RawFile.calculate_md5(content)
            
            # 2. Verificar se arquivo já existe (deduplicação)
            existing_file = self.db.query(RawFile).filter(
                RawFile.sha256_hash == sha256_hash
            ).first()
            
            if existing_file:
                logger.info(f"📦 Arquivo já existe (SHA256: {sha256_hash[:16]}...)")
                logger.info(f"   ID existente: {existing_file.id}")
                return existing_file
            
            # 3. Determinar se armazenar em DB ou filesystem
            file_size = len(content)
            should_store_in_db = file_size < (10 * 1024 * 1024)  # 10MB
            
            # 4. Criar objeto RawFile
            raw_file = RawFile(
                municipality_id=municipality_id,
                source_type=source_type,
                source_identifier=source_identifier,
                filename=filename,
                file_format=file_format.upper(),
                file_content=content if should_store_in_db else None,
                file_path=file_path if not should_store_in_db else None,
                file_size_bytes=file_size,
                sha256_hash=sha256_hash,
                md5_hash=md5_hash,
                extra_metadata=metadata or {},
                status="stored"
            )
            
            self.db.add(raw_file)
            self.db.flush()  # Para obter o ID
            
            # 5. Registrar lineage (file upload)
            lineage = DataLineage(
                raw_file_id=raw_file.id,
                operation="file_upload",
                status="completed",
                operation_details={
                    "source_type": source_type,
                    "source_identifier": source_identifier,
                    "filename": filename,
                    "file_format": file_format,
                    "file_size_bytes": file_size,
                    "stored_in_db": should_store_in_db
                },
                result={
                    "sha256_hash": sha256_hash,
                    "md5_hash": md5_hash,
                    "deduplication": False
                },
                completed_at=datetime.utcnow()
            )
            
            self.db.add(lineage)
            self.db.commit()
            
            logger.info(f"✅ Raw file stored: {raw_file.id}")
            logger.info(f"   SHA256: {sha256_hash[:16]}...")
            logger.info(f"   Size: {file_size:,} bytes")
            logger.info(f"   Storage: {'PostgreSQL' if should_store_in_db else 'Filesystem'}")
            
            return raw_file
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Erro ao armazenar raw file: {e}")
            
            # Registrar falha no lineage
            lineage_fail = DataLineage(
                raw_file_id=None,
                operation="file_upload",
                status="failed",
                operation_details={
                    "filename": filename,
                    "error": str(e)
                },
                error_message=str(e),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(lineage_fail)
            self.db.commit()
            
            raise
    
    def get_raw_file_by_id(self, raw_file_id: str) -> Optional[RawFile]:
        """Busca raw file por ID"""
        return self.db.query(RawFile).filter(RawFile.id == raw_file_id).first()
    
    def get_raw_file_by_hash(self, sha256_hash: str) -> Optional[RawFile]:
        """Busca raw file por hash (para deduplicação)"""
        return self.db.query(RawFile).filter(
            RawFile.sha256_hash == sha256_hash
        ).first()
    
    def get_raw_files_by_source(
        self,
        source_type: str,
        source_identifier: Optional[str] = None,
        municipality_id: Optional[str] = None
    ) -> List[RawFile]:
        """Busca raw files por fonte"""
        query = self.db.query(RawFile).filter(
            RawFile.source_type == source_type
        )
        
        if source_identifier:
            query = query.filter(RawFile.source_identifier == source_identifier)
        
        if municipality_id:
            query = query.filter(RawFile.municipality_id == municipality_id)
        
        return query.order_by(RawFile.created_at.desc()).all()
    
    def get_file_content(self, raw_file: RawFile) -> bytes:
        """
        Recupera conteúdo do arquivo
        
        Args:
            raw_file: Objeto RawFile
        
        Returns:
            bytes: Conteúdo do arquivo
        """
        if raw_file.file_content:
            # Arquivo está no PostgreSQL
            return raw_file.file_content
        
        elif raw_file.file_path:
            # Arquivo está no filesystem
            with open(raw_file.file_path, 'rb') as f:
                return f.read()
        
        else:
            raise ValueError(f"Raw file {raw_file.id} não tem conteúdo nem caminho")
    
    def verify_integrity(self, raw_file: RawFile) -> bool:
        """
        Verifica integridade do arquivo (hash)
        
        Args:
            raw_file: Objeto RawFile
        
        Returns:
            bool: True se integridade OK
        """
        try:
            content = self.get_file_content(raw_file)
            current_hash = RawFile.calculate_sha256(content)
            
            if current_hash != raw_file.sha256_hash:
                logger.error(f"❌ INTEGRIDADE COMPROMETIDA!")
                logger.error(f"   File: {raw_file.id}")
                logger.error(f"   Expected: {raw_file.sha256_hash}")
                logger.error(f"   Current: {current_hash}")
                return False
            
            logger.info(f"✅ Integridade verificada: {raw_file.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar integridade: {e}")
            return False
    
    def update_status(
        self,
        raw_file: RawFile,
        new_status: str,
        error_message: Optional[str] = None
    ):
        """
        Atualiza status do raw file
        
        Args:
            raw_file: Objeto RawFile
            new_status: Novo status
            error_message: Mensagem de erro (se houver)
        """
        raw_file.status = new_status
        if error_message:
            raw_file.error_message = error_message
        
        self.db.commit()
        logger.info(f"📝 Raw file {raw_file.id} status → {new_status}")

