"""
Script para criar as tabelas do Dashboard LOA/LDO no PostgreSQL.
"""

import sys
sys.path.insert(0, '/app')

from app.core.database import engine, Base
from app.models.dashboard_models import (
    ExercicioOrcamentario,
    ReceitaOrcamentaria,
    DespesaCategoria,
    ProgramaGoverno,
    OrgaoFundo,
    InvestimentoRegional,
    ParticipacaoSocial,
    LimiteConstitucional,
    SerieHistoricaReceita
)

print("🗄️ Criando tabelas do Dashboard LOA/LDO...")

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)

print("✅ Tabelas criadas com sucesso!")
print("")
print("📊 Tabelas criadas:")
print("   - exercicio_orcamentario")
print("   - receitas_orcamentarias")
print("   - despesas_categoria")
print("   - programas_governo")
print("   - orgaos_fundos")
print("   - investimento_regional")
print("   - participacao_social")
print("   - limites_constitucionais")
print("   - serie_historica_receitas")

