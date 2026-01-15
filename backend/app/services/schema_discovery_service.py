"""
Serviço para descoberta automática de schemas
FASE 2: Elasticidade de nomes de colunas
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session
from io import StringIO
import pandas as pd
from unidecode import unidecode

from app.models.file_schema import FileSchema, SchemaAlias
from app.models.raw_file import RawFile

logger = logging.getLogger(__name__)


class SchemaDiscoveryService:
    """
    Descobre automaticamente a estrutura de arquivos
    e gera aliases semânticos inteligentes
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def discover_schema(
        self,
        raw_file: RawFile,
        content: str,
        delimiter: str = ";"
    ) -> FileSchema:
        """
        Descobre schema de um arquivo CSV
        
        Args:
            raw_file: Objeto RawFile
            content: Conteúdo do arquivo
            delimiter: Delimitador do CSV
        
        Returns:
            FileSchema criado
        """
        try:
            logger.info(f"🔍 Discovering schema: {raw_file.filename}")
            
            # 1. Parse CSV com pandas
            df = pd.read_csv(StringIO(content), delimiter=delimiter, encoding='utf-8')
            
            # 2. Descobrir informações de cada coluna
            columns_info = []
            
            for col_name in df.columns:
                col_info = self._discover_column_info(col_name, df[col_name])
                columns_info.append(col_info)
                
                logger.debug(
                    f"   Column: {col_name} → {col_info['data_type']} "
                    f"({len(col_info['semantic_aliases'])} aliases)"
                )
            
            # 3. Criar FileSchema
            file_schema = FileSchema(
                raw_file_id=raw_file.id,
                filename=raw_file.filename,
                file_format="CSV",
                columns_info=columns_info,
                total_rows=len(df),
                total_columns=len(df.columns),
                discovery_metadata={
                    "delimiter": delimiter,
                    "encoding": "utf-8",
                    "has_header": True,
                    "discovery_method": "pandas",
                    "discovery_version": "2.0"
                },
                status="active"
            )
            
            self.db.add(file_schema)
            self.db.flush()
            
            # 4. Criar índice de aliases (para busca rápida)
            await self._create_alias_index(file_schema)
            
            self.db.commit()
            
            logger.info(
                f"✅ Schema discovered: {raw_file.filename} "
                f"({len(columns_info)} columns, {len(df)} rows)"
            )
            
            return file_schema
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error discovering schema: {e}")
            raise
    
    def _discover_column_info(
        self,
        column_name: str,
        column_data: pd.Series
    ) -> Dict[str, Any]:
        """
        Descobre informações de uma coluna
        
        Args:
            column_name: Nome da coluna
            column_data: Dados da coluna (pandas Series)
        
        Returns:
            Dict com informações da coluna
        """
        # Nome normalizado
        normalized_name = self._normalize_column_name(column_name)
        
        # Display name (limpo)
        display_name = self._clean_display_name(column_name)
        
        # Tipo de dados
        data_type = self._infer_data_type(column_data)
        
        # Valores de exemplo (primeiros 5 não-nulos)
        sample_values = column_data.dropna().head(5).tolist()
        
        # Para categorias, pegar valores únicos (se <= 50)
        unique_values = None
        unique_count = column_data.nunique()
        if unique_count <= 50:
            unique_values = column_data.dropna().unique().tolist()
        
        # Assinatura de conteúdo (inferir significado)
        content_signature = self._analyze_content_signature(column_data)
        
        # CRÍTICO: Gerar aliases semânticos
        semantic_aliases = self._generate_semantic_aliases(
            column_name,
            column_data,
            content_signature
        )
        
        return {
            "original_name": column_name,
            "normalized_name": normalized_name,
            "display_name": display_name,
            "semantic_aliases": semantic_aliases,
            "data_type": data_type,
            "sample_values": sample_values,
            "unique_values": unique_values,
            "content_signature": content_signature,
            "null_count": int(column_data.isna().sum()),
            "unique_count": unique_count
        }
    
    def _normalize_column_name(self, column_name: str) -> str:
        """
        Normaliza nome da coluna
        
        "EDITAL N°" → "edital_n"
        """
        # Remove acentos
        normalized = unidecode(column_name)
        
        # Lowercase
        normalized = normalized.lower()
        
        # Remove caracteres especiais, mantém apenas letras, números e espaços
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Substitui espaços por underscore
        normalized = re.sub(r'\s+', '_', normalized)
        
        # Remove underscores duplicados
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove underscores no início e fim
        normalized = normalized.strip('_')
        
        return normalized
    
    def _clean_display_name(self, column_name: str) -> str:
        """
        Limpa nome para display
        
        "EDITAL N°" → "Edital N"
        """
        # Remove caracteres especiais problemáticos
        cleaned = re.sub(r'[°º]', '', column_name)
        
        # Remove espaços extras
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Capitalize primeira letra de cada palavra
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())
        
        return cleaned
    
    def _infer_data_type(self, column_data: pd.Series) -> str:
        """
        Infere tipo de dados da coluna
        """
        # Tentar converter para numérico
        try:
            numeric_data = pd.to_numeric(column_data.dropna(), errors='coerce')
            if numeric_data.notna().sum() > len(column_data.dropna()) * 0.8:
                # Se 80%+ são numéricos
                if (numeric_data % 1 == 0).all():
                    return "integer"
                else:
                    return "float"
        except:
            pass
        
        # Tentar converter para data
        try:
            date_data = pd.to_datetime(column_data.dropna(), errors='coerce', dayfirst=True)
            if date_data.notna().sum() > len(column_data.dropna()) * 0.8:
                return "date"
        except:
            pass
        
        # Se tem poucos valores únicos, é categoria
        unique_ratio = column_data.nunique() / len(column_data.dropna())
        if unique_ratio < 0.05:  # Menos de 5% de valores únicos
            return "category"
        
        return "text"
    
    def _analyze_content_signature(self, column_data: pd.Series) -> str:
        """
        Analisa CONTEÚDO da coluna para inferir significado
        """
        # Pegar amostra não-nula
        sample = column_data.dropna().head(10)
        
        if len(sample) == 0:
            return "unknown"
        
        # Testar se são números sequenciais (IDs, editais)
        try:
            numeric_sample = pd.to_numeric(sample, errors='coerce')
            if numeric_sample.notna().all():
                if numeric_sample.is_monotonic_increasing:
                    return "numeric_sequential"
                return "numeric"
        except:
            pass
        
        # Converter para string para análise
        sample_str = ' '.join(sample.astype(str).tolist()).upper()
        
        # Testar se são nomes de organizações
        org_keywords = ['SEINF', 'SME', 'SMS', 'SECRETARIA', 'INSTITUTO', 'URBFOR', 'IJF']
        if any(org in sample_str for org in org_keywords):
            return "organization_name"
        
        # Testar se são modalidades de licitação
        modal_keywords = ['PREGAO', 'CONCORRENCIA', 'DISPENSA', 'INEXIGIBILIDADE', 'PE', 'CE']
        if any(modal in sample_str for modal in modal_keywords):
            return "bidding_modality"
        
        # Testar se são valores monetários
        if any(char in sample_str for char in ['R$', 'RS']):
            return "money"
        
        # Testar se contém números com vírgulas (valores)
        if re.search(r'\d+[,\.]\d+', sample_str):
            return "numeric_formatted"
        
        # Testar se são datas
        if any(char in sample_str for char in ['/', '-']) and re.search(r'\d{1,4}', sample_str):
            return "date"
        
        return "text"
    
    def _generate_semantic_aliases(
        self,
        column_name: str,
        column_data: pd.Series,
        content_signature: str
    ) -> List[str]:
        """
        Gera aliases semânticos inteligentes
        
        "EDITAL N°" → ["edital", "numero_edital", "edital_numero", 
                       "n_edital", "edital_n", "numero", "id_edital"]
        """
        aliases: Set[str] = set()
        
        # 1. Normalizar (remove acentos, símbolos)
        normalized = unidecode(column_name).lower()
        normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
        aliases.add(normalized.strip())
        
        # 2. Versões sem espaços
        aliases.add(normalized.replace(' ', '_'))
        aliases.add(normalized.replace(' ', ''))
        
        # 3. Palavras individuais (> 2 caracteres)
        words = re.findall(r'\w+', normalized)
        for word in words:
            if len(word) > 2:
                aliases.add(word)
        
        # 4. Combinações de palavras
        if len(words) >= 2:
            # Primeira + última palavra
            aliases.add(f"{words[0]}_{words[-1]}")
            aliases.add(f"{words[0]}{words[-1]}")
            
            # Todas as palavras juntas
            aliases.add("_".join(words))
            aliases.add("".join(words))
        
        # 5. CRÍTICO: Aliases baseados no CONTEÚDO
        content_aliases = self._generate_content_based_aliases(
            column_name,
            content_signature
        )
        aliases.update(content_aliases)
        
        # 6. Remover aliases muito curtos (< 2 chars) ou muito longos (> 50 chars)
        aliases = {a for a in aliases if 2 <= len(a) <= 50}
        
        return sorted(list(aliases))
    
    def _generate_content_based_aliases(
        self,
        column_name: str,
        content_signature: str
    ) -> Set[str]:
        """
        Gera aliases baseados no tipo de conteúdo
        """
        aliases = set()
        
        if content_signature == "numeric_sequential":
            aliases.update(["numero", "number", "id", "codigo", "code"])
        
        elif content_signature == "organization_name":
            aliases.update(["orgao", "origem", "secretaria", "entidade", 
                          "organization", "department", "entity"])
        
        elif content_signature == "bidding_modality":
            aliases.update(["modalidade", "modality", "tipo", "type"])
        
        elif content_signature == "money":
            aliases.update(["valor", "preco", "custo", "montante", 
                          "value", "price", "cost", "amount"])
        
        elif content_signature == "date":
            aliases.update(["data", "date", "quando", "when", "dia"])
        
        # Aliases específicos por palavras-chave no nome
        name_lower = column_name.lower()
        
        if any(kw in name_lower for kw in ['edital', 'licitacao']):
            aliases.update(["edital", "licitacao", "bidding", "tender"])
        
        if any(kw in name_lower for kw in ['processo', 'proc']):
            aliases.update(["processo", "process", "proc"])
        
        if any(kw in name_lower for kw in ['objeto', 'descricao']):
            aliases.update(["objeto", "descricao", "description", "object"])
        
        if any(kw in name_lower for kw in ['situacao', 'status']):
            aliases.update(["situacao", "status", "state"])
        
        return aliases
    
    async def _create_alias_index(self, file_schema: FileSchema):
        """
        Cria índice de busca reversa: alias → coluna
        Acelera busca de colunas
        """
        for col_info in file_schema.columns_info:
            original_name = col_info["original_name"]
            
            # 1. Alias exato (nome original)
            alias_entry = SchemaAlias(
                file_schema_id=file_schema.id,
                alias=original_name.lower(),
                original_column_name=original_name,
                match_type="exact",
                confidence="1.0"
            )
            self.db.add(alias_entry)
            
            # 2. Alias normalizado
            normalized = col_info["normalized_name"]
            alias_entry = SchemaAlias(
                file_schema_id=file_schema.id,
                alias=normalized.lower(),
                original_column_name=original_name,
                match_type="normalized",
                confidence="0.95"
            )
            self.db.add(alias_entry)
            
            # 3. Aliases semânticos
            for semantic_alias in col_info["semantic_aliases"]:
                alias_entry = SchemaAlias(
                    file_schema_id=file_schema.id,
                    alias=semantic_alias.lower(),
                    original_column_name=original_name,
                    match_type="semantic",
                    confidence="0.9"
                )
                self.db.add(alias_entry)
        
        logger.info(f"   Created alias index for {file_schema.filename}")
    
    def get_schema_by_raw_file(self, raw_file_id: str) -> Optional[FileSchema]:
        """Busca schema por raw_file_id"""
        return self.db.query(FileSchema).filter(
            FileSchema.raw_file_id == raw_file_id,
            FileSchema.status == "active"
        ).first()
    
    def get_all_active_schemas(self) -> List[FileSchema]:
        """Retorna todos os schemas ativos"""
        return self.db.query(FileSchema).filter(
            FileSchema.status == "active"
        ).order_by(FileSchema.discovered_at.desc()).all()
    
    def search_column_by_alias(
        self,
        alias: str,
        file_schema_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca colunas por alias
        
        Args:
            alias: Alias a buscar
            file_schema_id: Filtrar por schema específico (opcional)
        
        Returns:
            Lista de matches
        """
        alias_lower = alias.lower().strip()
        
        query = self.db.query(SchemaAlias).filter(
            SchemaAlias.alias == alias_lower
        )
        
        if file_schema_id:
            query = query.filter(SchemaAlias.file_schema_id == file_schema_id)
        
        results = query.all()
        
        matches = []
        for result in results:
            schema = self.db.query(FileSchema).filter(
                FileSchema.id == result.file_schema_id
            ).first()
            
            if schema:
                matches.append({
                    "file_schema_id": schema.id,
                    "filename": schema.filename,
                    "original_column_name": result.original_column_name,
                    "match_type": result.match_type,
                    "confidence": float(result.confidence)
                })
        
        # Ordenar por confiança
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        return matches

