"""
Migration SQL para adicionar tabelas LDO.

Execute este script no PostgreSQL para criar as novas tabelas.
"""

-- =====================================================
-- MIGRATION: ADD LDO TABLES
-- Data: 09/01/2026
-- Descrição: Adiciona tabelas para armazenar dados da LDO
-- =====================================================

-- 1. Tabela de Metas e Prioridades da LDO
CREATE TABLE IF NOT EXISTS metas_prioridades_ldo (
    id VARCHAR(36) PRIMARY KEY,
    exercicio_id VARCHAR(36) NOT NULL REFERENCES exercicio_orcamentario(id) ON DELETE CASCADE,
    
    -- JSON fields
    prioridades JSON,
    diretrizes_gerais JSON,
    metas_setoriais JSON,
    programas_prioritarios JSON,
    diretrizes_setoriais JSON,
    
    CONSTRAINT uk_metas_prioridades_exercicio UNIQUE (exercicio_id)
);

CREATE INDEX idx_metas_prioridades_exercicio ON metas_prioridades_ldo(exercicio_id);

COMMENT ON TABLE metas_prioridades_ldo IS 'Armazena metas e prioridades governamentais da LDO';
COMMENT ON COLUMN metas_prioridades_ldo.prioridades IS 'Array de prioridades ordenadas por importância';
COMMENT ON COLUMN metas_prioridades_ldo.metas_setoriais IS 'Metas por setor (saúde, educação, etc)';


-- 2. Tabela de Metas Fiscais da LDO (Anexo Obrigatório LRF)
CREATE TABLE IF NOT EXISTS metas_fiscais_ldo (
    id VARCHAR(36) PRIMARY KEY,
    exercicio_id VARCHAR(36) NOT NULL REFERENCES exercicio_orcamentario(id) ON DELETE CASCADE,
    
    -- Resultado Primário
    resultado_primario_meta NUMERIC(20, 2),
    resultado_primario_ano_anterior NUMERIC(20, 2),
    resultado_primario_dois_anos_antes NUMERIC(20, 2),
    
    -- Resultado Nominal
    resultado_nominal_meta NUMERIC(20, 2),
    resultado_nominal_ano_anterior NUMERIC(20, 2),
    resultado_nominal_dois_anos_antes NUMERIC(20, 2),
    
    -- Dívida Consolidada
    divida_consolidada_meta NUMERIC(20, 2),
    divida_consolidada_percentual_rcl NUMERIC(5, 2),
    divida_consolidada_ano_anterior NUMERIC(20, 2),
    divida_consolidada_dois_anos_antes NUMERIC(20, 2),
    
    -- Dívida Líquida
    divida_liquida_meta NUMERIC(20, 2),
    divida_liquida_percentual_rcl NUMERIC(5, 2),
    divida_liquida_ano_anterior NUMERIC(20, 2),
    
    -- RCL
    rcl_prevista NUMERIC(20, 2),
    rcl_ano_anterior NUMERIC(20, 2),
    rcl_dois_anos_antes NUMERIC(20, 2),
    
    -- Receitas e Despesas
    receita_total_prevista NUMERIC(20, 2),
    despesa_total_prevista NUMERIC(20, 2),
    
    -- Projeções e premissas (JSON)
    projecoes_trienio JSON,
    premissas_macroeconomicas JSON,
    
    -- Margem de expansão
    margem_expansao_despesas_obrigatorias NUMERIC(20, 2),
    
    -- Renúncias de receita
    renuncias_receita_total NUMERIC(20, 2),
    renuncias_receita_detalhes JSON,
    
    -- Metodologia e observações
    metodologia_calculo TEXT,
    observacoes TEXT,
    
    CONSTRAINT uk_metas_fiscais_exercicio UNIQUE (exercicio_id)
);

CREATE INDEX idx_metas_fiscais_exercicio ON metas_fiscais_ldo(exercicio_id);

COMMENT ON TABLE metas_fiscais_ldo IS 'Anexo de Metas Fiscais da LDO (obrigatório por LRF)';
COMMENT ON COLUMN metas_fiscais_ldo.resultado_primario_meta IS 'Meta de resultado primário para o exercício';
COMMENT ON COLUMN metas_fiscais_ldo.projecoes_trienio IS 'Projeções para os 3 anos seguintes';


-- 3. Tabela de Riscos Fiscais da LDO (Anexo Obrigatório LRF)
CREATE TABLE IF NOT EXISTS riscos_fiscais_ldo (
    id VARCHAR(36) PRIMARY KEY,
    exercicio_id VARCHAR(36) NOT NULL REFERENCES exercicio_orcamentario(id) ON DELETE CASCADE,
    
    -- Riscos identificados (JSON array)
    riscos JSON,
    
    -- Passivos Contingentes
    passivos_contingentes_total NUMERIC(20, 2),
    passivos_contingentes_detalhes JSON,
    
    -- Demandas Judiciais
    demandas_judiciais_total NUMERIC(20, 2),
    demandas_judiciais_detalhes JSON,
    
    -- Garantias Concedidas
    garantias_concedidas_total NUMERIC(20, 2),
    garantias_concedidas_detalhes JSON,
    
    -- Operações de Crédito
    operacoes_credito_riscos JSON,
    
    -- Riscos Macroeconômicos
    riscos_macroeconomicos JSON,
    
    -- Riscos Específicos do Município
    riscos_especificos_municipio JSON,
    
    -- Avaliação Geral
    avaliacao_geral_risco VARCHAR(20),  -- baixo | moderado | alto | critico
    total_exposicao_risco NUMERIC(20, 2),
    percentual_exposicao_orcamento NUMERIC(5, 2),
    
    CONSTRAINT uk_riscos_fiscais_exercicio UNIQUE (exercicio_id)
);

