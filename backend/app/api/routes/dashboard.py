"""
API Routes para Dashboard LOA/LDO.

Endpoints para visualização de dados orçamentários estruturados.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import os
import uuid
import shutil
import structlog

from app.api.dependencies import get_db
from app.services.dashboard_extraction_service import DashboardExtractionService
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

router = APIRouter()
logger = structlog.get_logger()


# ===========================
# SCHEMAS PYDANTIC PARA API
# ===========================

from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict


class VisaoGeralResponse(BaseModel):
    """Resposta para a tela de Visão Geral."""
    ano: int
    municipio: str
    tipo_documento: str
    prefeito: Optional[str]
    
    orcamento_total: float
    orcamento_fiscal: float
    orcamento_seguridade: float
    limite_suplementacao: Optional[float]
    variacao_ano_anterior: Optional[float]
    
    top_orgaos: List[Dict[str, Any]]
    principais_programas: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ReceitasResponse(BaseModel):
    """Resposta para a tela de Receitas."""
    ano: int
    
    receitas_correntes_total: float
    receitas_capital_total: float
    
    receitas_correntes: List[Dict[str, Any]]
    receitas_capital: List[Dict[str, Any]]
    
    # Série histórica (se disponível)
    serie_historica: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class DespesasResponse(BaseModel):
    """Resposta para a tela de Despesas."""
    ano: int
    despesa_total: float
    
    por_categoria: List[Dict[str, Any]]
    programas: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class InvestimentoRegionalResponse(BaseModel):
    """Resposta para a tela de Investimento Regional."""
    ano: int
    total_regionais: float
    regionais: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ParticipacaoSocialResponse(BaseModel):
    """Resposta para a tela de Participação Social."""
    ano: int
    foruns_realizados: int
    temas_chave: int
    total_priorizado: float
    rastreabilidade: float
    descricao: Optional[str]
    iniciativas: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class LimitesConstitucionaisResponse(BaseModel):
    """Resposta para dashboard de Limites Constitucionais."""
    ano: int
    
    educacao: Dict[str, Any]
    saude: Dict[str, Any]
    pessoal: Dict[str, Any]
    
    class Config:
        from_attributes = True


class ExercicioListItem(BaseModel):
    """Item da lista de exercícios."""
    id: str
    ano: int
    municipio: str
    tipo_documento: str
    orcamento_total: float
    processado_em: datetime
    
    class Config:
        from_attributes = True


# ===========================
# ENDPOINTS
# ===========================

@router.get("/exercicios", response_model=List[ExercicioListItem])
async def list_exercicios(
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Lista todos os exercícios orçamentários disponíveis."""
    service = DashboardExtractionService()
    exercicios = service.list_exercicios(db, municipio)
    
    return [
        ExercicioListItem(
            id=str(e.id),
            ano=e.ano,
            municipio=e.municipio,
            tipo_documento=e.tipo_documento,
            orcamento_total=float(e.orcamento_total or 0),
            processado_em=e.processado_em
        )
        for e in exercicios
    ]


@router.get("/visao-geral/{ano}", response_model=VisaoGeralResponse)
async def get_visao_geral(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para a tela de Visão Geral."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado para {municipio}")
    
    # Top órgãos
    orgaos = db.query(OrgaoFundo).filter(
        OrgaoFundo.exercicio_id == exercicio.id
    ).order_by(OrgaoFundo.valor_total.desc()).limit(10).all()
    
    top_orgaos = [
        {
            "codigo": o.codigo_orgao,
            "nome": o.nome,
            "sigla": o.sigla,
            "valor": float(o.valor_total or 0)
        }
        for o in orgaos
    ]
    
    # Principais programas
    programas = db.query(ProgramaGoverno).filter(
        ProgramaGoverno.exercicio_id == exercicio.id
    ).order_by(ProgramaGoverno.valor_total.desc()).limit(10).all()
    
    principais_programas = [
        {
            "codigo": p.codigo_programa,
            "nome": p.nome,
            "valor_total": float(p.valor_total or 0),
            "valor_fiscal": float(p.valor_fiscal or 0),
            "valor_seguridade": float(p.valor_seguridade or 0),
            "percentual_fiscal": float(p.percentual_fiscal or 0),
            "percentual_seguridade": float(p.percentual_seguridade or 0)
        }
        for p in programas
    ]
    
    return VisaoGeralResponse(
        ano=exercicio.ano,
        municipio=exercicio.municipio,
        tipo_documento=exercicio.tipo_documento,
        prefeito=exercicio.prefeito,
        orcamento_total=float(exercicio.orcamento_total or 0),
        orcamento_fiscal=float(exercicio.orcamento_fiscal or 0),
        orcamento_seguridade=float(exercicio.orcamento_seguridade or 0),
        limite_suplementacao=float(exercicio.limite_suplementacao) if exercicio.limite_suplementacao else None,
        variacao_ano_anterior=float(exercicio.variacao_ano_anterior) if exercicio.variacao_ano_anterior else None,
        top_orgaos=top_orgaos,
        principais_programas=principais_programas
    )


