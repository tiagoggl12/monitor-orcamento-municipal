"""
Modelos para dados estruturados do Dashboard LOA/LDO.

Estes modelos armazenam dados extraídos de forma estruturada para 
exibição rápida e precisa nos dashboards do TCE.

Compatível com SQLite e PostgreSQL.
"""

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json

from app.core.database import Base


def generate_uuid():
    """Gera UUID como string para compatibilidade com SQLite."""
    return str(uuid.uuid4())


class ExercicioOrcamentario(Base):
    """Tabela principal do exercício orçamentário (LOA/LDO por ano)."""
    
    __tablename__ = "exercicio_orcamentario"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    # Identificação
    ano = Column(Integer, nullable=False, index=True)
    municipio = Column(String(100), nullable=False)
    estado = Column(String(2), default="CE")
    tipo_documento = Column(String(10), nullable=False)  # LOA, LDO, PLOA
    
    # Metadados do documento
    prefeito = Column(String(200))
    documento_legal = Column(String(200))  # "Lei nº 11.515, de 27 de dezembro de 2024"
    documento_referencia = Column(String(200))  # "Mensagem nº 55, de 15 de outubro de 2025"
    data_publicacao = Column(DateTime)
    
    # Valores principais
    orcamento_total = Column(Numeric(20, 2))
    orcamento_fiscal = Column(Numeric(20, 2))
    orcamento_seguridade = Column(Numeric(20, 2))
    limite_suplementacao = Column(Numeric(5, 2))  # Percentual
    receita_corrente_liquida = Column(Numeric(20, 2))
    variacao_ano_anterior = Column(Numeric(5, 2))  # Percentual
    
    # Rastreabilidade
    raw_file_id = Column(String(36), ForeignKey("raw_files.id"))
    municipality_id = Column(String(36), ForeignKey("municipalities.id"))
    
    # Controle
    processado_em = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="completed")  # processing, completed, error
    observacoes = Column(Text)  # JSON serializado como texto
    
    # Relacionamentos LOA
    receitas = relationship("ReceitaOrcamentaria", back_populates="exercicio", cascade="all, delete-orphan")
    despesas_categoria = relationship("DespesaCategoria", back_populates="exercicio", cascade="all, delete-orphan")
    programas = relationship("ProgramaGoverno", back_populates="exercicio", cascade="all, delete-orphan")
    orgaos = relationship("OrgaoFundo", back_populates="exercicio", cascade="all, delete-orphan")
    regionais = relationship("InvestimentoRegional", back_populates="exercicio", cascade="all, delete-orphan")
    participacao_social = relationship("ParticipacaoSocial", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    limites_constitucionais = relationship("LimiteConstitucional", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    
    # Relacionamentos LDO (novos)
    metas_prioridades_ldo = relationship("MetasPrioridadesLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    metas_fiscais_ldo = relationship("MetasFiscaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    riscos_fiscais_ldo = relationship("RiscosFiscaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    politicas_setoriais_ldo = relationship("PoliticasSetoriaisLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    avaliacao_anterior_ldo = relationship("AvaliacaoAnteriorLDO", back_populates="exercicio", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExercicioOrcamentario {self.tipo_documento} {self.ano} - {self.municipio}>"


class ReceitaOrcamentaria(Base):
    """Receitas detalhadas por categoria."""
    
    __tablename__ = "receitas_orcamentarias"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Classificação
    tipo = Column(String(20), nullable=False)  # corrente, capital
    categoria = Column(String(200), nullable=False)
    subcategoria = Column(String(200))
    codigo_receita = Column(String(30))
    
    # Valores
    valor_previsto = Column(Numeric(20, 2), nullable=False)
    
    # Descrição para cidadão
    descricao_popular = Column(Text)
    
    # Fonte de recurso
    fonte_recurso = Column(String(100))
    
    # Ordem de exibição
    ordem = Column(Integer, default=0)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="receitas")
    
    def __repr__(self):
        return f"<Receita {self.categoria}: R$ {self.valor_previsto}>"


class DespesaCategoria(Base):
    """Despesas por categoria econômica."""
    
    __tablename__ = "despesas_categoria"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Classificação
    categoria = Column(String(200), nullable=False)
    codigo_natureza = Column(String(30))
    
    # Valores por esfera
    valor_fiscal = Column(Numeric(20, 2), default=0)
    valor_seguridade = Column(Numeric(20, 2), default=0)
    valor_total = Column(Numeric(20, 2), nullable=False)
    
    # Ordem de exibição
    ordem = Column(Integer, default=0)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="despesas_categoria")
    
    def __repr__(self):
        return f"<DespesaCategoria {self.categoria}: R$ {self.valor_total}>"


class ProgramaGoverno(Base):
    """Programas de governo com detalhamento."""
    
    __tablename__ = "programas_governo"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Identificação
    codigo_programa = Column(String(20))  # Pode ser null se não fornecido no documento
    nome = Column(String(300), nullable=False)
    objetivo = Column(Text)
    
    # Valores
    valor_fiscal = Column(Numeric(20, 2), default=0)
    valor_seguridade = Column(Numeric(20, 2), default=0)
    valor_total = Column(Numeric(20, 2), nullable=False)
    
    # Percentuais calculados
    percentual_fiscal = Column(Numeric(5, 2))
    percentual_seguridade = Column(Numeric(5, 2))
    
    # Órgão responsável
    orgao_responsavel = Column(String(200))
    
    # Ordem de exibição (por valor decrescente geralmente)
    ordem = Column(Integer, default=0)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="programas")
    
    def __repr__(self):
        return f"<Programa {self.codigo_programa} - {self.nome}: R$ {self.valor_total}>"


class OrgaoFundo(Base):
    """Órgãos e fundos com valores totais."""
    
    __tablename__ = "orgaos_fundos"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Identificação
    codigo_orgao = Column(String(20))
    nome = Column(String(300), nullable=False)
    tipo = Column(String(50))  # Secretaria, Fundo, Autarquia, etc.
    sigla = Column(String(20))
    
    # Valores
    valor_total = Column(Numeric(20, 2), nullable=False)
    valor_fiscal = Column(Numeric(20, 2), default=0)
    valor_seguridade = Column(Numeric(20, 2), default=0)
    
    # Ordem de exibição
    ordem = Column(Integer, default=0)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="orgaos")
    
    def __repr__(self):
        return f"<Orgao {self.nome}: R$ {self.valor_total}>"


class InvestimentoRegional(Base):
    """Investimento por regional/território."""
    
    __tablename__ = "investimento_regional"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False)
    
    # Identificação
    regional_numero = Column(Integer, nullable=False)
    regional_nome = Column(String(100))
    
    # Valor - pode ser null se extraído apenas da etapa 1 (Gemini)
    # O parser determinístico (etapa 2) completará com valores reais
    valor_total = Column(Numeric(20, 2), default=0)
    
    # Bairros (JSON serializado como texto)
    bairros_json = Column(Text)  # ["Bairro1", "Bairro2", ...]
    
    # Destaques por área (JSON serializado como texto)
    # Formato: [{"categoria": "saude", "nome": "...", "descricao": "...", "prioridade": "alta"}, ...]
    destaques_json = Column(Text)
    
    # Valores por área de atuação (JSON serializado como texto)
    # Formato: {"infraestrutura": 221831234.00, "saude": 110915617.00, "educacao": 138644522.00, ...}
    valores_por_area_json = Column(Text)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="regionais")
    
    @property
    def bairros(self):
        """Retorna lista de bairros."""
        if self.bairros_json:
            return json.loads(self.bairros_json)
        return []
    
    @bairros.setter
    def bairros(self, value):
        """Define lista de bairros."""
        if value:
            self.bairros_json = json.dumps(value)
        else:
            self.bairros_json = None
    
    @property
    def destaques(self):
        """Retorna destaques."""
        if self.destaques_json:
            return json.loads(self.destaques_json)
        return {}
    
    @destaques.setter
    def destaques(self, value):
        """Define destaques."""
        if value:
            self.destaques_json = json.dumps(value)
        else:
            self.destaques_json = None
    
    def __repr__(self):
        return f"<Regional {self.regional_numero}: R$ {self.valor_total}>"


