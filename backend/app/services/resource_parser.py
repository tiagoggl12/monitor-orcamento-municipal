"""
Parser para recursos (TXT/CSV) do Portal da Transparência
"""
import csv
import io
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class ResourceParser:
    """
    Parser para arquivos TXT e CSV do Portal da Transparência
    """
    
    def parse_txt(self, content: str, resource_name: str) -> List[Dict[str, Any]]:
        """
        Parse de arquivo TXT (formato layout SEFIN)
        
        Args:
            content: Conteúdo do arquivo TXT
            resource_name: Nome do resource
            
        Returns:
            Lista de dicionários com os dados parseados
        """
        try:
            # Split em linhas
            lines = content.strip().split('\n')
            
            if not lines:
                return []
            
            # Estratégia: Tratar cada linha como um documento
            # O conteúdo completo será usado para busca semântica
            documents = []
            
            for idx, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Criar documento com a linha inteira
                doc = {
                    "line_number": idx + 1,
                    "content": line,
                    "resource_name": resource_name
                }
                
                # Tentar extrair campos estruturados se possível
                # (Isso pode ser melhorado com parsers específicos por tipo)
                if self._is_delimited(line):
                    fields = self._parse_delimited_line(line)
                    if fields:
                        doc["parsed_fields"] = fields
                
                documents.append(doc)
            
            logger.info(
                f"TXT parsed successfully",
                resource_name=resource_name,
                lines=len(lines),
                documents=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                f"Error parsing TXT",
                resource_name=resource_name,
                error=str(e)
            )
            raise
    
    def parse_csv(self, content: str, resource_name: str) -> List[Dict[str, Any]]:
        """
        Parse de arquivo CSV
        
        Args:
            content: Conteúdo do arquivo CSV
            resource_name: Nome do resource
            
        Returns:
            Lista de dicionários com os dados parseados
        """
        try:
            # Detectar delimitador
            delimiter = self._detect_csv_delimiter(content)
            
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            
            documents = []
            for idx, row in enumerate(reader):
                # Remover campos vazios
                row_cleaned = {k: v for k, v in row.items() if v and v.strip()}
                
                if row_cleaned:
                    # Criar conteúdo textual para busca semântica
                    content_text = " | ".join([f"{k}: {v}" for k, v in row_cleaned.items()])
                    
                    doc = {
                        "row_number": idx + 1,
                        "content": content_text,
                        "resource_name": resource_name,
                        "fields": row_cleaned
                    }
                    documents.append(doc)
            
            logger.info(
                f"CSV parsed successfully",
                resource_name=resource_name,
                rows=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                f"Error parsing CSV",
                resource_name=resource_name,
                error=str(e)
            )
            raise
    
    def _is_delimited(self, line: str) -> bool:
        """
        Verifica se a linha parece ter delimitadores
        """
        delimiters = [';', '|', '\t', ',']
        for delimiter in delimiters:
            if delimiter in line and line.count(delimiter) >= 2:
                return True
        return False
    
    def _parse_delimited_line(self, line: str) -> Dict[str, str]:
        """
        Tenta parsear uma linha delimitada
        """
        # Tentar diferentes delimitadores
        for delimiter in [';', '|', '\t', ',']:
            if delimiter in line:
                parts = line.split(delimiter)
                if len(parts) >= 2:
                    # Criar campos genéricos field_0, field_1, etc.
                    return {
                        f"field_{i}": part.strip()
                        for i, part in enumerate(parts)
                        if part.strip()
                    }
        return {}
    
    def _detect_csv_delimiter(self, content: str) -> str:
        """
        Detecta o delimitador do CSV
        """
        sample = content[:1000]  # Primeira linha
        
        delimiters = [';', ',', '\t', '|']
        counts = {d: sample.count(d) for d in delimiters}
        
        # Retorna o delimitador mais comum
        delimiter = max(counts, key=counts.get)
        
        # Se nenhum delimitador encontrado, usa vírgula
        if counts[delimiter] == 0:
            delimiter = ','
        
        logger.debug(f"CSV delimiter detected: '{delimiter}'")
        return delimiter