@router.get("/receitas/{ano}", response_model=ReceitasResponse)
async def get_receitas(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para a tela de Receitas."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    # Receitas correntes
    correntes = db.query(ReceitaOrcamentaria).filter(
        ReceitaOrcamentaria.exercicio_id == exercicio.id,
        ReceitaOrcamentaria.tipo == "corrente"
    ).order_by(ReceitaOrcamentaria.valor_previsto.desc()).all()
    
    # Receitas de capital
    capital = db.query(ReceitaOrcamentaria).filter(
        ReceitaOrcamentaria.exercicio_id == exercicio.id,
        ReceitaOrcamentaria.tipo == "capital"
    ).order_by(ReceitaOrcamentaria.valor_previsto.desc()).all()
    
    total_correntes = sum(r.valor_previsto or 0 for r in correntes)
    total_capital = sum(r.valor_previsto or 0 for r in capital)
    
    # Buscar série histórica (últimos 5 anos disponíveis)
    serie_historica = []
    exercicios_historicos = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.ano <= ano
    ).order_by(ExercicioOrcamentario.ano.desc()).limit(5).all()
    
    for ex_hist in reversed(exercicios_historicos):  # Ordem cronológica
        receitas_hist = db.query(ReceitaOrcamentaria).filter(
            ReceitaOrcamentaria.exercicio_id == ex_hist.id
        ).all()
        
        total_hist = sum(r.valor_previsto or 0 for r in receitas_hist)
        
        serie_historica.append({
            "ano": ex_hist.ano,
            "total": float(total_hist)
        })
    
    return ReceitasResponse(
        ano=ano,
        receitas_correntes_total=float(total_correntes),
        receitas_capital_total=float(total_capital),
        receitas_correntes=[
            {
                "categoria": r.categoria,
                "codigo": r.codigo_receita,
                "valor": float(r.valor_previsto or 0),
                "descricao_popular": r.descricao_popular
            }
            for r in correntes
        ],
        receitas_capital=[
            {
                "categoria": r.categoria,
                "codigo": r.codigo_receita,
                "valor": float(r.valor_previsto or 0),
                "descricao_popular": r.descricao_popular
            }
            for r in capital
        ],
        serie_historica=serie_historica
    )