CREATE INDEX idx_riscos_fiscais_exercicio ON riscos_fiscais_ldo(exercicio_id);

COMMENT ON TABLE riscos_fiscais_ldo IS 'Anexo de Riscos Fiscais da LDO (obrigatório por LRF)';
COMMENT ON COLUMN riscos_fiscais_ldo.riscos IS 'Array de riscos identificados com impactos e probabilidades';
COMMENT ON COLUMN riscos_fiscais_ldo.passivos_contingentes_total IS 'Total de passivos contingentes (processos, garantias, etc)';


-- 4. Tabela de Políticas Setoriais da LDO
CREATE TABLE IF NOT EXISTS politicas_setoriais_ldo (
    id VARCHAR(36) PRIMARY KEY,
    exercicio_id VARCHAR(36) NOT NULL REFERENCES exercicio_orcamentario(id) ON DELETE CASCADE,
    
    -- Políticas por setor (JSON)
    politicas JSON,
    
    CONSTRAINT uk_politicas_setoriais_exercicio UNIQUE (exercicio_id)
);

CREATE INDEX idx_politicas_setoriais_exercicio ON politicas_setoriais_ldo(exercicio_id);

COMMENT ON TABLE politicas_setoriais_ldo IS 'Políticas e diretrizes setoriais detalhadas da LDO';
COMMENT ON COLUMN politicas_setoriais_ldo.politicas IS 'JSON com políticas por setor (saúde, educação, etc)';


-- 5. Tabela de Avaliação do Ano Anterior
CREATE TABLE IF NOT EXISTS avaliacao_anterior_ldo (
    id VARCHAR(36) PRIMARY KEY,
    exercicio_id VARCHAR(36) NOT NULL REFERENCES exercicio_orcamentario(id) ON DELETE CASCADE,
    
    -- Ano avaliado
    ano_avaliado INTEGER,
    
    -- Avaliação de metas (JSON)
    metas_fiscais_cumpridas JSON,
    metas_setoriais_cumpridas JSON,
    
    -- Avaliação geral
    avaliacao_geral TEXT,
    percentual_geral_cumprimento NUMERIC(5, 2),
    
    -- Justificativas (JSON array)
    justificativas_nao_cumprimento JSON,
    
    CONSTRAINT uk_avaliacao_anterior_exercicio UNIQUE (exercicio_id)
);

CREATE INDEX idx_avaliacao_anterior_exercicio ON avaliacao_anterior_ldo(exercicio_id);
CREATE INDEX idx_avaliacao_anterior_ano ON avaliacao_anterior_ldo(ano_avaliado);

COMMENT ON TABLE avaliacao_anterior_ldo IS 'Avaliação do cumprimento das metas do ano anterior';
COMMENT ON COLUMN avaliacao_anterior_ldo.metas_fiscais_cumpridas IS 'Comparativo meta vs realizado do ano anterior';


-- =====================================================
-- GRANTS (ajuste conforme seu usuário)
-- =====================================================

-- Se necessário, conceder permissões
-- GRANT ALL ON metas_prioridades_ldo TO seu_usuario;
-- GRANT ALL ON metas_fiscais_ldo TO seu_usuario;
-- GRANT ALL ON riscos_fiscais_ldo TO seu_usuario;
-- GRANT ALL ON politicas_setoriais_ldo TO seu_usuario;
-- GRANT ALL ON avaliacao_anterior_ldo TO seu_usuario;


-- =====================================================
-- VERIFICAÇÃO
-- =====================================================

-- Verificar se as tabelas foram criadas
SELECT 
    tablename, 
    schemaname
FROM pg_tables 
WHERE tablename LIKE '%_ldo'
ORDER BY tablename;

-- Contar registros (deve retornar 0 inicialmente)
SELECT 
    'metas_prioridades_ldo' AS tabela, COUNT(*) AS registros FROM metas_prioridades_ldo
UNION ALL
SELECT 'metas_fiscais_ldo', COUNT(*) FROM metas_fiscais_ldo
UNION ALL
SELECT 'riscos_fiscais_ldo', COUNT(*) FROM riscos_fiscais_ldo
UNION ALL
SELECT 'politicas_setoriais_ldo', COUNT(*) FROM politicas_setoriais_ldo
UNION ALL
SELECT 'avaliacao_anterior_ldo', COUNT(*) FROM avaliacao_anterior_ldo;


-- =====================================================
-- ROLLBACK (em caso de necessidade)
-- =====================================================

-- Para desfazer a migration, execute:
-- DROP TABLE IF EXISTS avaliacao_anterior_ldo CASCADE;
-- DROP TABLE IF EXISTS politicas_setoriais_ldo CASCADE;
-- DROP TABLE IF EXISTS riscos_fiscais_ldo CASCADE;
-- DROP TABLE IF EXISTS metas_fiscais_ldo CASCADE;
-- DROP TABLE IF EXISTS metas_prioridades_ldo CASCADE;

