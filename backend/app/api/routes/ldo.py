"""
Rotas da API para dados de LDO (Lei de Diretrizes Orçamentárias).

Endpoints para consultar metas fiscais, riscos, prioridades, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import structlog

from app.api.dependencies import get_db
from app.models.dashboard_models import ExercicioOrcamentario
from app.models.ldo_models import (
    MetasPrioridadesLDO,
    MetasFiscaisLDO,
    RiscosFiscaisLDO,
    PoliticasSetoriaisLDO,
    AvaliacaoAnteriorLDO
)

logger = structlog.get_logger()

router = APIRouter(prefix="/ldo", tags=["LDO"])


# =====================================================
# ENDPOINTS DE LISTAGEM
# =====================================================

@router.get("/exercicios")
async def list_exercicios_ldo(
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Lista todos os exercícios com LDO processada.
    
    Retorna lista de anos disponíveis com dados de LDO.
    """
    exercicios = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.tipo_documento == "LDO",
        ExercicioOrcamentario.municipio == municipio
    ).order_by(ExercicioOrcamentario.ano.desc()).all()
    
    return [
        {
            "ano": ex.ano,
            "municipio": ex.municipio,
            "prefeito": ex.prefeito,
            "documento_legal": ex.documento_legal,
            "processado_em": ex.processado_em.isoformat() if ex.processado_em else None
        }
        for ex in exercicios
    ]


# =====================================================
# METAS E PRIORIDADES
# =====================================================