@router.get("/despesas/{ano}", response_model=DespesasResponse)
async def get_despesas(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para a tela de Despesas."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    # Despesas por categoria
    categorias = db.query(DespesaCategoria).filter(
        DespesaCategoria.exercicio_id == exercicio.id
    ).order_by(DespesaCategoria.valor_total.desc()).all()
    
    # Programas
    programas = db.query(ProgramaGoverno).filter(
        ProgramaGoverno.exercicio_id == exercicio.id
    ).order_by(ProgramaGoverno.valor_total.desc()).all()
    
    return DespesasResponse(
        ano=ano,
        despesa_total=float(exercicio.orcamento_total or 0),
        por_categoria=[
            {
                "categoria": c.categoria,
                "codigo": c.codigo_natureza,
                "valor_total": float(c.valor_total or 0),
                "valor_fiscal": float(c.valor_fiscal or 0),
                "valor_seguridade": float(c.valor_seguridade or 0)
            }
            for c in categorias
        ],
        programas=[
            {
                "codigo": p.codigo_programa,
                "nome": p.nome,
                "objetivo": p.objetivo,
                "valor_total": float(p.valor_total or 0),
                "valor_fiscal": float(p.valor_fiscal or 0),
                "valor_seguridade": float(p.valor_seguridade or 0),
                "percentual_fiscal": float(p.percentual_fiscal or 0),
                "percentual_seguridade": float(p.percentual_seguridade or 0),
                "orgao_responsavel": p.orgao_responsavel
            }
            for p in programas
        ]
    )


@router.get("/investimento-regional/{ano}", response_model=InvestimentoRegionalResponse)
async def get_investimento_regional(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para a tela de Investimento Regional."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    regionais = db.query(InvestimentoRegional).filter(
        InvestimentoRegional.exercicio_id == exercicio.id
    ).order_by(InvestimentoRegional.valor_total.desc()).all()
    
    total = sum(r.valor_total or 0 for r in regionais)
    
    # Enriquecer dados das regionais
    regionais_data = []
    for r in regionais:
        destaques = r.destaques or {}
        
        # Processar destaques para o formato da API
        destaques_formatados = []
        for categoria, info in destaques.items():
            if isinstance(info, dict):
                destaques_formatados.append({
                    "categoria": categoria,
                    "nome": info.get("nome", ""),
                    "descricao": info.get("descricao", ""),
                    "prioridade": info.get("prioridade", "media"),
                    "valor": info.get("valor", 0)
                })
        
        regionais_data.append({
            "numero": r.regional_numero,
            "nome": r.regional_nome,
            "valor": float(r.valor_total or 0),
            "bairros": r.bairros or [],
            "destaques": destaques_formatados
        })
    
    return InvestimentoRegionalResponse(
        ano=ano,
        total_regionais=float(total),
        regionais=regionais_data
    )


@router.get("/investimento-regional/{ano}/regional/{numero}")
async def get_detalhamento_regional(
    ano: int,
    numero: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """
    Retorna detalhamento completo de uma regional específica.
    Usado no modal "Ver Plano Completo".
    """
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    regional = db.query(InvestimentoRegional).filter(
        InvestimentoRegional.exercicio_id == exercicio.id,
        InvestimentoRegional.regional_numero == numero
    ).first()
    
    if not regional:
        raise HTTPException(status_code=404, detail=f"Regional {numero} não encontrada")
    
    # Processar destaques para divisão por área
    destaques = regional.destaques or {}
    divisao_por_area = {}
    acoes_estrategicas = []
    
    # Mapear categorias para áreas com valores estimados
    categorias_mapa = {
        "saude": {"nome": "Saúde", "cor": "#EF4444", "icone": "health"},
        "infraestrutura": {"nome": "Infraestrutura", "cor": "#F97316", "icone": "construction"},
        "educacao": {"nome": "Educação", "cor": "#8B5CF6", "icone": "school"},
        "social": {"nome": "Social", "cor": "#3B82F6", "icone": "people"},
        "urbanismo": {"nome": "Urbanismo", "cor": "#10B981", "icone": "city"},
        "cultura": {"nome": "Cultura", "cor": "#EC4899", "icone": "palette"},
        "esporte": {"nome": "Esporte", "cor": "#14B8A6", "icone": "sports"}
    }
    
    # Calcular valor total para percentuais
    valor_total_regional = float(regional.valor_total or 0)
    
    # Processar destaques
    for categoria, info in destaques.items():
        if isinstance(info, dict):
            categoria_info = categorias_mapa.get(categoria, {"nome": categoria.capitalize(), "cor": "#6B7280", "icone": "circle"})
            
            # Para divisão por área, estimar valores proporcionais
            # Se temos 4 categorias, cada uma recebe ~25% do orçamento
            valor_estimado = info.get("valor", valor_total_regional / max(len(destaques), 1))
            percentual = (valor_estimado / valor_total_regional * 100) if valor_total_regional > 0 else 0
            
            divisao_por_area[categoria] = {
                "nome": categoria_info["nome"],
                "valor": float(valor_estimado),
                "percentual": round(percentual, 1),
                "cor": categoria_info["cor"]
            }
            
            # Adicionar às ações estratégicas
            acoes_estrategicas.append({
                "categoria": categoria,
                "categoria_nome": categoria_info["nome"],
                "categoria_icone": categoria_info["icone"],
                "cor": categoria_info["cor"],
                "nome": info.get("nome", ""),
                "descricao": info.get("descricao", ""),
                "prioridade": info.get("prioridade", "alta"),
                "valor_estimado": float(valor_estimado),
                "status": info.get("status", "planejado"),
                "previsao": f"Conclusão prevista para {ano}"
            })
    
    # Calcular indicador de impacto (simulado baseado no investimento per capita)
    num_bairros = len(regional.bairros or [])
    investimento_per_capita_estimado = valor_total_regional / (num_bairros * 50000) if num_bairros > 0 else 0
    variacao_idh_estimada = min(investimento_per_capita_estimado * 0.1, 5.0)  # Máximo 5%
    
    return {
        "ano": ano,
        "regional_numero": regional.regional_numero,
        "regional_nome": regional.regional_nome,
        "valor_total": valor_total_regional,
        "bairros": regional.bairros or [],
        "num_bairros": len(regional.bairros or []),
        "divisao_por_area": divisao_por_area,
        "acoes_estrategicas": acoes_estrategicas,
        "indicadores": {
            "idh_variacao_estimada": round(variacao_idh_estimada, 2),
            "populacao_beneficiada_estimada": num_bairros * 50000,  # Estimativa
            "investimento_per_capita": round(investimento_per_capita_estimado, 2)
        },
        "fonte_dados": f"PLOA {ano} - Versão Preliminar" if ano == 2026 else f"LOA {ano}",
        "documento_referencia": exercicio.documento_legal
    }


@router.get("/participacao-social/{ano}", response_model=ParticipacaoSocialResponse)
async def get_participacao_social(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para a tela de Participação Social."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    participacao = db.query(ParticipacaoSocial).filter(
        ParticipacaoSocial.exercicio_id == exercicio.id
    ).first()
    
    if not participacao:
        return ParticipacaoSocialResponse(
            ano=ano,
            foruns_realizados=0,
            temas_chave=0,
            total_priorizado=0,
            rastreabilidade=0,
            descricao=None,
            iniciativas=[]
        )
    
    return ParticipacaoSocialResponse(
        ano=ano,
        foruns_realizados=participacao.foruns_realizados or 0,
        temas_chave=participacao.temas_chave or 0,
        total_priorizado=float(participacao.total_priorizado or 0),
        rastreabilidade=float(participacao.rastreabilidade_percentual or 100),
        descricao=participacao.descricao_processo,
        iniciativas=participacao.iniciativas or []
    )


@router.get("/limites-constitucionais/{ano}", response_model=LimitesConstitucionaisResponse)
async def get_limites_constitucionais(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Retorna dados para o dashboard de Limites Constitucionais."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    limites = db.query(LimiteConstitucional).filter(
        LimiteConstitucional.exercicio_id == exercicio.id
    ).first()
    
    if not limites:
        return LimitesConstitucionaisResponse(
            ano=ano,
            educacao={"minimo": 25, "previsto": None, "valor": None, "cumprindo": None},
            saude={"minimo": 15, "previsto": None, "valor": None, "cumprindo": None},
            pessoal={"limite": 54, "previsto": None, "valor": None, "dentro_limite": None}
        )
    
    return LimitesConstitucionaisResponse(
        ano=ano,
        educacao={
            "minimo": float(limites.educacao_minimo_percentual or 25),
            "previsto": float(limites.educacao_previsto_percentual) if limites.educacao_previsto_percentual else None,
            "valor": float(limites.educacao_valor) if limites.educacao_valor else None,
            "cumprindo": limites.educacao_cumprindo
        },
        saude={
            "minimo": float(limites.saude_minimo_percentual or 15),
            "previsto": float(limites.saude_previsto_percentual) if limites.saude_previsto_percentual else None,
            "valor": float(limites.saude_valor) if limites.saude_valor else None,
            "cumprindo": limites.saude_cumprindo
        },
        pessoal={
            "limite": float(limites.pessoal_limite_percentual or 54),
            "previsto": float(limites.pessoal_previsto_percentual) if limites.pessoal_previsto_percentual else None,
            "valor": float(limites.pessoal_valor) if limites.pessoal_valor else None,
            "dentro_limite": limites.pessoal_dentro_limite
        }
    )


@router.post("/processar-documento")
async def processar_documento(
    file: UploadFile = File(...),
    municipio: str = "Fortaleza",
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Processa um documento LOA/LDO e extrai dados estruturados.
    
    - Aceita arquivos PDF
    - Extrai automaticamente todos os dados para o dashboard
    - Armazena no PostgreSQL para acesso rápido
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são aceitos")
    
    # Salvar arquivo temporariamente
    temp_dir = "/tmp/loa_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info("Arquivo salvo temporariamente", path=temp_path)
        
        # Detectar tipo de documento (LOA ou LDO) pelo nome do arquivo
        filename_upper = file.filename.upper()
        is_ldo = 'LDO' in filename_upper or 'DIRETRIZES' in filename_upper
        
        # Processar documento
        service = DashboardExtractionService()
        
        if is_ldo:
            logger.info("Detectado como LDO - usando extração específica")
            exercicio = service.extract_ldo_from_pdf(temp_path, db)
        else:
            logger.info("Detectado como LOA - usando extração padrão")
            exercicio = service.extract_from_pdf(temp_path, db)
        
        return {
            "status": "success",
            "message": f"Documento {exercicio.tipo_documento} processado com sucesso",
            "exercicio": {
                "id": str(exercicio.id),
                "ano": exercicio.ano,
                "municipio": exercicio.municipio,
                "tipo_documento": exercicio.tipo_documento,
                "orcamento_total": float(exercicio.orcamento_total or 0) if exercicio.orcamento_total else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar documento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Limpar arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.delete("/exercicio/{ano}")
async def delete_exercicio(
    ano: int,
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """Remove um exercício e todos os dados relacionados."""
    
    exercicio = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.ano == ano,
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).first()
    
    if not exercicio:
        raise HTTPException(status_code=404, detail=f"Exercício {ano} não encontrado")
    
    db.delete(exercicio)
    db.commit()
    
    return {"status": "success", "message": f"Exercício {ano} removido com sucesso"}


@router.get("/evolucao-receitas")
async def get_evolucao_receitas(
    municipio: str = "Fortaleza",
    db: Session = Depends(get_db)
):
    """
    Retorna série histórica de receitas agregando dados de todas as LOAs processadas.
    Útil para gráficos de evolução temporal.
    """
    
    # Buscar todos os exercícios do município ordenados por ano (apenas LOAs)
    exercicios = db.query(ExercicioOrcamentario).filter(
        ExercicioOrcamentario.municipio == municipio,
        ExercicioOrcamentario.tipo_documento == "LOA"
    ).order_by(ExercicioOrcamentario.ano).all()
    
    if not exercicios:
        raise HTTPException(status_code=404, detail=f"Nenhuma LOA encontrada para {municipio}")
    
    # Construir série histórica
    serie_historica = []
    
    for exercicio in exercicios:
        # Receitas correntes
        correntes = db.query(ReceitaOrcamentaria).filter(
            ReceitaOrcamentaria.exercicio_id == exercicio.id,
            ReceitaOrcamentaria.tipo == "corrente"
        ).all()
        
        # Receitas de capital
        capital = db.query(ReceitaOrcamentaria).filter(
            ReceitaOrcamentaria.exercicio_id == exercicio.id,
            ReceitaOrcamentaria.tipo == "capital"
        ).all()
        
        total_correntes = sum(r.valor_previsto or 0 for r in correntes)
        total_capital = sum(r.valor_previsto or 0 for r in capital)
        
        # Principais categorias de receitas correntes
        categorias_correntes = {}
        for r in correntes:
            if r.categoria:
                categoria = r.categoria
                if categoria not in categorias_correntes:
                    categorias_correntes[categoria] = 0
                categorias_correntes[categoria] += float(r.valor_previsto or 0)
        
        serie_historica.append({
            "ano": exercicio.ano,
            "total": float(exercicio.orcamento_total or 0),
            "receitas_correntes": float(total_correntes),
            "receitas_capital": float(total_capital),
            "categorias_principais": categorias_correntes,
            "prefeito": exercicio.prefeito
        })
    
    # Calcular variações percentuais ano a ano
    for i in range(1, len(serie_historica)):
        ano_anterior = serie_historica[i-1]["total"]
        ano_atual = serie_historica[i]["total"]
        
        if ano_anterior > 0:
            variacao = ((ano_atual - ano_anterior) / ano_anterior) * 100
            serie_historica[i]["variacao_percentual"] = round(variacao, 2)
        else:
            serie_historica[i]["variacao_percentual"] = None
    
    # Primeiro ano não tem variação
    if serie_historica:
        serie_historica[0]["variacao_percentual"] = None
    
    return {
        "municipio": municipio,
        "anos_disponiveis": [ex.ano for ex in exercicios],
        "total_exercicios": len(exercicios),
        "serie_historica": serie_historica
    }