class ParticipacaoSocial(Base):
    """Dados do orçamento participativo."""
    
    __tablename__ = "participacao_social"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False, unique=True)
    
    # Indicadores
    foruns_realizados = Column(Integer, default=0)
    temas_chave = Column(Integer, default=0)
    total_priorizado = Column(Numeric(20, 2), default=0)
    rastreabilidade_percentual = Column(Numeric(5, 2), default=100)
    
    # Descrição do processo
    descricao_processo = Column(Text)
    
    # Iniciativas priorizadas (JSON serializado como texto)
    # Formato: [{"nome": "...", "valor": 123456, "descricao": "...", "categoria": "..."}, ...]
    iniciativas_json = Column(Text)
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="participacao_social")
    
    @property
    def iniciativas(self):
        """Retorna lista de iniciativas."""
        if self.iniciativas_json:
            return json.loads(self.iniciativas_json)
        return []
    
    @iniciativas.setter
    def iniciativas(self, value):
        """Define lista de iniciativas."""
        if value:
            self.iniciativas_json = json.dumps(value)
        else:
            self.iniciativas_json = None
    
    def __repr__(self):
        return f"<ParticipacaoSocial {self.foruns_realizados} fóruns, R$ {self.total_priorizado}>"


class LimiteConstitucional(Base):
    """Limites constitucionais e cumprimento."""
    
    __tablename__ = "limites_constitucionais"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    exercicio_id = Column(String(36), ForeignKey("exercicio_orcamentario.id"), nullable=False, unique=True)
    
    # Educação (mínimo 25%)
    educacao_minimo_percentual = Column(Numeric(5, 2), default=25.00)
    educacao_previsto_percentual = Column(Numeric(5, 2))
    educacao_valor = Column(Numeric(20, 2))
    educacao_cumprindo = Column(Boolean)
    
    # Saúde (mínimo 15%)
    saude_minimo_percentual = Column(Numeric(5, 2), default=15.00)
    saude_previsto_percentual = Column(Numeric(5, 2))
    saude_valor = Column(Numeric(20, 2))
    saude_cumprindo = Column(Boolean)
    
    # Pessoal (limite 54% RCL para Executivo)
    pessoal_limite_percentual = Column(Numeric(5, 2), default=54.00)
    pessoal_previsto_percentual = Column(Numeric(5, 2))
    pessoal_valor = Column(Numeric(20, 2))
    pessoal_dentro_limite = Column(Boolean)
    
    # Base de cálculo
    receita_impostos = Column(Numeric(20, 2))  # Base para educação e saúde
    receita_corrente_liquida = Column(Numeric(20, 2))  # Base para pessoal
    
    # Relacionamento
    exercicio = relationship("ExercicioOrcamentario", back_populates="limites_constitucionais")
    
    def __repr__(self):
        return f"<LimitesConstitucionais Edu:{self.educacao_previsto_percentual}% Saude:{self.saude_previsto_percentual}%>"