@router.get("/metas-prioridades/{ano}")
async def get_metas_prioridades(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna metas e prioridades governamentais da LDO.
    
    Inclui:
    - Prioridades ordenadas por importância
    - Diretrizes gerais do governo
    - Metas setoriais (saúde, educação, etc)
    - Programas prioritários
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    metas = db.query(MetasPrioridadesLDO).filter(
        MetasPrioridadesLDO.exercicio_id == exercicio.id
    ).first()
    
    if not metas:
        return {
            "ano": ano,
            "municipio": municipio,
            "prioridades": [],
            "diretrizes_gerais": [],
            "metas_setoriais": {},
            "programas_prioritarios": [],
            "diretrizes_setoriais": {}
        }
    
    return {
        "ano": ano,
        "municipio": municipio,
        "prefeito": exercicio.prefeito,
        "prioridades": metas.prioridades or [],
        "diretrizes_gerais": metas.diretrizes_gerais or [],
        "metas_setoriais": metas.metas_setoriais or {},
        "programas_prioritarios": metas.programas_prioritarios or [],
        "diretrizes_setoriais": metas.diretrizes_setoriais or {}
    }


# =====================================================
# METAS FISCAIS
# =====================================================

@router.get("/metas-fiscais/{ano}")
async def get_metas_fiscais(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna Anexo de Metas Fiscais da LDO (obrigatório por LRF).
    
    Inclui:
    - Resultado Primário, Nominal
    - Dívida Consolidada
    - RCL (Receita Corrente Líquida)
    - Projeções plurianuais
    - Premissas macroeconômicas
    - Renúncias de receita
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    metas = db.query(MetasFiscaisLDO).filter(
        MetasFiscaisLDO.exercicio_id == exercicio.id
    ).first()
    
    if not metas:
        raise HTTPException(
            status_code=404,
            detail=f"Metas fiscais não encontradas para LDO {ano}"
        )
    
    return {
        "ano": ano,
        "municipio": municipio,
        "resultado_primario": {
            "meta": float(metas.resultado_primario_meta) if metas.resultado_primario_meta else None,
            "ano_anterior": float(metas.resultado_primario_ano_anterior) if metas.resultado_primario_ano_anterior else None,
            "dois_anos_antes": float(metas.resultado_primario_dois_anos_antes) if metas.resultado_primario_dois_anos_antes else None
        },
        "resultado_nominal": {
            "meta": float(metas.resultado_nominal_meta) if metas.resultado_nominal_meta else None,
            "ano_anterior": float(metas.resultado_nominal_ano_anterior) if metas.resultado_nominal_ano_anterior else None,
            "dois_anos_antes": float(metas.resultado_nominal_dois_anos_antes) if metas.resultado_nominal_dois_anos_antes else None
        },
        "divida_consolidada": {
            "meta": float(metas.divida_consolidada_meta) if metas.divida_consolidada_meta else None,
            "percentual_rcl": float(metas.divida_consolidada_percentual_rcl) if metas.divida_consolidada_percentual_rcl else None,
            "ano_anterior": float(metas.divida_consolidada_ano_anterior) if metas.divida_consolidada_ano_anterior else None,
            "dois_anos_antes": float(metas.divida_consolidada_dois_anos_antes) if metas.divida_consolidada_dois_anos_antes else None
        },
        "divida_liquida": {
            "meta": float(metas.divida_liquida_meta) if metas.divida_liquida_meta else None,
            "percentual_rcl": float(metas.divida_liquida_percentual_rcl) if metas.divida_liquida_percentual_rcl else None,
            "ano_anterior": float(metas.divida_liquida_ano_anterior) if metas.divida_liquida_ano_anterior else None
        },
        "rcl": {
            "prevista": float(metas.rcl_prevista) if metas.rcl_prevista else None,
            "ano_anterior": float(metas.rcl_ano_anterior) if metas.rcl_ano_anterior else None,
            "dois_anos_antes": float(metas.rcl_dois_anos_antes) if metas.rcl_dois_anos_antes else None
        },
        "receita_total_prevista": float(metas.receita_total_prevista) if metas.receita_total_prevista else None,
        "despesa_total_prevista": float(metas.despesa_total_prevista) if metas.despesa_total_prevista else None,
        "projecoes_trienio": metas.projecoes_trienio or {},
        "premissas_macroeconomicas": metas.premissas_macroeconomicas or {},
        "margem_expansao_despesas_obrigatorias": float(metas.margem_expansao_despesas_obrigatorias) if metas.margem_expansao_despesas_obrigatorias else None,
        "renuncias_receita": {
            "total": float(metas.renuncias_receita_total) if metas.renuncias_receita_total else None,
            "detalhes": metas.renuncias_receita_detalhes or []
        },
        "metodologia_calculo": metas.metodologia_calculo,
        "observacoes": metas.observacoes
    }


# =====================================================
# RISCOS FISCAIS
# =====================================================

@router.get("/riscos-fiscais/{ano}")
async def get_riscos_fiscais(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna Anexo de Riscos Fiscais da LDO (obrigatório por LRF).
    
    Inclui:
    - Riscos identificados (receita, despesa, dívida, judicial, etc)
    - Passivos contingentes
    - Demandas judiciais
    - Garantias concedidas
    - Avaliação geral de risco
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    riscos = db.query(RiscosFiscaisLDO).filter(
        RiscosFiscaisLDO.exercicio_id == exercicio.id
    ).first()
    
    if not riscos:
        return {
            "ano": ano,
            "municipio": municipio,
            "riscos": [],
            "passivos_contingentes": {"total": 0, "detalhes": []},
            "demandas_judiciais": {"total": 0, "detalhes": []},
            "avaliacao_geral_risco": "nao_informado"
        }
    
    return {
        "ano": ano,
        "municipio": municipio,
        "riscos": riscos.riscos or [],
        "passivos_contingentes": {
            "total": float(riscos.passivos_contingentes_total) if riscos.passivos_contingentes_total else 0,
            "detalhes": riscos.passivos_contingentes_detalhes or []
        },
        "demandas_judiciais": {
            "total": float(riscos.demandas_judiciais_total) if riscos.demandas_judiciais_total else 0,
            "detalhes": riscos.demandas_judiciais_detalhes or []
        },
        "garantias_concedidas": {
            "total": float(riscos.garantias_concedidas_total) if riscos.garantias_concedidas_total else 0,
            "detalhes": riscos.garantias_concedidas_detalhes or []
        },
        "operacoes_credito_riscos": riscos.operacoes_credito_riscos or [],
        "riscos_macroeconomicos": riscos.riscos_macroeconomicos or {},
        "riscos_especificos_municipio": riscos.riscos_especificos_municipio or [],
        "avaliacao_geral_risco": riscos.avaliacao_geral_risco or "nao_informado",
        "total_exposicao_risco": float(riscos.total_exposicao_risco) if riscos.total_exposicao_risco else 0,
        "percentual_exposicao_orcamento": float(riscos.percentual_exposicao_orcamento) if riscos.percentual_exposicao_orcamento else 0
    }


# =====================================================
# POLÍTICAS SETORIAIS
# =====================================================

@router.get("/politicas-setoriais/{ano}")
async def get_politicas_setoriais(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna políticas setoriais detalhadas da LDO.
    
    Políticas por setor: saúde, educação, assistência social, etc.
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    politicas = db.query(PoliticasSetoriaisLDO).filter(
        PoliticasSetoriaisLDO.exercicio_id == exercicio.id
    ).first()
    
    return {
        "ano": ano,
        "municipio": municipio,
        "politicas": politicas.politicas if politicas else {}
    }


# =====================================================
# AVALIAÇÃO ANO ANTERIOR
# =====================================================

@router.get("/avaliacao-ano-anterior/{ano}")
async def get_avaliacao_ano_anterior(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna avaliação do cumprimento de metas do ano anterior.
    
    Transparência sobre se o governo cumpriu o prometido na LDO anterior.
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    avaliacao = db.query(AvaliacaoAnteriorLDO).filter(
        AvaliacaoAnteriorLDO.exercicio_id == exercicio.id
    ).first()
    
    if not avaliacao:
        return {
            "ano": ano,
            "municipio": municipio,
            "ano_avaliado": None,
            "disponivel": False
        }
    
    return {
        "ano": ano,
        "municipio": municipio,
        "ano_avaliado": avaliacao.ano_avaliado,
        "disponivel": True,
        "metas_fiscais_cumpridas": avaliacao.metas_fiscais_cumpridas or {},
        "metas_setoriais_cumpridas": avaliacao.metas_setoriais_cumpridas or {},
        "avaliacao_geral": avaliacao.avaliacao_geral,
        "percentual_geral_cumprimento": float(avaliacao.percentual_geral_cumprimento) if avaliacao.percentual_geral_cumprimento else None,
        "justificativas_nao_cumprimento": avaliacao.justificativas_nao_cumprimento or []
    }


# =====================================================
# VISÃO CONSOLIDADA (todas as abas em uma chamada)
# =====================================================

@router.get("/consolidado/{ano}")
async def get_ldo_consolidada(
    ano: int,
    municipio: str = Query("Fortaleza", description="Nome do município"),
    db: Session = Depends(get_db)
):
    """
    Retorna todos os dados da LDO em uma única chamada.
    
    Útil para carregar o dashboard completo de uma vez.
    """
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LDO"
    ).first()
    
    if not exercicio:
        raise HTTPException(
            status_code=404,
            detail=f"LDO {ano} não encontrada para {municipio}"
        )
    
    # Buscar todos os dados
    metas_prioridades = db.query(MetasPrioridadesLDO).filter(
        MetasPrioridadesLDO.exercicio_id == exercicio.id
    ).first()
    
    metas_fiscais = db.query(MetasFiscaisLDO).filter(
        MetasFiscaisLDO.exercicio_id == exercicio.id
    ).first()
    
    riscos_fiscais = db.query(RiscosFiscaisLDO).filter(
        RiscosFiscaisLDO.exercicio_id == exercicio.id
    ).first()
    
    politicas_setoriais = db.query(PoliticasSetoriaisLDO).filter(
        PoliticasSetoriaisLDO.exercicio_id == exercicio.id
    ).first()
    
    return {
        "ano": ano,
        "municipio": municipio,
        "prefeito": exercicio.prefeito,
        "documento_legal": exercicio.documento_legal,
        "tem_metas_prioridades": metas_prioridades is not None,
        "tem_metas_fiscais": metas_fiscais is not None,
        "tem_riscos_fiscais": riscos_fiscais is not None,
        "tem_politicas_setoriais": politicas_setoriais is not None,
        "processado_em": exercicio.processado_em.isoformat() if exercicio.processado_em else None
    }

