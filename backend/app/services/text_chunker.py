"""
Text Chunker - Divide texto em chunks semânticos para vetorização
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TextChunker:
    """
    Divide texto em chunks inteligentes mantendo contexto semântico
    """
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.logger = logger
        
        # Criar splitter com LangChain
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=[
                "\n\n\n",  # Múltiplas quebras (seções)
                "\n\n",    # Parágrafos
                "\n",      # Linhas
                ". ",      # Sentenças
                ", ",      # Frases
                " ",       # Palavras
                ""         # Caracteres
            ]
        )
    
    def chunk_text(
        self,
        text: str,
        document_type: str = "LOA",
        metadata: Dict = None
    ) -> List[Dict[str, any]]:
        """
        Divide texto em chunks semânticos
        
        Args:
            text: Texto completo do documento
            document_type: Tipo do documento (LOA ou LDO)
            metadata: Metadados adicionais
            
        Returns:
            Lista de chunks com metadados
        """
        self.logger.info(
            "Starting text chunking",
            text_length=len(text),
            doc_type=document_type
        )
        
        if not text or not text.strip():
            self.logger.warning("Empty text provided for chunking")
            return []
        
        # Dividir texto
        text_chunks = self.splitter.split_text(text)
        
        # Criar chunks com metadados
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                "id": i,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "word_count": len(chunk_text.split()),
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "document_type": document_type,
                    **(metadata or {})
                }
            }
            chunks.append(chunk)
        
        self.logger.info(
            "Text chunking completed",
            total_chunks=len(chunks),
            avg_chunk_size=sum(c["char_count"] for c in chunks) / len(chunks) if chunks else 0
        )
        
        return chunks
    
    def chunk_by_sections(
        self,
        text: str,
        section_markers: List[str] = None
    ) -> List[Dict[str, any]]:
        """
        Divide texto por seções identificadas (para LOA/LDO estruturadas)
        
        Args:
            text: Texto completo
            section_markers: Marcadores de seção (ex: "CAPÍTULO", "ARTIGO")
            
        Returns:
            Lista de chunks por seção
        """
        if not section_markers:
            # Marcadores padrão para documentos orçamentários
            section_markers = [
                "CAPÍTULO",
                "TÍTULO",
                "SEÇÃO",
                "ARTIGO",
                "Art.",
                "§"
            ]
        
        self.logger.info("Chunking by sections", markers=section_markers)
        
        # Implementação simples: dividir por marcadores
        # TODO: Implementar parser mais sofisticado se necessário
        
        chunks = []
        current_section = []
        current_marker = None
        
        for line in text.split('\n'):
            # Verificar se linha começa com marcador de seção
            is_section_start = any(
                line.strip().upper().startswith(marker.upper())
                for marker in section_markers
            )
            
            if is_section_start and current_section:
                # Salvar seção anterior
                section_text = '\n'.join(current_section)
                if section_text.strip():
                    chunks.append({
                        "text": section_text,
                        "section_marker": current_marker,
                        "char_count": len(section_text)
                    })
                
                # Iniciar nova seção
                current_section = [line]
                current_marker = line.strip().split()[0] if line.strip() else None
            else:
                current_section.append(line)
        
        # Adicionar última seção
        if current_section:
            section_text = '\n'.join(current_section)
            if section_text.strip():
                chunks.append({
                    "text": section_text,
                    "section_marker": current_marker,
                    "char_count": len(section_text)
                })
        
        self.logger.info(
            "Section chunking completed",
            total_sections=len(chunks)
        )
        
        return chunks
    
    def optimize_chunks_for_embedding(
        self,
        chunks: List[Dict[str, any]],
        max_tokens: int = 8000  # Limite do Gemini
    ) -> List[Dict[str, any]]:
        """
        Otimiza chunks para não exceder limite de tokens do modelo
        
        Args:
            chunks: Lista de chunks
            max_tokens: Máximo de tokens permitido
            
        Returns:
            Lista de chunks otimizados
        """
        # Estimativa: ~4 caracteres por token
        max_chars = max_tokens * 4
        
        optimized_chunks = []
        
        for chunk in chunks:
            if chunk["char_count"] <= max_chars:
                optimized_chunks.append(chunk)
            else:
                # Dividir chunk muito grande
                text = chunk["text"]
                sub_chunks = self.splitter.split_text(text)
                
                for sub_text in sub_chunks:
                    optimized_chunks.append({
                        "text": sub_text,
                        "char_count": len(sub_text),
                        "metadata": {
                            **chunk.get("metadata", {}),
                            "split_from_large_chunk": True
                        }
                    })
        
        self.logger.info(
            "Chunks optimized",
            original_count=len(chunks),
            optimized_count=len(optimized_chunks)
        )
        
        return optimized_chunks
    
    def add_context_to_chunks(
        self,
        chunks: List[Dict[str, any]],
        document_metadata: Dict
    ) -> List[Dict[str, any]]:
        """
        Adiciona contexto dos metadados do documento a cada chunk
        
        Args:
            chunks: Lista de chunks
            document_metadata: Metadados do documento
            
        Returns:
            Chunks com contexto enriquecido
        """
        for chunk in chunks:
            # Adicionar prefixo de contexto ao texto
            context_prefix = self._build_context_prefix(document_metadata)
            chunk["text_with_context"] = f"{context_prefix}\n\n{chunk['text']}"
            
            # Mesclar metadados
            chunk["metadata"] = {
                **chunk.get("metadata", {}),
                **document_metadata
            }
        
        return chunks
    
    def _build_context_prefix(self, metadata: Dict) -> str:
        """
        Constrói prefixo de contexto para o chunk
        
        Args:
            metadata: Metadados do documento
            
        Returns:
            String com contexto
        """
        parts = []
        
        if "document_type" in metadata:
            parts.append(f"Documento: {metadata['document_type']}")
        
        if "municipality" in metadata:
            parts.append(f"Município: {metadata['municipality']}")
        
        if "state" in metadata:
            parts.append(f"Estado: {metadata['state']}")
        
        if "year" in metadata:
            parts.append(f"Ano: {metadata['year']}")
        
        return " | ".join(parts) if parts else ""

