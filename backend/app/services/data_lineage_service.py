"""
Serviço para gerenciar Data Lineage (rastreamento completo)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.data_lineage import DataLineage
from app.models.raw_file import RawFile
from app.models.parsed_data import ParsedData

logger = logging.getLogger(__name__)


class DataLineageService:
    """
    Gerencia rastreamento completo de transformações
    - Registra todas as operações
    - Permite auditoria completa
    - Gera relatórios de lineage
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_operation(
        self,
        raw_file_id: str,
        operation: str,
        operation_details: Optional[Dict[str, Any]] = None,
        parsed_data_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DataLineage:
        """
        Inicia registro de operação
        
        Args:
            raw_file_id: ID do raw file
            operation: Tipo de operação
            operation_details: Detalhes da operação
            parsed_data_id: ID do parsed data (se aplicável)
            metadata: Metadados adicionais (será armazenado em extra_metadata)
        
        Returns:
            DataLineage: Objeto criado
        """
        lineage = DataLineage(
            raw_file_id=raw_file_id,
            parsed_data_id=parsed_data_id,
            operation=operation,
            status="started",
            operation_details=operation_details or {},
            extra_metadata=metadata or {},
            started_at=datetime.utcnow()
        )
        
        self.db.add(lineage)
        self.db.commit()
        
        logger.info(f"🔵 Lineage started: {operation} (ID: {lineage.id})")
        
        return lineage
    
    def complete_operation(
        self,
        lineage: DataLineage,
        result: Optional[Dict[str, Any]] = None,
        embedding_model: Optional[str] = None,
        embedding_dimensions: Optional[str] = None
    ):
        """
        Marca operação como completa
        
        Args:
            lineage: Objeto DataLineage
            result: Resultado da operação
            embedding_model: Modelo usado (se aplicável)
            embedding_dimensions: Dimensões do embedding (se aplicável)
        """
        lineage.status = "completed"
        lineage.completed_at = datetime.utcnow()
        
        if result:
            lineage.result = result
        
        if embedding_model:
            lineage.embedding_model = embedding_model
        
        if embedding_dimensions:
            lineage.embedding_dimensions = embedding_dimensions
        
        self.db.commit()
        
        duration = lineage.calculate_duration_seconds()
        logger.info(f"✅ Lineage completed: {lineage.operation} ({duration:.2f}s)")
    
    def fail_operation(
        self,
        lineage: DataLineage,
        error_message: str,
        error_traceback: Optional[str] = None
    ):
        """
        Marca operação como falha
        
        Args:
            lineage: Objeto DataLineage
            error_message: Mensagem de erro
            error_traceback: Traceback do erro
        """
        lineage.status = "failed"
        lineage.completed_at = datetime.utcnow()
        lineage.error_message = error_message
        lineage.error_traceback = error_traceback
        
        self.db.commit()
        
        logger.error(f"❌ Lineage failed: {lineage.operation}")
        logger.error(f"   Error: {error_message}")
    
    def log_chat_retrieval(
        self,
        parsed_data_ids: List[str],
        chat_session_id: str,
        message_id: str,
        retrieval_scores: Optional[Dict[str, float]] = None
    ):
        """
        Registra uso de dados em chat (para auditoria)
        
        Args:
            parsed_data_ids: IDs dos parsed data usados
            chat_session_id: ID da sessão de chat
            message_id: ID da mensagem
            retrieval_scores: Scores de similaridade
        """
        for parsed_id in parsed_data_ids:
            # Buscar raw_file_id
            parsed_data = self.db.query(ParsedData).filter(
                ParsedData.id == parsed_id
            ).first()
            
            if not parsed_data:
                logger.warning(f"⚠️ ParsedData não encontrado: {parsed_id}")
                continue
            
            score = retrieval_scores.get(parsed_id) if retrieval_scores else None
            
            lineage = DataLineage(
                raw_file_id=parsed_data.raw_file_id,
                parsed_data_id=parsed_id,
                operation="chat_retrieval",
                status="completed",
                chat_session_id=chat_session_id,
                message_id=message_id,
                retrieval_score=str(score) if score else None,
                operation_details={
                    "retrieval_method": "semantic_search"
                },
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.db.add(lineage)
        
        self.db.commit()
        logger.info(f"📝 Logged retrieval for {len(parsed_data_ids)} items")
    
    def get_file_lineage(
        self,
        raw_file_id: str,
        include_chat_usage: bool = True
    ) -> Dict[str, Any]:
        """
        Retorna lineage completo de um arquivo
        
        Args:
            raw_file_id: ID do raw file
            include_chat_usage: Incluir uso em chats
        
        Returns:
            Dict com lineage completo
        """
        # Buscar raw file
        raw_file = self.db.query(RawFile).filter(
            RawFile.id == raw_file_id
        ).first()
        
        if not raw_file:
            return {"error": "Raw file not found"}
        
        # Buscar todas as operações
        query = self.db.query(DataLineage).filter(
            DataLineage.raw_file_id == raw_file_id
        )
        
        if not include_chat_usage:
            query = query.filter(DataLineage.operation != "chat_retrieval")
        
        lineage_entries = query.order_by(DataLineage.started_at.asc()).all()
        
        # Buscar parsed data
        parsed_data = self.db.query(ParsedData).filter(
            ParsedData.raw_file_id == raw_file_id
        ).all()
        
        return {
            "raw_file": raw_file.to_dict(),
            "lineage_entries": [entry.to_dict() for entry in lineage_entries],
            "parsed_data_count": len(parsed_data),
            "operations_summary": self._summarize_operations(lineage_entries),
            "chat_usage_count": sum(
                1 for e in lineage_entries if e.operation == "chat_retrieval"
            )
        }
    
    def get_data_lineage_for_chat_message(
        self,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Retorna lineage de dados usados em uma mensagem de chat
        (Para mostrar ao usuário EXATAMENTE de onde veio a informação)
        
        Args:
            message_id: ID da mensagem
        
        Returns:
            Dict com citações rastreáveis
        """
        # Buscar lineage entries
        lineage_entries = self.db.query(DataLineage).filter(
            DataLineage.message_id == message_id,
            DataLineage.operation == "chat_retrieval"
        ).all()
        
        citations = []
        
        for entry in lineage_entries:
            # Buscar parsed data
            parsed_data = self.db.query(ParsedData).filter(
                ParsedData.id == entry.parsed_data_id
            ).first()
            
            if not parsed_data:
                continue
            
            # Buscar raw file
            raw_file = self.db.query(RawFile).filter(
                RawFile.id == parsed_data.raw_file_id
            ).first()
            
            citations.append({
                "raw_file": {
                    "id": raw_file.id,
                    "filename": raw_file.filename,
                    "source_type": raw_file.source_type,
                    "source_identifier": raw_file.source_identifier,
                    "sha256_hash": raw_file.sha256_hash,
                    "created_at": raw_file.created_at.isoformat()
                },
                "parsed_data": {
                    "id": parsed_data.id,
                    "row_number": parsed_data.row_number,
                    "data": parsed_data.data,
                    "text_content": parsed_data.text_content
                },
                "retrieval": {
                    "score": entry.retrieval_score,
                    "timestamp": entry.started_at.isoformat()
                },
                "verify_url": f"/api/verify/{entry.id}"
            })
        
        return {
            "message_id": message_id,
            "citations_count": len(citations),
            "citations": citations
        }
    
    def verify_lineage_entry(self, lineage_id: str) -> Dict[str, Any]:
        """
        Verifica um lineage entry (para uso judicial)
        
        Args:
            lineage_id: ID do lineage entry
        
        Returns:
            Dict com verificação completa
        """
        lineage = self.db.query(DataLineage).filter(
            DataLineage.id == lineage_id
        ).first()
        
        if not lineage:
            return {"error": "Lineage entry not found"}
        
        # Buscar raw file
        raw_file = self.db.query(RawFile).filter(
            RawFile.id == lineage.raw_file_id
        ).first()
        
        # Verificar integridade do arquivo
        from app.services.raw_file_service import RawFileService
        raw_file_service = RawFileService(self.db)
        integrity_ok = raw_file_service.verify_integrity(raw_file)
        
        # Buscar parsed data
        parsed_data = None
        if lineage.parsed_data_id:
            parsed_data = self.db.query(ParsedData).filter(
                ParsedData.id == lineage.parsed_data_id
            ).first()
        
        return {
            "lineage_entry": lineage.to_dict(),
            "raw_file": raw_file.to_dict(),
            "parsed_data": parsed_data.to_dict() if parsed_data else None,
            "integrity_check": {
                "passed": integrity_ok,
                "sha256_hash": raw_file.sha256_hash,
                "verified_at": datetime.utcnow().isoformat()
            },
            "verification_signature": self._generate_verification_signature(
                lineage, raw_file, parsed_data
            )
        }
    
    def _summarize_operations(self, lineage_entries: List[DataLineage]) -> Dict[str, int]:
        """Sumariza operações por tipo e status"""
        summary = {}
        
        for entry in lineage_entries:
            key = f"{entry.operation}_{entry.status}"
            summary[key] = summary.get(key, 0) + 1
        
        return summary
    
    def _generate_verification_signature(
        self,
        lineage: DataLineage,
        raw_file: RawFile,
        parsed_data: Optional[ParsedData]
    ) -> str:
        """
        Gera assinatura de verificação (para uso judicial)
        Combina hashes e timestamps para garantir autenticidade
        """
        import hashlib
        
        signature_data = f"{raw_file.sha256_hash}:{lineage.id}:{lineage.started_at.isoformat()}"
        
        if parsed_data:
            signature_data += f":{parsed_data.id}:{parsed_data.row_number}"
        
        signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return signature
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais do sistema"""
        return {
            "total_operations": self.db.query(DataLineage).count(),
            "completed_operations": self.db.query(DataLineage).filter(
                DataLineage.status == "completed"
            ).count(),
            "failed_operations": self.db.query(DataLineage).filter(
                DataLineage.status == "failed"
            ).count(),
            "chat_retrievals": self.db.query(DataLineage).filter(
                DataLineage.operation == "chat_retrieval"
            ).count(),
            "operations_by_type": dict(
                self.db.query(
                    DataLineage.operation,
                    DataLineage.status
                ).group_by(
                    DataLineage.operation,
                    DataLineage.status
                ).all()
            )
        }

