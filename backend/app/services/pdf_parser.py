"""
Parser de PDFs - Extrai texto de documentos LOA e LDO
"""

import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional
import structlog
import re

logger = structlog.get_logger()


class PDFParser:
    """
    Parser de PDFs com múltiplas estratégias de extração
    """
    
    def __init__(self):
        self.logger = logger
    
    def extract_text(self, pdf_path: str) -> Dict[str, any]:
        """
        Extrai texto do PDF usando PyMuPDF como método principal
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Dicionário com texto extraído e metadados
        """
        self.logger.info("Starting PDF text extraction", pdf_path=pdf_path)
        
        try:
            # Tentar com PyMuPDF primeiro (mais rápido)
            result = self._extract_with_pymupdf(pdf_path)
            
            # Se resultado for muito pequeno, tentar pdfplumber (melhor para tabelas)
            if len(result["text"]) < 500:
                self.logger.warning(
                    "PyMuPDF extracted little text, trying pdfplumber",
                    chars_extracted=len(result["text"])
                )
                result = self._extract_with_pdfplumber(pdf_path)
            
            self.logger.info(
                "PDF text extraction completed",
                pages=result["total_pages"],
                chars=len(result["text"]),
                method=result["method"]
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to extract text from PDF", error=str(e))
            raise
    
    def _extract_with_pymupdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Extrai texto usando PyMuPDF (fitz)
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com dados extraídos
        """
        doc = fitz.open(pdf_path)
        
        text_parts = []
        metadata = {
            "method": "pymupdf",
            "total_pages": len(doc),
            "pages_data": []
        }
        
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            
            # Limpar texto
            page_text = self._clean_text(page_text)
            
            if page_text.strip():
                text_parts.append(page_text)
                metadata["pages_data"].append({
                    "page": page_num,
                    "chars": len(page_text)
                })
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        metadata["text"] = full_text
        
        return metadata
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Dict[str, any]:
        """
        Extrai texto usando pdfplumber (melhor para tabelas)
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com dados extraídos
        """
        text_parts = []
        metadata = {
            "method": "pdfplumber",
            "total_pages": 0,
            "pages_data": []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata["total_pages"] = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extrair texto
                page_text = page.extract_text() or ""
                
                # Tentar extrair tabelas
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        table_text = self._table_to_text(table)
                        page_text += f"\n\n{table_text}"
                
                # Limpar texto
                page_text = self._clean_text(page_text)
                
                if page_text.strip():
                    text_parts.append(page_text)
                    metadata["pages_data"].append({
                        "page": page_num,
                        "chars": len(page_text),
                        "tables": len(tables)
                    })
        
        full_text = "\n\n".join(text_parts)
        metadata["text"] = full_text
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """
        Limpa e normaliza texto extraído
        
        Args:
            text: Texto bruto
            
        Returns:
            Texto limpo
        """
        if not text:
            return ""
        
        # Remover múltiplos espaços
        text = re.sub(r' +', ' ', text)
        
        # Remover múltiplas quebras de linha (mantém max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remover espaços no início/fim de linhas
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Normalizar caracteres especiais comuns em PDFs
        text = text.replace('\x00', '')
        text = text.replace('\uf0b7', '•')  # Bullet points
        
        return text.strip()
    
    def _table_to_text(self, table: List[List]) -> str:
        """
        Converte tabela para texto formatado
        
        Args:
            table: Tabela extraída (lista de listas)
            
        Returns:
            Texto formatado da tabela
        """
        if not table:
            return ""
        
        lines = []
        for row in table:
            if row:
                # Filtrar células None ou vazias
                cells = [str(cell).strip() if cell else "" for cell in row]
                line = " | ".join(cells)
                if line.strip():
                    lines.append(line)
        
        return "\n".join(lines)
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, any]:
        """
        Extrai metadados do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com metadados
        """
        try:
            doc = fitz.open(pdf_path)
            
            metadata = {
                "pages": len(doc),
                "file_size": Path(pdf_path).stat().st_size,
                "pdf_metadata": doc.metadata or {}
            }
            
            doc.close()
            
            return metadata
            
        except Exception as e:
            self.logger.error("Failed to extract PDF metadata", error=str(e))
            return {
                "pages": 0,
                "file_size": 0,
                "pdf_metadata": {},
                "error": str(e)
            }
    
    def validate_pdf_readability(self, pdf_path: str) -> bool:
        """
        Valida se o PDF pode ser lido
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            True se legível, False caso contrário
        """
        try:
            doc = fitz.open(pdf_path)
            
            # Tentar ler primeira página
            if len(doc) > 0:
                first_page = doc[0]
                text = first_page.get_text("text")
                doc.close()
                
                # Se tem pelo menos 10 caracteres, considera legível
                return len(text.strip()) >= 10
            
            doc.close()
            return False
            
        except Exception as e:
            self.logger.error("PDF validation failed", error=str(e))
            return False

