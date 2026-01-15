"""
Validador de arquivos para upload
"""

from fastapi import UploadFile, HTTPException, status
from pathlib import Path
import magic  # python-magic para detectar tipo de arquivo
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class FileValidator:
    """
    Validador de arquivos de upload
    """
    
    @staticmethod
    async def validate_pdf(file: UploadFile) -> None:
        """
        Valida se o arquivo é um PDF válido
        
        Args:
            file: Arquivo enviado
            
        Raises:
            HTTPException: Se arquivo for inválido
        """
        # 1. Validar extensão
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome do arquivo não fornecido"
            )
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato de arquivo não permitido. Apenas PDFs são aceitos. "
                       f"Extensão fornecida: {file_extension}"
            )
        
        # 2. Validar tamanho do arquivo
        # Ler primeiros bytes para verificar tamanho
        file.file.seek(0, 2)  # Ir para o final do arquivo
        file_size = file.file.tell()
        file.file.seek(0)  # Voltar ao início
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo está vazio"
            )
        
        if file_size > settings.max_upload_size_bytes:
            size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo muito grande ({size_mb:.2f} MB). "
                       f"Tamanho máximo permitido: {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        
        # 3. Validar magic number (primeiros bytes do arquivo)
        # PDF começa com %PDF
        file.file.seek(0)
        header = file.file.read(5)
        file.file.seek(0)
        
        if not header.startswith(b'%PDF'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo não é um PDF válido (magic number inválido)"
            )
        
        logger.info(
            "File validation passed",
            filename=file.filename,
            size_mb=file_size / (1024 * 1024)
        )
    
    @staticmethod
    def validate_document_type(doc_type: str) -> None:
        """
        Valida se o tipo de documento é válido (LOA ou LDO)
        
        Args:
            doc_type: Tipo do documento
            
        Raises:
            HTTPException: Se tipo for inválido
        """
        valid_types = ["LOA", "LDO"]
        if doc_type.upper() not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de documento inválido. Use 'LOA' ou 'LDO'. "
                       f"Fornecido: {doc_type}"
            )
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Remove caracteres perigosos do nome do arquivo
        
        Args:
            filename: Nome original do arquivo
            
        Returns:
            Nome sanitizado
        """
        # Remover path separators
        filename = filename.replace("/", "_").replace("\\", "_")
        
        # Remover caracteres especiais perigosos
        dangerous_chars = ['..', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limitar tamanho
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1)
            filename = name[:250] + '.' + ext
        
        return filename

