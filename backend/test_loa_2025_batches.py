"""
Script para processar LOA 2025 em batches.

Teste com abordagem de quebrar o PDF em partes menores.
"""

import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.models.document import Document
from app.services.batch_extraction_service import BatchExtractionService

print('=' * 70)
print('🚀 PROCESSAMENTO LOA 2025 EM BATCHES')
print('=' * 70)

db = SessionLocal()

try:
    # Buscar documento
    doc = db.query(Document).filter(
        Document.filename.ilike('%2025%'),
        Document.type == 'LOA'
    ).first()
    
    if not doc:
        print('❌ Documento LOA 2025 não encontrado!')
        sys.exit(1)
    
    print(f'\n📄 Documento: {doc.filename}')
    print(f'   • Tamanho: {doc.file_size_bytes / (1024*1024):.1f} MB')
    print(f'   • Path: {doc.file_path}')
    
    # Criar serviço de batch
    batch_service = BatchExtractionService(pages_per_batch=100)
    
    print(f'\n🔄 Processando em batches de 100 páginas...')
    print(f'   (Cada batch pode levar 2-5 minutos)\n')
    
    import time
    start_time = time.time()
    
    # Processar
    exercicio = batch_service.extract_from_pdf_in_batches(
        pdf_path=doc.file_path,
        db=db,
        municipality_id=str(doc.municipality_id)
    )
    
    elapsed_time = time.time() - start_time
    
    print(f'\n' + '=' * 70)
    print('✅ PROCESSAMENTO CONCLUÍDO!')
    print('=' * 70)
    
    print(f'\n⏱️  Tempo total: {elapsed_time/60:.1f} minutos ({elapsed_time:.0f} segundos)')
    
    # Estatísticas
    from app.models.dashboard_models import OrgaoFundo, ProgramaGoverno
    from sqlalchemy import func
    
    total_orgaos = db.query(func.count(OrgaoFundo.id)).filter(
        OrgaoFundo.exercicio_id == exercicio.id
    ).scalar()
    
    total_programas = db.query(func.count(ProgramaGoverno.id)).filter(
        ProgramaGoverno.exercicio_id == exercicio.id
    ).scalar()
    
    print(f'\n📊 RESULTADOS:')
    print(f'   • Ano: {exercicio.ano}')
    print(f'   • Orçamento Total: R$ {exercicio.orcamento_total:,.2f}')
    print(f'   • Órgãos extraídos: {total_orgaos}')
    print(f'   • Programas extraídos: {total_programas}')
    
    if total_orgaos > 0:
        print(f'\n📋 Top 15 Órgãos:')
        orgaos = db.query(OrgaoFundo).filter(
            OrgaoFundo.exercicio_id == exercicio.id
        ).order_by(OrgaoFundo.valor_total.desc()).limit(15).all()
        
        for i, org in enumerate(orgaos, 1):
            print(f'   {i:2}. {org.nome[:55]:55} R$ {org.valor_total:>15,.2f}')
        
        # Verificar FUNDAÇÃO
        fundacao = db.query(OrgaoFundo).filter(
            OrgaoFundo.exercicio_id == exercicio.id,
            OrgaoFundo.nome.ilike('%FUNDAÇÃO%CIÊNCIA%')
        ).first()
        
        if fundacao:
            print(f'\n🎯 FUNDAÇÃO DE CIÊNCIA:')
            print(f'   ✅ ENCONTRADA!')
            print(f'   • Valor: R$ {fundacao.valor_total:,.2f}')
    
    print(f'\n🎉 Dashboard 2025 está POPULADO!')
    print(f'   Acesse: http://localhost:3000')
    
except Exception as e:
    print(f'\n❌ ERRO:')
    print(f'   {str(e)}')
    import traceback
    traceback.print_exc()
finally:
    db.close()

print('=' * 70)

