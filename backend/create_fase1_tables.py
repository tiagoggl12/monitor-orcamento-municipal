"""
Script para criar tabelas da Fase 1
"""
import sys
sys.path.insert(0, '/app')

from app.core.database import engine, Base
from app.models import RawFile, ParsedData, DataLineage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Cria tabelas da Fase 1"""
    try:
        logger.info("🔧 Criando tabelas da Fase 1...")
        
        # Criar tabelas
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Tabelas criadas com sucesso!")
        logger.info("   - raw_files")
        logger.info("   - parsed_data")
        logger.info("   - data_lineage")
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas: {e}")
        raise

if __name__ == "__main__":
    create_tables()

