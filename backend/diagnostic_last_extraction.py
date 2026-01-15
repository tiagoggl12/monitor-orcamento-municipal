#!/usr/bin/env python3
"""
DIAGNÓSTICO DA ÚLTIMA EXTRAÇÃO
Verifica exatamente o que foi extraído e salvo no banco de dados.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.dashboard_models import (
    ExercicioOrcamentario, 
    InvestimentoRegional,
    OrgaoFundo,
    ProgramaGoverno,
    ReceitaOrcamentaria,
    DespesaCategoria,
    ParticipacaoSocial,
    LimiteConstitucional
)
from sqlalchemy import func, desc

def main():
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("🔍 DIAGNÓSTICO DA ÚLTIMA EXTRAÇÃO")
        print("=" * 80)
        
        # Buscar último exercício processado
        exercicio = db.query(ExercicioOrcamentario)\
            .filter(ExercicioOrcamentario.tipo_documento == "LOA")\
            .order_by(desc(ExercicioOrcamentario.processado_em))\
            .first()
        
        if not exercicio:
            print("❌ Nenhum exercício LOA encontrado no banco!")
            return
        
        print(f"\n📄 ÚLTIMO EXERCÍCIO PROCESSADO:")
        print(f"   Ano: {exercicio.ano}")
        print(f"   Município: {exercicio.municipio}")
        print(f"   Tipo: {exercicio.tipo_documento}")
        print(f"   Status: {exercicio.status}")
        print(f"   Processado em: {exercicio.processado_em}")
        print(f"   Orçamento Total: R$ {exercicio.orcamento_total:,.2f}")
        
        # Contar dados salvos
        print(f"\n📊 DADOS SALVOS:")
        
        # Receitas
        receitas_count = db.query(func.count(ReceitaOrcamentaria.id))\
            .filter(ReceitaOrcamentaria.exercicio_id == exercicio.id)\
            .scalar()
        print(f"   💰 Receitas: {receitas_count}")
        
        # Categorias de despesa
        categorias_count = db.query(func.count(DespesaCategoria.id))\
            .filter(DespesaCategoria.exercicio_id == exercicio.id)\
            .scalar()
        print(f"   📦 Categorias de Despesa: {categorias_count}")
        
        # Órgãos
        orgaos_count = db.query(func.count(OrgaoFundo.id))\
            .filter(OrgaoFundo.exercicio_id == exercicio.id)\
            .scalar()
        print(f"   🏛️  Órgãos: {orgaos_count}")
        
        if orgaos_count > 0:
            # Mostrar primeiros 5 órgãos
            orgaos = db.query(OrgaoFundo)\
                .filter(OrgaoFundo.exercicio_id == exercicio.id)\
                .limit(5)\
                .all()
            print(f"\n      📋 Primeiros 5 órgãos:")
            for org in orgaos:
                print(f"         • {org.nome} - R$ {org.valor_total:,.2f}")
        
        # Programas
        programas_count = db.query(func.count(ProgramaGoverno.id))\
            .filter(ProgramaGoverno.exercicio_id == exercicio.id)\
            .scalar()
        print(f"\n   📝 Programas: {programas_count}")
        
        # Regionais
        regionais_count = db.query(func.count(InvestimentoRegional.id))\
            .filter(InvestimentoRegional.exercicio_id == exercicio.id)\
            .scalar()
        print(f"   🗺️  Regionais: {regionais_count}")
        
        if regionais_count > 0:
            # Mostrar todas as regionais
            regionais = db.query(InvestimentoRegional)\
                .filter(InvestimentoRegional.exercicio_id == exercicio.id)\
                .order_by(InvestimentoRegional.regional_numero)\
                .all()
            
            print(f"\n      📍 Detalhes das Regionais:")
            for reg in regionais:
                print(f"\n         Regional {reg.regional_numero}: {reg.regional_nome}")
                print(f"            Valor Total: R$ {reg.valor_total:,.2f}")
                
                # Verificar dados detalhados
                has_details = False
                
                if reg.bairros_json:
                    try:
                        bairros = json.loads(reg.bairros_json)
                        print(f"            ✅ Bairros: {len(bairros)} bairros")
                        has_details = True
                    except:
                        print(f"            ⚠️  Bairros: erro ao parsear JSON")
                
                if reg.valores_por_area_json:
                    try:
                        valores = json.loads(reg.valores_por_area_json)
                        print(f"            ✅ Valores por Área: {len(valores)} áreas")
                        has_details = True
                    except:
                        print(f"            ⚠️  Valores por Área: erro ao parsear JSON")
                
                if reg.destaques_json:
                    try:
                        destaques = json.loads(reg.destaques_json)
                        print(f"            ✅ Destaques: {len(destaques)} projetos")
                        has_details = True
                    except:
                        print(f"            ⚠️  Destaques: erro ao parsear JSON")
                
                if not has_details:
                    print(f"            ❌ Sem dados detalhados (bairros, áreas, destaques)")
        
        # Participação Social
        participacao = db.query(ParticipacaoSocial)\
            .filter(ParticipacaoSocial.exercicio_id == exercicio.id)\
            .first()
        if participacao:
            print(f"\n   👥 Participação Social: ✅")
            print(f"      Fóruns: {participacao.foruns_realizados}")
        else:
            print(f"\n   👥 Participação Social: ❌")
        
        # Limites Constitucionais
        limites = db.query(LimiteConstitucional)\
            .filter(LimiteConstitucional.exercicio_id == exercicio.id)\
            .first()
        if limites:
            print(f"\n   ⚖️  Limites Constitucionais: ✅")
            print(f"      Educação: {limites.educacao_previsto_percentual}%")
            print(f"      Saúde: {limites.saude_previsto_percentual}%")
        else:
            print(f"\n   ⚖️  Limites Constitucionais: ❌")
        
        # DIAGNÓSTICO FINAL
        print(f"\n" + "=" * 80)
        print("🎯 DIAGNÓSTICO:")
        print("=" * 80)
        
        issues = []
        
        if receitas_count == 0:
            issues.append("❌ Nenhuma receita extraída")
        else:
            print(f"✅ Receitas: OK ({receitas_count} itens)")
        
        if categorias_count == 0:
            issues.append("❌ Nenhuma categoria de despesa extraída")
        else:
            print(f"✅ Categorias de Despesa: OK ({categorias_count} itens)")
        
        if orgaos_count == 0:
            issues.append("❌ Nenhum órgão extraído")
        elif orgaos_count < 50:
            issues.append(f"⚠️  Poucos órgãos extraídos ({orgaos_count}) - deveria ter 100+")
        else:
            print(f"✅ Órgãos: OK ({orgaos_count} itens)")
        
        if programas_count == 0:
            issues.append("❌ Nenhum programa extraído")
        elif programas_count < 50:
            issues.append(f"⚠️  Poucos programas extraídos ({programas_count}) - deveria ter 100+")
        else:
            print(f"✅ Programas: OK ({programas_count} itens)")
        
        if regionais_count == 0:
            issues.append("❌ Nenhuma regional extraída")
        elif regionais_count < 10:
            issues.append(f"⚠️  Poucas regionais extraídas ({regionais_count}) - deveria ter 12")
        else:
            print(f"✅ Regionais: OK ({regionais_count} itens)")
            
            # Verificar dados detalhados nas regionais
            regionais_sem_detalhes = 0
            for reg in regionais:
                if not (reg.bairros_json or reg.valores_por_area_json or reg.destaques_json):
                    regionais_sem_detalhes += 1
            
            if regionais_sem_detalhes > 0:
                issues.append(f"⚠️  {regionais_sem_detalhes} regionais sem dados detalhados (bairros/áreas/destaques)")
        
        if not participacao:
            issues.append("⚠️  Sem dados de participação social")
        
        if not limites:
            issues.append("⚠️  Sem limites constitucionais")
        
        if issues:
            print(f"\n⚠️  PROBLEMAS IDENTIFICADOS:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print(f"\n✅ TUDO OK! Extração completa e consistente.")
        
        print("=" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()

