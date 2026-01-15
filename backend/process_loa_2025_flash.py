"""
Script para processar LOA 2025 com Gemini Flash e batches de 25 páginas.
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.document import Document
from app.services.batch_extraction_service import BatchExtractionService
from app.services.gemini_with_timeout import GeminiWithTimeout
from app.models.dashboard_models import OrgaoFundo, ProgramaGoverno
from sqlalchemy import func
import time

print('=' * 70)
print('🚀 PROCESSAMENTO LOA 2025 - OTIMIZADO')
print('   • 25 páginas por batch')
print('   • Gemini 2.5 Flash (mais rápido)')
print('   • Timeout: 5 minutos por batch')
print('=' * 70)

db = SessionLocal()

try:
    doc = db.query(Document).filter(
        Document.filename.ilike('%2025%'),
        Document.type == 'LOA'
    ).first()
    
    if not doc:
        print('❌ Documento não encontrado!')
        sys.exit(1)
    
    print(f'\n📄 Documento: {doc.filename}')
    print(f'   • Tamanho: {doc.file_size_bytes / (1024*1024):.1f} MB')
    print(f'   • Páginas: 1167')
    
    total_batches = (1167 + 24) // 25
    print(f'   • Batches: {total_batches} (25 páginas cada)')
    
    # Criar serviço com 25 páginas por batch
    batch_service = BatchExtractionService(pages_per_batch=25)
    
    # Trocar para Gemini Flash (mais rápido)
    batch_service.model = GeminiWithTimeout(
        api_key=settings.GEMINI_API_KEY,
        model_name='gemini-2.5-flash',
        timeout=300  # 5 minutos por batch
    )
    
    print(f'\n⏱️  Iniciando processamento...')
    print(f'   ⏳ Tempo estimado: 20-30 minutos')
    print(f'   📊 Acompanhe o progresso abaixo\n')
    
    start_time = time.time()
    
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
        
        fundacao = db.query(OrgaoFundo).filter(
            OrgaoFundo.exercicio_id == exercicio.id,
            OrgaoFundo.nome.ilike('%FUNDAÇÃO%CIÊNCIA%')
        ).first()
        
        if fundacao:
            print(f'\n🎯 FUNDAÇÃO DE CIÊNCIA:')
            print(f'   ✅ ENCONTRADA!')
            print(f'   • Valor: R$ {fundacao.valor_total:,.2f}')
        else:
            print(f'\n🔍 Procurando FUNDAÇÃO DE CIÊNCIA...')
            print(f'   ❌ Não encontrada (pode estar com nome diferente)')
    
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

