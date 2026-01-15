"""
Schemas de Metadados Estruturados para ChromaDB
================================================

Define estruturas de metadados para cada tipo de documento,
permitindo queries estruturadas e filtros precisos.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import re
import structlog

logger = structlog.get_logger()


class MetadataExtractor:
    """
    Extrai metadados estruturados de documentos brutos
    """
    
    @staticmethod
    def extract_from_portal_csv(row: Dict[str, Any], resource_name: str) -> Dict[str, Any]:
        """
        Extrai metadados estruturados de uma linha CSV do Portal da Transparência
        
        Args:
            row: Linha do CSV (dict)
            resource_name: Nome do resource
            
        Returns:
            Dict com metadados estruturados e indexáveis
        """
        try:
            # Identificar tipo de documento pelo resource_name
            doc_type = MetadataExtractor._identify_doc_type(resource_name, row)
            
            # Extração base (comum a todos)
            base_metadata = {
                "doc_type": doc_type,
                "source": "portal_transparency",
                "resource_name": resource_name,
            }
            
            # Extração específica por tipo
            if doc_type == "licitacao":
                return {**base_metadata, **MetadataExtractor._extract_licitacao_metadata(row)}
            elif doc_type == "contrato":
                return {**base_metadata, **MetadataExtractor._extract_contrato_metadata(row)}
            elif doc_type == "empenho":
                return {**base_metadata, **MetadataExtractor._extract_empenho_metadata(row)}
            else:
                # Genérico
                return {**base_metadata, **MetadataExtractor._extract_generic_metadata(row)}
                
        except Exception as e:
            logger.error(f"Erro ao extrair metadados: {e}", row=row)
            return {
                "doc_type": "unknown",
                "source": "portal_transparency",
                "error": str(e)
            }
    
    @staticmethod
    def _identify_doc_type(resource_name: str, row: Dict[str, Any]) -> str:
        """
        Identifica o tipo de documento
        """
        resource_lower = resource_name.lower()
        
        if "resultado" in resource_lower or "licitac" in resource_lower:
            return "licitacao"
        elif "contrato" in resource_lower:
            return "contrato"
        elif "empenho" in resource_lower:
            return "empenho"
        elif "despesa" in resource_lower:
            return "despesa"
        elif "receita" in resource_lower:
            return "receita"
        else:
            return "generic"
    
    @staticmethod
    def _extract_licitacao_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai metadados específicos de licitações
        """
        metadata = {}
        
        # ORIGEM (órgão) - CAMPO CRÍTICO
        origem = row.get("ORIGEM", row.get("origem", "")).strip()
        if origem:
            metadata["origem"] = origem.upper()
        
        # EDITAL N° - CAMPO CRÍTICO
        edital = row.get("EDITAL N", row.get("EDITAL_N", row.get("edital_n", "")))
        if edital:
            # Extrair apenas números
            edital_num = re.sub(r'\D', '', str(edital))
            if edital_num:
                metadata["edital"] = int(edital_num)
                metadata["edital_str"] = str(edital)
        
        # MODALIDADE
        modalidade = row.get("MODALIDADE", row.get("modalidade", "")).strip()
        if modalidade:
            metadata["modalidade"] = modalidade.upper()
        
        # PROCESSO ADMINISTRATIVO
        processo = row.get("PROCESSO ADM.", row.get("processo_adm", "")).strip()
        if processo:
            metadata["processo"] = processo
        
        # Número do processo licitatório
        numero = row.get("N", row.get("numero", "")).strip()
        if numero:
            metadata["numero_processo"] = numero
        
        # DATA DE ABERTURA
        data_abertura = row.get("DATA DE ABERTURA DAS PROPOSTAS", 
                                 row.get("data_abertura", ""))
        if data_abertura:
            metadata["data_abertura"] = str(data_abertura)
            # Tentar parsear para timestamp
            try:
                if "/" in str(data_abertura):
                    parts = str(data_abertura).split("/")
                    if len(parts) == 3:
                        # dd/mm/yyyy
                        dia, mes, ano = parts
                        metadata["data_abertura_timestamp"] = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                        metadata["ano"] = int(ano)
                        metadata["mes"] = int(mes)
            except:
                pass
        
        # REGISTRO DE PREÇOS
        registro = row.get("REGISTRO DE PREOS", row.get("registro_precos", "")).strip()
        if registro:
            metadata["registro_precos"] = registro.upper()
        
        # OBJETO (extrair keywords)
        objeto = row.get("OBJETO DO ITEM", row.get("objeto", ""))
        if objeto:
            keywords = MetadataExtractor._extract_keywords(str(objeto))
            metadata["keywords"] = ",".join(keywords[:10])  # Top 10 keywords
        
        # VALORES (se houver)
        for valor_field in ["VALOR TOTAL", "valor_total", "VALOR", "valor"]:
            if valor_field in row:
                try:
                    valor = MetadataExtractor._parse_valor(row[valor_field])
                    if valor:
                        metadata["valor_total"] = float(valor)
                        break
                except:
                    pass
        
        return metadata
    
    @staticmethod
    def _extract_contrato_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai metadados de contratos
        """
        metadata = {}
        
        # Órgão
        for field in ["ORIGEM", "origem", "ORGAO", "orgao"]:
            if field in row:
                metadata["origem"] = str(row[field]).strip().upper()
                break
        
        # Número do contrato
        for field in ["NUMERO_CONTRATO", "numero_contrato", "CONTRATO", "contrato"]:
            if field in row:
                metadata["numero_contrato"] = str(row[field]).strip()
                break
        
        # Fornecedor
        for field in ["FORNECEDOR", "fornecedor", "CONTRATADA", "contratada"]:
            if field in row:
                metadata["fornecedor"] = str(row[field]).strip()
                break
        
        # Data
        for field in ["DATA", "data", "DATA_ASSINATURA", "data_assinatura"]:
            if field in row:
                metadata["data"] = str(row[field]).strip()
                break
        
        # Valor
        for field in ["VALOR", "valor", "VALOR_TOTAL", "valor_total"]:
            if field in row:
                try:
                    valor = MetadataExtractor._parse_valor(row[field])
                    if valor:
                        metadata["valor_total"] = float(valor)
                        break
                except:
                    pass
        
        return metadata
    
    @staticmethod
    def _extract_empenho_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai metadados de empenhos
        """
        metadata = {}
        
        # Órgão
        for field in ["ORIGEM", "origem", "ORGAO", "orgao", "UNIDADE", "unidade"]:
            if field in row:
                metadata["origem"] = str(row[field]).strip().upper()
                break
        
        # Número do empenho
        for field in ["EMPENHO", "empenho", "NUMERO", "numero"]:
            if field in row:
                metadata["numero_empenho"] = str(row[field]).strip()
                break
        
        # Credor
        for field in ["CREDOR", "credor", "FORNECEDOR", "fornecedor"]:
            if field in row:
                metadata["credor"] = str(row[field]).strip()
                break
        
        # Valor
        for field in ["VALOR", "valor", "VALOR_EMPENHO", "valor_empenho"]:
            if field in row:
                try:
                    valor = MetadataExtractor._parse_valor(row[field])
                    if valor:
                        metadata["valor_total"] = float(valor)
                        break
                except:
                    pass
        
        return metadata
    
    @staticmethod
    def _extract_generic_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai metadados genéricos
        """
        metadata = {}
        
        # Tentar identificar órgão
        for field in ["ORIGEM", "origem", "ORGAO", "orgao", "UNIDADE", "unidade"]:
            if field in row:
                metadata["origem"] = str(row[field]).strip().upper()
                break
        
        # Tentar identificar data
        for field in ["DATA", "data", "ANO", "ano", "EXERCICIO", "exercicio"]:
            if field in row:
                metadata["data"] = str(row[field]).strip()
                break
        
        return metadata
    
    @staticmethod
    def _extract_keywords(text: str, min_length: int = 4) -> List[str]:
        """
        Extrai palavras-chave relevantes de um texto
        """
        # Stopwords em português
        stopwords = {
            "a", "o", "e", "de", "da", "do", "para", "com", "em", "por", 
            "que", "no", "na", "os", "as", "dos", "das", "ao", "à",
            "um", "uma", "ser", "ter", "este", "esta", "esse", "essa"
        }
        
        # Tokenizar e limpar
        words = re.findall(r'\b[a-záàâãéèêíïóôõöúçñ]+\b', text.lower())
        
        # Filtrar stopwords e palavras curtas
        keywords = [w for w in words if w not in stopwords and len(w) >= min_length]
        
        # Remover duplicatas preservando ordem
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords
    
    @staticmethod
    def _parse_valor(valor_str: Any) -> Optional[float]:
        """
        Parseia string de valor monetário para float
        
        Formatos aceitos:
        - R$ 1.234,56
        - 1234.56
        - 1.234,56
        """
        if not valor_str:
            return None
        
        valor_str = str(valor_str).strip()
        
        # Remover "R$" e espaços
        valor_str = valor_str.replace("R$", "").replace(" ", "")
        
        # Se tiver vírgula e ponto, assumir formato brasileiro
        if "," in valor_str and "." in valor_str:
            valor_str = valor_str.replace(".", "").replace(",", ".")
        elif "," in valor_str:
            # Apenas vírgula, trocar por ponto
            valor_str = valor_str.replace(",", ".")
        
        try:
            return float(valor_str)
        except:
            return None


class MetadataValidator:
    """
    Valida se metadados estão completos e corretos
    """
    
    REQUIRED_FIELDS = {
        "licitacao": ["origem", "edital", "modalidade"],
        "contrato": ["origem", "numero_contrato"],
        "empenho": ["origem", "numero_empenho"],
    }
    
    @staticmethod
    def validate(metadata: Dict[str, Any]) -> bool:
        """
        Valida se metadados obrigatórios estão presentes
        """
        doc_type = metadata.get("doc_type", "generic")
        
        if doc_type not in MetadataValidator.REQUIRED_FIELDS:
            return True  # Genéricos sempre passam
        
        required = MetadataValidator.REQUIRED_FIELDS[doc_type]
        
        for field in required:
            if field not in metadata or not metadata[field]:
                logger.warning(f"Campo obrigatório ausente: {field}", metadata=metadata)
                return False
        
        return True
    
    @staticmethod
    def get_quality_score(metadata: Dict[str, Any]) -> float:
        """
        Retorna score de qualidade dos metadados (0.0 a 1.0)
        """
        score = 0.0
        total_checks = 0
        
        # Campos importantes
        important_fields = [
            "origem", "edital", "modalidade", "data_abertura",
            "valor_total", "keywords", "processo"
        ]
        
        for field in important_fields:
            total_checks += 1
            if field in metadata and metadata[field]:
                score += 1.0
        
        return score / total_checks if total_checks > 0 else 0.0

