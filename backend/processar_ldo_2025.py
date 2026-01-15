"""
Script para processar LDO_2025.pdf existente no sistema.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.dashboard_extraction_service import DashboardExtractionService

def processar_ldo_2025():
    """Processa o arquivo LDO_2025.pdf."""
    
    db = SessionLocal()
    
    try:
        print("=" * 70)
        print("PROCESSANDO LDO 2025")
        print("=" * 70)
        
        # Buscar o documento LDO_2025.pdf
        doc = db.query(Document).filter(
            Document.filename.like('%LDO%2025%')
        ).first()
        
        if not doc:
            print("\n❌ Arquivo LDO_2025.pdf não encontrado no banco de dados!")
            print("\nDocumentos disponíveis:")
            docs = db.query(Document).all()
            for d in docs:
                print(f"  - {d.filename} ({d.type}) - {d.file_path}")
            return False
        
        print(f"\n✅ Documento encontrado: {doc.filename}")
        print(f"   Caminho: {doc.file_path}")
        print(f"   Tipo marcado: {doc.type}")
        
        # Verificar se o arquivo existe
        if not os.path.exists(doc.file_path):
            print(f"\n❌ Arquivo não existe no path: {doc.file_path}")
            return False
        
        # Processar com o serviço de extração
        print("\n🚀 Iniciando extração de dados da LDO...")
        print("   (Isso pode levar alguns minutos...)\n")
        
        service = DashboardExtractionService()
        exercicio = service.extract_ldo_from_pdf(
            pdf_path=doc.file_path,
            db=db,
            municipality_id=doc.municipality_id
        )
        
        print("\n" + "=" * 70)
        print("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        print("=" * 70)
        print(f"\nDados extraídos:")
        print(f"  - Tipo: {exercicio.tipo_documento}")
        print(f"  - Ano: {exercicio.ano}")
        print(f"  - Município: {exercicio.municipio}")
        print(f"  - Prefeito: {exercicio.prefeito}")
        
        # Verificar dados LDO
        from app.models.ldo_models import (
            MetasPrioridadesLDO,
            MetasFiscaisLDO,
            RiscosFiscaisLDO
        )
        
        metas_prioridades = db.query(MetasPrioridadesLDO).filter(
            MetasPrioridadesLDO.exercicio_id == exercicio.id
        ).first()
        
        metas_fiscais = db.query(MetasFiscaisLDO).filter(
            MetasFiscaisLDO.exercicio_id == exercicio.id
        ).first()
        
        riscos_fiscais = db.query(RiscosFiscaisLDO).filter(
            RiscosFiscaisLDO.exercicio_id == exercicio.id
        ).first()
        
        print(f"\nDados LDO salvos:")
        print(f"  - Metas e Prioridades: {'✅' if metas_prioridades else '❌'}")
        if metas_prioridades and metas_prioridades.prioridades:
            print(f"    → {len(metas_prioridades.prioridades)} prioridades")
        
        print(f"  - Metas Fiscais: {'✅' if metas_fiscais else '❌'}")
        if metas_fiscais:
            print(f"    → Resultado Primário: R$ {metas_fiscais.resultado_primario_meta:,.2f}" if metas_fiscais.resultado_primario_meta else "")
            print(f"    → RCL Prevista: R$ {metas_fiscais.rcl_prevista:,.2f}" if metas_fiscais.rcl_prevista else "")
        
        print(f"  - Riscos Fiscais: {'✅' if riscos_fiscais else '❌'}")
        if riscos_fiscais and riscos_fiscais.riscos:
            print(f"    → {len(riscos_fiscais.riscos)} riscos identificados")
        
        print("\n" + "=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao processar LDO: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    success = processar_ldo_2025()
    sys.exit(0 if success else 1)