class ProjetoRegional(Base):
    """Projetos estratégicos por regional."""
    
    __tablename__ = "projetos_regionais"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    regional_id = Column(String(36), ForeignKey("investimento_regional.id"), nullable=False)
    
    # Identificação do projeto
    nome = Column(String(300), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(50))  # saude, infraestrutura, educacao, social, urbanismo, etc
    prioridade = Column(String(20))  # alta, media, baixa
    
    # Valores
    valor_estimado = Column(Numeric(20, 2))
    percentual_regional = Column(Numeric(5, 2))  # % do orçamento regional
    
    # Metadados
    status = Column(String(50))  # planejado, em_andamento, concluido
    previsao_conclusao = Column(String(20))  # "2026", "2025-2026", etc
    
    # Relacionamento
    regional = relationship("InvestimentoRegional", backref="projetos")
    
    def __repr__(self):
        return f"<Projeto {self.nome} - {self.categoria}>"


class SerieHistoricaReceita(Base):
    """Série histórica de receitas para gráficos de evolução."""
    
    __tablename__ = "serie_historica_receitas"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    
    # Identificação
    municipio = Column(String(100), nullable=False)
    ano = Column(Integer, nullable=False, index=True)
    
    # Valores
    receita_total = Column(Numeric(20, 2))
    receita_corrente = Column(Numeric(20, 2))
    receita_capital = Column(Numeric(20, 2))
    
    # Fonte
    fonte = Column(String(50))  # LOA, realizado, estimativa
    
    def __repr__(self):
        return f"<SerieHistorica {self.municipio} {self.ano}: R$ {self.receita_total}>"
