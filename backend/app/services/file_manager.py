"""
Gerenciador de arquivos - salva e gerencia uploads
"""

from fastapi import UploadFile
from pathlib import Path
import shutil
import uuid
from datetime import datetime
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class FileManager:
    """
    Gerenciador de arquivos para uploads
    """
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self) -> None:
        """
        Garante que o diretório de upload existe
        """
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Upload directory ensured", path=str(self.upload_dir))
    
    async def save_upload(
        self,
        file: UploadFile,
        municipality_id: str,
        doc_type: str
    ) -> tuple[str, int]:
        """
        Salva arquivo de upload no disco
        
        Args:
            file: Arquivo enviado
            municipality_id: ID do município
            doc_type: Tipo do documento (LOA ou LDO)
            
        Returns:
            Tupla (file_path, file_size_bytes)
        """
        # Gerar nome único para o arquivo
        file_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_filename = Path(file.filename).name
        
        # Criar subdiretório para o município
        municipality_dir = self.upload_dir / municipality_id
        municipality_dir.mkdir(parents=True, exist_ok=True)
        
        # Nome do arquivo: {tipo}_{timestamp}_{uuid}_{original}.pdf
        safe_filename = f"{doc_type}_{timestamp}_{file_id}_{original_filename}"
        file_path = municipality_dir / safe_filename
        
        # Salvar arquivo
        try:
            file.file.seek(0)
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_size = file_path.stat().st_size
            
            logger.info(
                "File saved successfully",
                file_path=str(file_path),
                size_mb=file_size / (1024 * 1024),
                municipality_id=municipality_id,
                doc_type=doc_type
            )
            
            return str(file_path), file_size
            
        except Exception as e:
            logger.error(
                "Failed to save file",
                error=str(e),
                file_path=str(file_path)
            )
            # Tentar remover arquivo parcial
            if file_path.exists():
                file_path.unlink()
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """
        Deleta arquivo do disco
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se deletado com sucesso, False caso contrário
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info("File deleted", file_path=file_path)
                return True
            else:
                logger.warning("File not found for deletion", file_path=file_path)
                return False
        except Exception as e:
            logger.error("Failed to delete file", error=str(e), file_path=file_path)
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Obtém informações sobre um arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do arquivo
        """
        path = Path(file_path)
        
        if not path.exists():
            return {
                "exists": False,
                "path": file_path
            }
        
        stat = path.stat()
        
        return {
            "exists": True,
            "path": file_path,
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }
    
    def estimate_processing_time(self, file_size_bytes: int) -> int:
        """
        Estima tempo de processamento em minutos baseado no tamanho
        
        Args:
            file_size_bytes: Tamanho do arquivo em bytes
            
        Returns:
            Tempo estimado em minutos
        """
        # Estimativa: ~1MB por minuto de processamento
        # (parsing + chunking + embeddings)
        size_mb = file_size_bytes / (1024 * 1024)
        
        # Mínimo 2 minutos, máximo 30 minutos
        estimated_minutes = max(2, min(30, int(size_mb * 1.5)))
        
        return estimated_minutes

