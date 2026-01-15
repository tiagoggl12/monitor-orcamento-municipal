"""
Script para criar tabelas LDO no banco de dados.

Execute: python create_ldo_tables.py
"""

import sys
import os

# Adicionar app ao path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import engine
from app.models.dashboard_models import Base
from app.models.ldo_models import (
    MetasPrioridadesLDO,
    MetasFiscaisLDO,
    RiscosFiscaisLDO,
    PoliticasSetoriaisLDO,
    AvaliacaoAnteriorLDO
)

def create_ldo_tables():
    """Cria todas as tabelas LDO no banco de dados."""
    
    print("=" * 70)
    print("CRIANDO TABELAS LDO")
    print("=" * 70)
    
    try:
        # Importar TODOS os modelos para garantir que SQLAlchemy os conheça
        from app.models.dashboard_models import (
            ExercicioOrcamentario,
            ReceitaOrcamentaria,
            DespesaCategoria,
            ProgramaGoverno,
            OrgaoFundo,
            InvestimentoRegional,
            ParticipacaoSocial,
            LimiteConstitucional
        )
        
        # Criar tabelas
        print("\n📦 Criando estrutura de tabelas...")
        Base.metadata.create_all(bind=engine)
        
        print("\n✅ Tabelas LDO criadas com sucesso!")
        print("\nTabelas criadas:")
        print("  - metas_prioridades_ldo")
        print("  - metas_fiscais_ldo")
        print("  - riscos_fiscais_ldo")
        print("  - politicas_setoriais_ldo")
        print("  - avaliacao_anterior_ldo")
        print("\n" + "=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao criar tabelas: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_ldo_tables()
    sys.exit(0 if success else 1)

