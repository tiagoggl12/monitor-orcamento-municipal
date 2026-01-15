"""
Modelos para dados estruturados da LDO (Lei de Diretrizes Orçamentárias).

Compatível com qualquer município brasileiro.
Estrutura flexível para capturar diversos formatos de LDO.
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


def generate_uuid():
    """Gera UUID como string para compatibilidade com SQLite."""
    import uuid
    return str(uuid.uuid4())


class MetasPrioridadesLDO(Base):
    """
    Armazena metas e prioridades governamentais da LDO.
    
    Exemplo: "Prioridade 1: Educação - Ampliar cobertura escolar"
    """
    
    __tablename__ = "metas_prioridades_ldo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Prioridades ordenadas por importância
    prioridades = Column(JSON)
    # Estrutura:
    # [
    #   {
    #     "ordem": 1,
    #     "setor": "Educação",
    #     "titulo": "Ampliar e qualificar rede escolar",
    #     "descricao": "Descrição detalhada...",
    #     "justificativa": "Necessidade de...",
    #     "meta_quantitativa": "Aumentar em 20%",
    #     "indicador": "Taxa de cobertura escolar",
    #     "prazo": "Dez/2025"
    #   }
    # ]
    
    # Diretrizes gerais do governo
    diretrizes_gerais = Column(JSON)
    # Array de strings:
    # ["Garantir equilíbrio fiscal", "Priorizar investimentos sociais", ...]
    
    # Metas de desempenho por setor (saúde, educação, etc)
    metas_setoriais = Column(JSON)
    # Estrutura:
    # {
    #   "saude": {
    #     "meta": "Reduzir mortalidade infantil",
    #     "indicador": "Taxa de mortalidade infantil",
    #     "valor_atual": 12.3,
    #     "valor_meta": 10.5,
    #     "unidade": "por mil nascidos vivos",
    #     "recursos_necessarios": 50000000
    #   },
    #   "educacao": {...}
    # }
    
    # Programas prioritários mencionados na LDO
    programas_prioritarios = Column(JSON)
    # Array de programas com códigos e descrições
    
    # Diretrizes setoriais específicas
    diretrizes_setoriais = Column(JSON)
    # {
    #   "saude": ["Fortalecer atenção básica", "Ampliar cobertura hospitalar"],
    #   "educacao": ["Melhorar infraestrutura escolar", "Capacitar professores"]
    # }
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="metas_prioridades_ldo")
    
    def __repr__(self):
        return f"<MetasPrioridadesLDO {self.exercicio_id}>"


class MetasFiscaisLDO(Base):
    """
    Armazena Anexo de Metas Fiscais da LDO.
    
    Obrigatório por lei (LRF - Lei de Responsabilidade Fiscal).
    """
    
    __tablename__ = "metas_fiscais_ldo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # ===== RESULTADO PRIMÁRIO =====
    # (Receitas não-financeiras - Despesas não-financeiras)
    resultado_primario_meta = Column(Numeric(20, 2))  # Meta para o ano
    resultado_primario_ano_anterior = Column(Numeric(20, 2))
    resultado_primario_dois_anos_antes = Column(Numeric(20, 2))
    
    # ===== RESULTADO NOMINAL =====
    # (Resultado primário - Juros líquidos)
    resultado_nominal_meta = Column(Numeric(20, 2))
    resultado_nominal_ano_anterior = Column(Numeric(20, 2))
    resultado_nominal_dois_anos_antes = Column(Numeric(20, 2))
    
    # ===== DÍVIDA CONSOLIDADA =====
    divida_consolidada_meta = Column(Numeric(20, 2))
    divida_consolidada_percentual_rcl = Column(Numeric(5, 2))  # % da RCL
    divida_consolidada_ano_anterior = Column(Numeric(20, 2))
    divida_consolidada_dois_anos_antes = Column(Numeric(20, 2))
    
    # ===== DÍVIDA CONSOLIDADA LÍQUIDA =====
    divida_liquida_meta = Column(Numeric(20, 2))
    divida_liquida_percentual_rcl = Column(Numeric(5, 2))
    divida_liquida_ano_anterior = Column(Numeric(20, 2))
    
    # ===== RECEITA CORRENTE LÍQUIDA (RCL) =====
    rcl_prevista = Column(Numeric(20, 2))
    rcl_ano_anterior = Column(Numeric(20, 2))
    rcl_dois_anos_antes = Column(Numeric(20, 2))
    
    # ===== RECEITAS E DESPESAS =====
    receita_total_prevista = Column(Numeric(20, 2))
    despesa_total_prevista = Column(Numeric(20, 2))
    
    # ===== PROJEÇÕES PLURIANUAIS (3 anos seguintes) =====
    projecoes_trienio = Column(JSON)
    # Estrutura:
    # {
    #   "2026": {
    #     "receita_total": 15500000000,
    #     "despesa_total": 15200000000,
    #     "resultado_primario": 300000000,
    #     "resultado_nominal": 180000000,
    #     "divida_consolidada": 2600000000,
    #     "rcl": 5800000000
    #   },
    #   "2027": {...},
    #   "2028": {...}
    # }
    
    # ===== PREMISSAS MACROECONÔMICAS =====
    premissas_macroeconomicas = Column(JSON)
    # {
    #   "pib_crescimento": 2.5,
    #   "inflacao_ipca": 4.0,
    #   "inflacao_igpm": 3.8,
    #   "taxa_selic": 10.5,
    #   "cambio_dolar": 5.20,
    #   "salario_minimo": 1412.00,
    #   "crescimento_transferencias_federais": 1.8
    # }
    
    # ===== MARGEM DE EXPANSÃO =====
    margem_expansao_despesas_obrigatorias = Column(Numeric(20, 2))
    
    # ===== RENÚNCIAS DE RECEITA =====
    renuncias_receita_total = Column(Numeric(20, 2))
    renuncias_receita_detalhes = Column(JSON)
    # [
    #   {"tipo": "IPTU", "valor": 50000000, "justificativa": "..."},
    #   {"tipo": "ISS", "valor": 30000000, "justificativa": "..."}
    # ]
    
    # Memória de cálculo e metodologia (para auditoria)
    metodologia_calculo = Column(Text)
    observacoes = Column(Text)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="metas_fiscais_ldo")
    
    def __repr__(self):
        return f"<MetasFiscaisLDO {self.exercicio_id} - Meta Primário: {self.resultado_primario_meta}>"


class RiscosFiscaisLDO(Base):
    """
    Armazena Anexo de Riscos Fiscais da LDO.
    
    Lista eventos que podem impactar negativamente as contas públicas.
    Obrigatório por lei (LRF - Lei de Responsabilidade Fiscal).
    """
    
    __tablename__ = "riscos_fiscais_ldo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Array de riscos identificados
    riscos = Column(JSON)
    # Estrutura:
    # [
    #   {
    #     "categoria": "receita",  # receita | despesa | divida | judicial | economico | operacional
    #     "subcategoria": "arrecadacao",
    #     "titulo": "Frustração de Receita de ICMS",
    #     "descricao": "Possível redução da arrecadação devido a...",
    #     "impacto_estimado": 150000000,
    #     "impacto_percentual_orcamento": 1.5,
    #     "probabilidade": "media",  # baixa | media | alta
    #     "nivel_risco": "alto",  # baixo | medio | alto | critico
    #     "providencias_mitigacao": "Revisão trimestral de metas, contingenciamento...",
    #     "fonte": "Estudos CONFAZ",
    #     "historico": "Em 2023 houve redução de 8%..."
    #   }
    # ]
    
    # Passivos Contingentes (processos judiciais, garantias, etc)
    passivos_contingentes_total = Column(Numeric(20, 2))
    passivos_contingentes_detalhes = Column(JSON)
    # [
    #   {
    #     "tipo": "trabalhista",  # trabalhista | civel | tributario | previdenciario
    #     "quantidade_processos": 45,
    #     "valor_total": 85000000,
    #     "valor_provisionado": 12000000,
    #     "probabilidade_perda": "possivel",  # remota | possivel | provavel
    #     "descricao": "Ações trabalhistas de servidores..."
    #   }
    # ]
    
    # Demandas Judiciais com Sentença Desfavorável
    demandas_judiciais_total = Column(Numeric(20, 2))
    demandas_judiciais_detalhes = Column(JSON)
    # [
    #   {
    #     "tipo": "precatorio",
    #     "quantidade": 120,
    #     "valor_total": 45000000,
    #     "ano_inscricao": 2024,
    #     "previsao_pagamento": "2025-2026"
    #   }
    # ]
    
    # Garantias Concedidas
    garantias_concedidas_total = Column(Numeric(20, 2))
    garantias_concedidas_detalhes = Column(JSON)
    
    # Operações de Crédito (riscos associados)
    operacoes_credito_riscos = Column(JSON)
    # [
    #   {
    #     "contrato": "Empréstimo BID 12345",
    #     "valor_principal": 500000000,
    #     "saldo_devedor": 320000000,
    #     "risco": "Variação cambial",
    #     "impacto_estimado": 50000000
    #   }
    # ]
    
    # Riscos Macroeconômicos
    riscos_macroeconomicos = Column(JSON)
    # {
    #   "inflacao_acima_previsto": {"impacto": 80000000, "probabilidade": "media"},
    #   "queda_pib": {"impacto": 120000000, "probabilidade": "baixa"},
    #   "alta_juros": {"impacto": 35000000, "probabilidade": "media"}
    # }
    
    # Outros Riscos Específicos do Município
    riscos_especificos_municipio = Column(JSON)
    
    # Avaliação Geral
    avaliacao_geral_risco = Column(String(20))  # baixo | moderado | alto | critico
    total_exposicao_risco = Column(Numeric(20, 2))  # Soma de todos impactos possíveis
    percentual_exposicao_orcamento = Column(Numeric(5, 2))
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="riscos_fiscais_ldo")
    
    def __repr__(self):
        return f"<RiscosFiscaisLDO {self.exercicio_id} - Riscos: {len(self.riscos or [])}>"


class PoliticasSetoriaisLDO(Base):
    """
    Armazena políticas setoriais detalhadas da LDO.
    
    Captura diretrizes específicas por área (saúde, educação, etc).
    """
    
    __tablename__ = "politicas_setoriais_ldo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Políticas por setor
    politicas = Column(JSON)
    # {
    #   "saude": {
    #     "diretrizes": ["Fortalecer atenção básica", "Ampliar rede hospitalar"],
    #     "programas_prioritarios": ["Saúde da Família", "UPA 24h"],
    #     "metas": [
    #       {
    #         "descricao": "Reduzir mortalidade infantil",
    #         "indicador": "Taxa por mil nascidos vivos",
    #         "meta": 10.5,
    #         "atual": 12.3
    #       }
    #     ],
    #     "recursos_estimados": 2800000000,
    #     "percentual_orcamento": 18.9,
    #     "acoes_principais": [...]
    #   },
    #   "educacao": {...},
    #   "assistencia_social": {...},
    #   "seguranca": {...},
    #   "infraestrutura": {...},
    #   "mobilidade": {...},
    #   "meio_ambiente": {...},
    #   "cultura": {...},
    #   "esporte": {...},
    #   "habitacao": {...}
    # }
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="politicas_setoriais_ldo")


class AvaliacaoAnteriorLDO(Base):
    """
    Armazena avaliação do cumprimento das metas do ano anterior.
    
    Transparência sobre se o governo cumpriu o que prometeu na LDO anterior.
    """
    
    __tablename__ = "avaliacao_anterior_ldo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Ano de referência da avaliação
    ano_avaliado = Column(Integer)
    
    # Avaliação de metas fiscais do ano anterior
    metas_fiscais_cumpridas = Column(JSON)
    # {
    #   "resultado_primario": {
    #     "meta": 380000000,
    #     "realizado": 420000000,
    #     "percentual_cumprimento": 110.5,
    #     "status": "superado"  # cumprido | superado | nao_cumprido
    #   },
    #   "resultado_nominal": {...},
    #   "divida_consolidada": {...}
    # }
    
    # Avaliação de metas setoriais
    metas_setoriais_cumpridas = Column(JSON)
    # {
    #   "saude": {
    #     "meta": "Reduzir mortalidade infantil para 11.0",
    #     "realizado": 11.8,
    #     "status": "parcialmente_cumprido",
    #     "justificativa": "Houve avanços mas não atingiu meta..."
    #   }
    # }
    
    # Avaliação geral
    avaliacao_geral = Column(Text)
    percentual_geral_cumprimento = Column(Numeric(5, 2))
    
    # Justificativas para não cumprimento
    justificativas_nao_cumprimento = Column(JSON)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="avaliacao_anterior_ldo")


# Atualizar relacionamentos no modelo ExercicioOrcamentario
# (Adicionar ao arquivo dashboard_models.py)

# No ExercicioOrcamentario, adicionar:
# metas_prioridades_ldo = relationship("MetasPrioridadesLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
# metas_fiscais_ldo = relationship("MetasFiscaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
# riscos_fiscais_ldo = relationship("RiscosFiscaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
# politicas_setoriais_ldo = relationship("PoliticasSetoriaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
# avaliacao_anterior_ldo = relationship("AvaliacaoAnteriorLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")

