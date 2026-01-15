"""
Serviço para mapeamento semântico de campos
FASE 2: Mapeia intenção do usuário para campos reais
"""

import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from app.models.file_schema import FileSchema, SchemaAlias
from app.services.schema_discovery_service import SchemaDiscoveryService

logger = logging.getLogger(__name__)


class FieldMapping:
    """Representa um mapeamento de query → campo"""
    
    def __init__(
        self,
        query_text: str,
        file_schema_id: str,
        filename: str,
        column_name: str,
        column_type: str,
        match_type: str,
        confidence: float,
        value: Any = None,
        operator: str = None
    ):
        self.query_text = query_text
        self.file_schema_id = file_schema_id
        self.filename = filename
        self.column_name = column_name
        self.column_type = column_type
        self.match_type = match_type
        self.confidence = confidence
        self.value = value
        self.operator = operator
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_text": self.query_text,
            "file_schema_id": self.file_schema_id,
            "filename": self.filename,
            "column_name": self.column_name,
            "column_type": self.column_type,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "value": self.value,
            "operator": self.operator
        }


class SemanticFieldMapper:
    """
    Mapeia queries do usuário para campos reais do schema
    
    Exemplo:
    - User: "edital 10367"
    - Mapper: {field: "EDITAL N°", value: 10367}
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.schema_service = SchemaDiscoveryService(db)
    
    def map_user_query_to_fields(
        self,
        user_query: str,
        file_schemas: Optional[List[FileSchema]] = None
    ) -> List[FieldMapping]:
        """
        Mapeia query do usuário para campos do schema
        
        Args:
            user_query: Query do usuário ("edital 10367 da SEINF")
            file_schemas: Schemas específicos (se None, usa todos)
        
        Returns:
            Lista de mapeamentos
        """
        if file_schemas is None:
            file_schemas = self.schema_service.get_all_active_schemas()
        
        if not file_schemas:
            logger.warning("No active schemas found")
            return []
        
        logger.info(f"🔍 Mapping query: '{user_query}'")
        logger.info(f"   Schemas disponíveis: {len(file_schemas)}")
        
        # 1. Extrair entidades da query
        entities = self._extract_entities(user_query, file_schemas)
        
        logger.info(f"   Entidades extraídas: {len(entities)}")
        for entity in entities:
            logger.debug(f"     - {entity['text']} ({entity['type']})")
        
        # 2. Para cada entidade, encontrar campo correspondente
        mappings = []
        
        for entity in entities:
            entity_mappings = self._map_entity_to_fields(
                entity,
                file_schemas,
                user_query
            )
            mappings.extend(entity_mappings)
        
        # 3. Ranquear por confiança
        mappings.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"✅ Encontrados {len(mappings)} mapeamentos")
        
        return mappings
    
    def _extract_entities(
        self,
        query: str,
        file_schemas: List[FileSchema]
    ) -> List[Dict[str, Any]]:
        """
        Extrai entidades da query
        
        "edital 10367 da SEINF" → [
            {"text": "edital", "type": "field_name", "position": 0},
            {"text": "10367", "type": "number", "position": 7},
            {"text": "SEINF", "type": "organization", "position": 16}
        ]
        """
        entities = []
        
        # 1. Números (possíveis valores de campos)
        for match in re.finditer(r'\b\d+\b', query):
            entities.append({
                "text": match.group(),
                "type": "number",
                "position": match.start(),
                "value": int(match.group())
            })
        
        # 2. Organizações conhecidas (extrair de schemas)
        org_values = self._extract_known_values_from_schemas(
            file_schemas,
            ["organization_name", "category"]
        )
        
        for org in org_values:
            if org.upper() in query.upper():
                pos = query.upper().index(org.upper())
                entities.append({
                    "text": org,
                    "type": "organization",
                    "position": pos,
                    "value": org
                })
        
        # 3. Palavras-chave de campos (baseado em aliases dos schemas)
        field_keywords = self._extract_field_keywords_from_schemas(file_schemas)
        
        for keyword in field_keywords:
            if keyword.lower() in query.lower():
                pos = query.lower().index(keyword.lower())
                entities.append({
                    "text": keyword,
                    "type": "field_name",
                    "position": pos
                })
        
        # 4. Remover duplicatas (mesma posição)
        seen_positions = set()
        unique_entities = []
        
        for entity in sorted(entities, key=lambda x: x["position"]):
            if entity["position"] not in seen_positions:
                unique_entities.append(entity)
                seen_positions.add(entity["position"])
        
        return unique_entities
    
    def _extract_known_values_from_schemas(
        self,
        file_schemas: List[FileSchema],
        content_signatures: List[str]
    ) -> List[str]:
        """
        Extrai valores conhecidos dos schemas
        (Ex: organizações, modalidades)
        """
        known_values = set()
        
        for schema in file_schemas:
            for col_info in schema.columns_info:
                if col_info.get("content_signature") in content_signatures:
                    unique_values = col_info.get("unique_values", [])
                    if unique_values:
                        known_values.update(unique_values)
        
        return list(known_values)
    
    def _extract_field_keywords_from_schemas(
        self,
        file_schemas: List[FileSchema]
    ) -> List[str]:
        """
        Extrai palavras-chave de campos dos schemas
        """
        keywords = set()
        
        for schema in file_schemas:
            for col_info in schema.columns_info:
                # Nome normalizado
                keywords.add(col_info["normalized_name"])
                
                # Aliases semânticos (top 5)
                aliases = col_info.get("semantic_aliases", [])
                keywords.update(aliases[:5])
        
        # Filtrar keywords muito curtos
        keywords = {kw for kw in keywords if len(kw) >= 3}
        
        return list(keywords)
    
    def _map_entity_to_fields(
        self,
        entity: Dict[str, Any],
        file_schemas: List[FileSchema],
        full_query: str
    ) -> List[FieldMapping]:
        """
        Mapeia uma entidade para campos dos schemas
        """
        mappings = []
        entity_text = entity["text"].lower().strip()
        entity_type = entity["type"]
        
        if entity_type == "field_name":
            # Buscar campo por nome/alias
            mappings.extend(
                self._map_field_name(entity_text, file_schemas)
            )
        
        elif entity_type == "number":
            # Buscar colunas numéricas que possam conter esse valor
            mappings.extend(
                self._map_number_value(
                    entity["value"],
                    file_schemas,
                    full_query
                )
            )
        
        elif entity_type == "organization":
            # Buscar colunas de organização
            mappings.extend(
                self._map_categorical_value(
                    entity["value"],
                    file_schemas,
                    "organization_name"
                )
            )
        
        return mappings
    
    def _map_field_name(
        self,
        field_text: str,
        file_schemas: List[FileSchema]
    ) -> List[FieldMapping]:
        """
        Mapeia nome de campo para colunas reais
        """
        mappings = []
        
        for schema in file_schemas:
            # Buscar por alias
            col_info = schema.get_column_by_alias(field_text)
            
            if col_info:
                mapping = FieldMapping(
                    query_text=field_text,
                    file_schema_id=schema.id,
                    filename=schema.filename,
                    column_name=col_info["original_name"],
                    column_type=col_info["data_type"],
                    match_type="exact_alias",
                    confidence=1.0
                )
                mappings.append(mapping)
            else:
                # Busca fuzzy
                fuzzy_matches = self._fuzzy_search_column(
                    field_text,
                    schema
                )
                mappings.extend(fuzzy_matches)
        
        return mappings
    
    def _map_number_value(
        self,
        number_value: int,
        file_schemas: List[FileSchema],
        context_query: str
    ) -> List[FieldMapping]:
        """
        Mapeia valor numérico para colunas numéricas
        """
        mappings = []
        
        for schema in file_schemas:
            # Buscar colunas numéricas
            numeric_columns = [
                col for col in schema.columns_info
                if col["data_type"] in ["integer", "float"]
            ]
            
            for col in numeric_columns:
                # Se é uma coluna sequencial (edital, processo), alta confiança
                if col["content_signature"] == "numeric_sequential":
                    confidence = 0.9
                else:
                    confidence = 0.7
                
                mapping = FieldMapping(
                    query_text=str(number_value),
                    file_schema_id=schema.id,
                    filename=schema.filename,
                    column_name=col["original_name"],
                    column_type=col["data_type"],
                    match_type="inferred_numeric",
                    confidence=confidence,
                    value=number_value,
                    operator="equals"
                )
                mappings.append(mapping)
        
        return mappings
    
    def _map_categorical_value(
        self,
        value: str,
        file_schemas: List[FileSchema],
        content_signature: str
    ) -> List[FieldMapping]:
        """
        Mapeia valor categórico para colunas
        """
        mappings = []
        
        for schema in file_schemas:
            for col in schema.columns_info:
                if col.get("content_signature") == content_signature:
                    # Verificar se valor existe nos unique_values
                    unique_values = col.get("unique_values", [])
                    
                    if value.upper() in [v.upper() for v in unique_values]:
                        mapping = FieldMapping(
                            query_text=value,
                            file_schema_id=schema.id,
                            filename=schema.filename,
                            column_name=col["original_name"],
                            column_type=col["data_type"],
                            match_type="exact_value",
                            confidence=1.0,
                            value=value,
                            operator="equals"
                        )
                        mappings.append(mapping)
        
        return mappings
    
    def _fuzzy_search_column(
        self,
        search_text: str,
        schema: FileSchema,
        threshold: float = 0.6
    ) -> List[FieldMapping]:
        """
        Busca fuzzy para typos e variações
        """
        mappings = []
        
        for col in schema.columns_info:
            # Testar similaridade com nome normalizado
            similarity = SequenceMatcher(
                None,
                search_text.lower(),
                col["normalized_name"].lower()
            ).ratio()
            
            if similarity >= threshold:
                mapping = FieldMapping(
                    query_text=search_text,
                    file_schema_id=schema.id,
                    filename=schema.filename,
                    column_name=col["original_name"],
                    column_type=col["data_type"],
                    match_type="fuzzy",
                    confidence=similarity * 0.8  # Penalizar fuzzy match
                )
                mappings.append(mapping)
            
            # Testar similaridade com aliases
            for alias in col.get("semantic_aliases", []):
                similarity = SequenceMatcher(
                    None,
                    search_text.lower(),
                    alias.lower()
                ).ratio()
                
                if similarity >= threshold:
                    mapping = FieldMapping(
                        query_text=search_text,
                        file_schema_id=schema.id,
                        filename=schema.filename,
                        column_name=col["original_name"],
                        column_type=col["data_type"],
                        match_type="fuzzy_alias",
                        confidence=similarity * 0.85
                    )
                    mappings.append(mapping)
        
        return mappings
    
    def format_mappings_for_llm(
        self,
        mappings: List[FieldMapping],
        top_n: int = 10
    ) -> str:
        """
        Formata mapeamentos de forma legível para LLM
        """
        if not mappings:
            return "Nenhum mapeamento encontrado."
        
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"MAPEAMENTOS ENCONTRADOS ({len(mappings)} total, mostrando top {top_n}):",
            ""
        ]
        
        for i, mapping in enumerate(mappings[:top_n], 1):
            lines.append(f"{i}. Query: \"{mapping.query_text}\"")
            lines.append(f"   → Arquivo: {mapping.filename}")
            lines.append(f"   → Coluna: \"{mapping.column_name}\"")
            lines.append(f"   → Tipo: {mapping.column_type}")
            lines.append(f"   → Match: {mapping.match_type} (confiança: {mapping.confidence:.2f})")
            
            if mapping.value is not None:
                lines.append(f"   → Valor: {mapping.value} ({mapping.operator})")
            
            lines.append("")
        
        return "\n".join(lines)

