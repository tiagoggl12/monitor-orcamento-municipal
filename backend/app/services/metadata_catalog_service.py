"""
Metadata Catalog Service
========================

Gera um catálogo dinâmico dos metadados disponíveis no sistema,
permitindo que o LLM tenha "awareness" do que existe no banco.
"""

from typing import Dict, Any, List, Set
from sqlalchemy.orm import Session
import structlog

from app.services.vector_db import VectorDBService
from app.models.document import Document
from app.models.municipality import Municipality

logger = structlog.get_logger(__name__)


class MetadataCatalogService:
    """
    Serviço para gerar catálogos de metadados do sistema
    """
    
    def __init__(self):
        self.vector_db = VectorDBService()
    
    async def get_full_catalog(self, municipality_id: str, db: Session) -> Dict[str, Any]:
        """
        Retorna catálogo completo de todos os dados disponíveis
        
        Args:
            municipality_id: ID do município
            db: Sessão do banco de dados
            
        Returns:
            Catálogo estruturado com todos os metadados
        """
        try:
            catalog = {
                "municipality": await self._get_municipality_info(municipality_id, db),
                "portal_transparency": await self._get_portal_catalog(municipality_id),
                "loa": await self._get_loa_catalog(municipality_id, db),
                "ldo": await self._get_ldo_catalog(municipality_id, db),
                "summary": {}
            }
            
            # Gerar resumo geral
            catalog["summary"] = {
                "total_collections": (
                    len(catalog["portal_transparency"]["collections"]) +
                    len(catalog["loa"]["collections"]) +
                    len(catalog["ldo"]["collections"])
                ),
                "total_documents": (
                    catalog["portal_transparency"]["total_documents"] +
                    catalog["loa"]["total_documents"] +
                    catalog["ldo"]["total_documents"]
                ),
                "has_portal_data": catalog["portal_transparency"]["total_documents"] > 0,
                "has_loa_data": catalog["loa"]["total_documents"] > 0,
                "has_ldo_data": catalog["ldo"]["total_documents"] > 0,
            }
            
            logger.info(
                "Metadata catalog generated",
                municipality_id=municipality_id,
                total_collections=catalog["summary"]["total_collections"],
                total_documents=catalog["summary"]["total_documents"]
            )
            
            return catalog
            
        except Exception as e:
            logger.error(f"Error generating metadata catalog: {e}", municipality_id=municipality_id)
            raise
    
    async def _get_municipality_info(self, municipality_id: str, db: Session) -> Dict[str, Any]:
        """
        Obtém informações do município
        """
        municipality = db.query(Municipality).filter(
            Municipality.id == municipality_id
        ).first()
        
        if not municipality:
            return {
                "id": municipality_id,
                "name": "Unknown",
                "state": "Unknown"
            }
        
        return {
            "id": municipality.id,
            "name": municipality.name,
            "state": municipality.state,
            "year": getattr(municipality, 'year', None)
        }
    
    async def _get_portal_catalog(self, municipality_id: str) -> Dict[str, Any]:
        """
        Gera catálogo das collections do Portal da Transparência
        """
        try:
            # Listar todas as collections que começam com "portal_"
            all_collections = self.vector_db.client.list_collections()
            portal_collections = [
                c.name for c in all_collections 
                if c.name.startswith("portal_")
            ]
            
            total_documents = 0
            collections_info = []
            
            # Extrair metadados únicos de todas as collections
            all_organs = set()
            all_modalities = set()
            all_doc_types = set()
            editals_range = {"min": None, "max": None}
            date_range = {"min": None, "max": None}
            
            for collection_name in portal_collections:
                try:
                    collection = self.vector_db.client.get_collection(name=collection_name)
                    count = collection.count()
                    total_documents += count
                    
                    # Pegar amostra de metadados (primeiros 100 documentos)
                    sample = collection.get(limit=100, include=["metadatas"])
                    
                    if sample and sample.get("metadatas"):
                        collection_metadata = self._analyze_collection_metadata(sample["metadatas"])
                        
                        # Agregar metadados
                        all_organs.update(collection_metadata.get("organs", []))
                        all_modalities.update(collection_metadata.get("modalities", []))
                        all_doc_types.update(collection_metadata.get("doc_types", []))
                        
                        # Atualizar ranges
                        if collection_metadata.get("editals"):
                            col_edital_min = collection_metadata["editals"].get("min")
                            col_edital_max = collection_metadata["editals"].get("max")
                            if col_edital_min:
                                if editals_range["min"] is None or col_edital_min < editals_range["min"]:
                                    editals_range["min"] = col_edital_min
                            if col_edital_max:
                                if editals_range["max"] is None or col_edital_max > editals_range["max"]:
                                    editals_range["max"] = col_edital_max
                        
                        if collection_metadata.get("dates"):
                            col_date_min = collection_metadata["dates"].get("min")
                            col_date_max = collection_metadata["dates"].get("max")
                            if col_date_min:
                                if date_range["min"] is None or col_date_min < date_range["min"]:
                                    date_range["min"] = col_date_min
                            if col_date_max:
                                if date_range["max"] is None or col_date_max > date_range["max"]:
                                    date_range["max"] = col_date_max
                        
                        collections_info.append({
                            "name": collection_name,
                            "documents": count,
                            "metadata": collection_metadata
                        })
                    else:
                        collections_info.append({
                            "name": collection_name,
                            "documents": count,
                            "metadata": {}
                        })
                    
                except Exception as e:
                    logger.warning(f"Error analyzing collection {collection_name}: {e}")
                    continue
            
            return {
                "collections": portal_collections,
                "total_documents": total_documents,
                "organs": sorted(list(all_organs)),
                "modalities": sorted(list(all_modalities)),
                "doc_types": sorted(list(all_doc_types)),
                "editals_range": editals_range if editals_range["min"] else None,
                "date_range": date_range if date_range["min"] else None,
                "collections_detail": collections_info
            }
            
        except Exception as e:
            logger.error(f"Error generating portal catalog: {e}")
            return {
                "collections": [],
                "total_documents": 0,
                "organs": [],
                "modalities": [],
                "doc_types": [],
                "editals_range": None,
                "date_range": None,
                "collections_detail": []
            }
    
    def _analyze_collection_metadata(self, metadatas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa metadados de uma amostra de documentos
        """
        organs = set()
        modalities = set()
        doc_types = set()
        editals = []
        dates = []
        
        for meta in metadatas:
            # Órgãos
            if "origem" in meta and meta["origem"]:
                organs.add(str(meta["origem"]).upper().strip())
            
            # Modalidades
            if "modalidade" in meta and meta["modalidade"]:
                modalities.add(str(meta["modalidade"]).upper().strip())
            
            # Tipos de documento
            if "doc_type" in meta and meta["doc_type"]:
                doc_types.add(str(meta["doc_type"]).lower().strip())
            
            # Editais (números)
            if "edital" in meta and meta["edital"]:
                try:
                    edital_num = int(meta["edital"])
                    editals.append(edital_num)
                except:
                    pass
            
            # Datas
            if "data_abertura_timestamp" in meta and meta["data_abertura_timestamp"]:
                dates.append(str(meta["data_abertura_timestamp"]))
            elif "data_abertura" in meta and meta["data_abertura"]:
                dates.append(str(meta["data_abertura"]))
        
        result = {
            "organs": sorted(list(organs)),
            "modalities": sorted(list(modalities)),
            "doc_types": sorted(list(doc_types))
        }
        
        if editals:
            result["editals"] = {
                "min": min(editals),
                "max": max(editals),
                "count": len(editals)
            }
        
        if dates:
            result["dates"] = {
                "min": min(dates),
                "max": max(dates),
                "count": len(dates)
            }
        
        return result
    
    async def _get_loa_catalog(self, municipality_id: str, db: Session) -> Dict[str, Any]:
        """
        Gera catálogo das collections de LOA
        """
        try:
            # Buscar documentos LOA no banco
            loa_docs = db.query(Document).filter(
                Document.municipality_id == municipality_id,
                Document.document_type == "loa"
            ).all()
            
            collections = []
            total_documents = 0
            years = set()
            
            for doc in loa_docs:
                collection_name = f"doc_{doc.id}"
                
                # Verificar se a collection existe no ChromaDB
                try:
                    collection = self.vector_db.client.get_collection(name=collection_name)
                    count = collection.count()
                    total_documents += count
                    
                    collections.append(collection_name)
                    if doc.year:
                        years.add(doc.year)
                except:
                    pass
            
            return {
                "collections": collections,
                "total_documents": total_documents,
                "years": sorted(list(years)),
                "document_count": len(loa_docs)
            }
            
        except Exception as e:
            logger.error(f"Error generating LOA catalog: {e}")
            return {
                "collections": [],
                "total_documents": 0,
                "years": [],
                "document_count": 0
            }
    
    async def _get_ldo_catalog(self, municipality_id: str, db: Session) -> Dict[str, Any]:
        """
        Gera catálogo das collections de LDO
        """
        try:
            # Buscar documentos LDO no banco
            ldo_docs = db.query(Document).filter(
                Document.municipality_id == municipality_id,
                Document.document_type == "ldo"
            ).all()
            
            collections = []
            total_documents = 0
            years = set()
            
            for doc in ldo_docs:
                collection_name = f"doc_{doc.id}"
                
                # Verificar se a collection existe no ChromaDB
                try:
                    collection = self.vector_db.client.get_collection(name=collection_name)
                    count = collection.count()
                    total_documents += count
                    
                    collections.append(collection_name)
                    if doc.year:
                        years.add(doc.year)
                except:
                    pass
            
            return {
                "collections": collections,
                "total_documents": total_documents,
                "years": sorted(list(years)),
                "document_count": len(ldo_docs)
            }
            
        except Exception as e:
            logger.error(f"Error generating LDO catalog: {e}")
            return {
                "collections": [],
                "total_documents": 0,
                "years": [],
                "document_count": 0
            }

