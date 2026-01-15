"""
Prompts para extração de dados de LDO (Lei de Diretrizes Orçamentárias).

Este módulo contém prompts genéricos e poderosos que funcionam para
qualquer município brasileiro, capturando o máximo de dados possível.
"""

def build_ldo_extraction_prompt() -> str:
    """
    Prompt UNIVERSAL e PODEROSO para extração de dados de LDO.
    
    Funciona para qualquer município brasileiro.
    Captura todos os anexos obrigatórios da LRF e dados estratégicos.
    """
    
    return '''# 🏛️ LDO EXTRACTION - UNIVERSAL SCHEMA FOR BRAZILIAN MUNICIPALITIES

Você está extraindo dados de uma **LDO (Lei de Diretrizes Orçamentárias)** de um município brasileiro.

A LDO é o documento que define as **metas, prioridades e riscos fiscais** para o ano seguinte.
É OBRIGATÓRIO por lei (LRF - Lei de Responsabilidade Fiscal) e contém anexos específicos.

## 🎯 OBJETIVO

Extrair o **MÁXIMO de informações estratégicas** possível, mesmo que estejam em formatos diferentes ou não padronizados.

## ⚠️ REGRAS CRÍTICAS (NUNCA VIOLE)

1. **TODOS os valores monetários** devem ser NÚMEROS puros: 14776973233.00 (NÃO "R$ 14,7 bi")
2. **SE NÃO ENCONTRAR** um dado, use `null` para valores e `[]` para arrays
3. **NÃO INVENTE DADOS** - se não está no documento, retorne null
4. **ARRAYS VAZIOS** devem ser `[]`, nunca null ou string
5. **O tipo_documento** deve ser exatamente "LDO"
6. **Seja FLEXÍVEL** - municípios usam terminologias diferentes (adapte!)

## 📊 SCHEMA JSON EXATO (COPIE A ESTRUTURA)

```json
{
  "metadados": {
    "tipo_documento": "LDO",
    "ano_exercicio": 2025,
    "ano_referencia": 2026,
    "municipio": "Nome do Município",
    "estado": "UF",
    "prefeito": "Nome do Prefeito",
    "documento_legal": "Lei nº XXX de DD/MM/AAAA",
    "data_publicacao": "2024-12-15"
  },
  
  "metas_prioridades": {
    "prioridades": [
      {
        "ordem": 1,
        "setor": "Educação",
        "titulo": "Ampliar e qualificar rede municipal de educação",
        "descricao": "Descrição detalhada da prioridade...",
        "justificativa": "Por que esta é uma prioridade...",
        "meta_quantitativa": "Aumentar cobertura em 20%",
        "indicador": "Taxa de cobertura escolar",
        "prazo": "Dezembro/2026"
      }
    ],
    "diretrizes_gerais": [
      "Garantir equilíbrio fiscal",
      "Priorizar investimentos em áreas sociais",
      "Reduzir custos administrativos"
    ],
    "metas_setoriais": {
      "saude": {
        "meta": "Reduzir mortalidade infantil",
        "indicador": "Taxa de mortalidade infantil",
        "valor_atual": 12.3,
        "valor_meta": 10.5,
        "unidade": "por mil nascidos vivos",
        "recursos_necessarios": 50000000.00
      },
      "educacao": {
        "meta": "Elevar IDEB",
        "indicador": "IDEB Anos Iniciais",
        "valor_atual": 5.8,
        "valor_meta": 6.2,
        "unidade": "índice",
        "recursos_necessarios": 80000000.00
      }
    },
    "programas_prioritarios": [
      {
        "codigo": "0042",
        "nome": "Desenvolvimento do Ensino Fundamental",
        "justificativa": "Essencial para melhoria da educação"
      }
    ],
    "diretrizes_setoriais": {
      "saude": [
        "Fortalecer atenção básica",
        "Ampliar cobertura hospitalar",
        "Investir em prevenção"
      ],
      "educacao": [
        "Melhorar infraestrutura escolar",
        "Capacitar professores",
        "Ampliar ensino integral"
      ]
    }
  },
  
  "metas_fiscais": {
    "resultado_primario": {
      "meta": 450000000.00,
      "ano_anterior": 380000000.00,
      "dois_anos_antes": 320000000.00
    },
    "resultado_nominal": {
      "meta": 180000000.00,
      "ano_anterior": 210000000.00,
      "dois_anos_antes": 195000000.00
    },
    "divida_consolidada": {
      "meta": 2500000000.00,
      "percentual_rcl": 45.5,
      "ano_anterior": 2450000000.00,
      "dois_anos_antes": 2380000000.00
    },
    "divida_liquida": {
      "meta": 2200000000.00,
      "percentual_rcl": 40.0,
      "ano_anterior": 2150000000.00
    },
    "rcl_prevista": 5500000000.00,
    "rcl_ano_anterior": 5200000000.00,
    "rcl_dois_anos_antes": 4900000000.00,
    "receita_total_prevista": 15000000000.00,
    "despesa_total_prevista": 14850000000.00,
    "projecoes_trienio": {
      "2026": {
        "receita_total": 15500000000.00,
        "despesa_total": 15200000000.00,
        "resultado_primario": 300000000.00,
        "resultado_nominal": 180000000.00,
        "divida_consolidada": 2600000000.00,
        "rcl": 5800000000.00
      },
      "2027": {
        "receita_total": 16300000000.00,
        "despesa_total": 16000000000.00,
        "resultado_primario": 300000000.00,
        "resultado_nominal": 180000000.00,
        "divida_consolidada": 2700000000.00,
        "rcl": 6100000000.00
      },
      "2028": {
        "receita_total": 17100000000.00,
        "despesa_total": 16800000000.00,
        "resultado_primario": 300000000.00,
        "resultado_nominal": 180000000.00,
        "divida_consolidada": 2750000000.00,
        "rcl": 6400000000.00
      }
    },
    "premissas_macroeconomicas": {
      "pib_crescimento": 2.5,
      "inflacao_ipca": 4.0,
      "inflacao_igpm": 3.8,
      "taxa_selic": 10.5,
      "cambio_dolar": 5.20,
      "salario_minimo": 1412.00,
      "crescimento_transferencias_federais": 1.8
    },
    "margem_expansao_despesas_obrigatorias": 120000000.00,
    "renuncias_receita": {
      "total": 85000000.00,
      "detalhes": [
        {
          "tipo": "IPTU",
          "valor": 50000000.00,
          "justificativa": "Incentivo à regularização"
        },
        {
          "tipo": "ISS",
          "valor": 30000000.00,
          "justificativa": "Apoio a pequenos empresários"
        }
      ]
    },
    "metodologia_calculo": "Texto explicando a metodologia...",
    "observacoes": "Observações gerais sobre as metas fiscais..."
  },
  
  "riscos_fiscais": {
    "riscos": [
      {
        "categoria": "receita",
        "subcategoria": "arrecadacao",
        "titulo": "Frustração de Receita de ICMS",
        "descricao": "Possível redução da arrecadação de ICMS devido a fatores econômicos...",
        "impacto_estimado": 150000000.00,
        "impacto_percentual_orcamento": 1.5,
        "probabilidade": "media",
        "nivel_risco": "alto",
        "providencias_mitigacao": "Revisão trimestral de metas, contingenciamento de despesas discricionárias",
        "fonte": "Estudos CONFAZ",
        "historico": "Em 2023 houve redução de 8% na arrecadação"
      },
      {
        "categoria": "despesa",
        "subcategoria": "pessoal",
        "titulo": "Aumento de Despesas com Pessoal",
        "descricao": "Possíveis reajustes salariais acima do previsto",
        "impacto_estimado": 80000000.00,
        "impacto_percentual_orcamento": 0.8,
        "probabilidade": "alta",
        "nivel_risco": "medio",
        "providencias_mitigacao": "Reserva de contingência de 2%",
        "fonte": "Negociações sindicais",
        "historico": null
      }
    ],
    "passivos_contingentes": {
      "total": 320000000.00,
      "detalhes": [
        {
          "tipo": "trabalhista",
          "quantidade_processos": 45,
          "valor_total": 85000000.00,
          "valor_provisionado": 12000000.00,
          "probabilidade_perda": "possivel",
          "descricao": "Ações trabalhistas de servidores municipais"
        },
        {
          "tipo": "civel",
          "quantidade_processos": 120,
          "valor_total": 180000000.00,
          "valor_provisionado": 25000000.00,
          "probabilidade_perda": "possivel",
          "descricao": "Ações de indenização diversas"
        }
      ]
    },
    "demandas_judiciais": {
      "total": 45000000.00,
      "detalhes": [
        {
          "tipo": "precatorio",
          "quantidade": 120,
          "valor_total": 45000000.00,
          "ano_inscricao": 2024,
          "previsao_pagamento": "2025-2026"
        }
      ]
    },
    "garantias_concedidas": {
      "total": 0.00,
      "detalhes": []
    },
    "operacoes_credito_riscos": [
      {
        "contrato": "Empréstimo BID 12345",
        "valor_principal": 500000000.00,
        "saldo_devedor": 320000000.00,
        "risco": "Variação cambial",
        "impacto_estimado": 50000000.00
      }
    ],
    "riscos_macroeconomicos": {
      "inflacao_acima_previsto": {
        "impacto": 80000000.00,
        "probabilidade": "media"
      },
      "queda_pib": {
        "impacto": 120000000.00,
        "probabilidade": "baixa"
      },
      "alta_juros": {
        "impacto": 35000000.00,
        "probabilidade": "media"
      }
    },
    "riscos_especificos_municipio": [],
    "avaliacao_geral_risco": "moderado",
    "total_exposicao_risco": 450000000.00,
    "percentual_exposicao_orcamento": 3.0
  },
  
  "politicas_setoriais": {
    "saude": {
      "diretrizes": [
        "Fortalecer atenção básica",
        "Ampliar rede hospitalar",
        "Investir em prevenção"
      ],
      "programas_prioritarios": [
        "Saúde da Família",
        "UPA 24h",
        "Hospitais Regionais"
      ],
      "metas": [
        {
          "descricao": "Reduzir mortalidade infantil",
          "indicador": "Taxa por mil nascidos vivos",
          "meta": 10.5,
          "atual": 12.3
        }
      ],
      "recursos_estimados": 2800000000.00,
      "percentual_orcamento": 18.9,
      "acoes_principais": [
        "Ampliar equipes de saúde da família",
        "Construir novas UPAs",
        "Capacitar profissionais"
      ]
    },
    "educacao": {
      "diretrizes": [
        "Melhorar infraestrutura escolar",
        "Capacitar professores",
        "Ampliar ensino integral"
      ],
      "programas_prioritarios": [
        "Educação Infantil",
        "Ensino Fundamental",
        "Educação de Jovens e Adultos"
      ],
      "metas": [
        {
          "descricao": "Elevar IDEB",
          "indicador": "IDEB Anos Iniciais",
          "meta": 6.2,
          "atual": 5.8
        }
      ],
      "recursos_estimados": 3500000000.00,
      "percentual_orcamento": 23.5,
      "acoes_principais": [
        "Construir novas escolas",
        "Reformar escolas existentes",
        "Ampliar ensino integral"
      ]
    }
  },
  
  "avaliacao_ano_anterior": {
    "ano_avaliado": 2024,
    "metas_fiscais_cumpridas": {
      "resultado_primario": {
        "meta": 380000000.00,
        "realizado": 420000000.00,
        "percentual_cumprimento": 110.5,
        "status": "superado"
      },
      "resultado_nominal": {
        "meta": 210000000.00,
        "realizado": 195000000.00,
        "percentual_cumprimento": 92.9,
        "status": "parcialmente_cumprido"
      },
      "divida_consolidada": {
        "meta": 2450000000.00,
        "realizado": 2380000000.00,
        "percentual_cumprimento": 102.9,
        "status": "cumprido"
      }
    },
    "metas_setoriais_cumpridas": {
      "saude": {
        "meta": "Reduzir mortalidade infantil para 11.0",
        "realizado": "11.8",
        "status": "parcialmente_cumprido",
        "justificativa": "Houve avanços mas não atingiu a meta devido a..."
      },
      "educacao": {
        "meta": "Elevar IDEB para 6.0",
        "realizado": "5.8",
        "status": "nao_cumprido",
        "justificativa": "Dificuldades estruturais impediram o cumprimento..."
      }
    },
    "avaliacao_geral": "O município cumpriu a maioria das metas fiscais, com destaque para o resultado primário que superou as expectativas...",
    "percentual_geral_cumprimento": 85.5,
    "justificativas_nao_cumprimento": [
      "Redução inesperada de transferências federais",
      "Aumento de despesas com saúde devido à pandemia"
    ]
  }
}
```

## 🔍 INSTRUÇÕES DE EXTRAÇÃO

### 1. **METADADOS**
- Busque no cabeçalho: "Lei nº XXX", "Prefeito", data
- Ano de referência é o ano SEGUINTE ao da publicação (LDO 2024 → exercício 2025)

### 2. **METAS E PRIORIDADES**
- Podem estar em: "Prioridades e Metas", "Anexo de Prioridades", "Diretrizes Gerais"
- Ordem de prioridade: buscar termos como "I -", "Prioridade 1", "Primeiro"
- Adapte terminologias: "Diretriz" = "Prioridade", "Meta Estratégica" = "Prioridade"

### 3. **METAS FISCAIS** (OBRIGATÓRIO POR LEI)
- Geralmente em: "Anexo de Metas Fiscais", "Demonstrativo I", "Tabela 1"
- Buscar tabelas com anos (2024, 2025, 2026)
- Valores podem estar em "milhares", "milhões" ou "reais" - **CONVERTA SEMPRE PARA REAIS**
- Se tabela mostra valores negativos entre parênteses: (150.000) = -150000.00

### 4. **RISCOS FISCAIS** (OBRIGATÓRIO POR LEI)
- Geralmente em: "Anexo de Riscos Fiscais", "Demonstrativo II"
- Categorias comuns:
  - **Receita**: frustração de arrecadação, variação de transferências
  - **Despesa**: aumento de pessoal, demandas judiciais, obras
  - **Dívida**: variação cambial, alta de juros
  - **Judicial**: processos trabalhistas, ações cíveis, precatórios
- Probabilidade: buscar "provável", "possível", "remota" → "alta", "media", "baixa"
- Nível de risco: buscar "crítico", "relevante", "baixo" → "alto", "medio", "baixo"

### 5. **POLÍTICAS SETORIAIS**
- Podem estar dispersas ao longo do documento
- Buscar capítulos por área: "Saúde", "Educação", "Assistência Social", etc
- Extrair diretrizes, programas e metas de cada área

### 6. **AVALIAÇÃO ANO ANTERIOR**
- Pode estar em: "Avaliação do Cumprimento de Metas", "Prestação de Contas LDO Anterior"
- Comparar metas estabelecidas vs realizadas
- Status: "cumprido" (90-110%), "superado" (>110%), "parcialmente" (70-90%), "não cumprido" (<70%)

## ⚡ ESTRATÉGIAS DE ADAPTAÇÃO

### Terminologia Variável:
- "Diretriz" = "Prioridade" = "Meta Estratégica" = "Objetivo Prioritário"
- "Resultado Primário" = "Superavit Primário" = "Economia Primária"
- "RCL" = "Receita Corrente Líquida" = "Receita Líquida Corrente"
- "Passivo Contingente" = "Riscos Passivos" = "Demandas Contingentes"

### Valores em Diferentes Unidades:
```
"150 milhões" → 150000000.00
"R$ 1,5 bi" → 1500000000.00
"1.500.000" (milhares de reais) → 1500000000.00
"(80.000)" (negativo) → -80000000.00
```

### Tabelas Complexas:
- Se tabela tem múltiplas colunas (2023, 2024, 2025), identifique o ano correto
- Se valores estão em % da RCL, MANTENHA os dois: valor absoluto E percentual

## 🎯 PRIORIZAÇÃO (do mais importante ao menos importante)

1. **OBRIGATÓRIO (LRF):**
   - Metas Fiscais (resultado primário, nominal, dívida, RCL)
   - Riscos Fiscais (passivos contingentes, demandas judiciais)

2. **ALTAMENTE RELEVANTE:**
   - Prioridades governamentais (top 5)
   - Diretrizes gerais
   - Projeções plurianuais

3. **RELEVANTE:**
   - Metas setoriais
   - Políticas setoriais detalhadas
   - Programas prioritários

4. **COMPLEMENTAR:**
   - Avaliação ano anterior
   - Premissas macroeconômicas
   - Riscos específicos do município

## ✅ VALIDAÇÃO FINAL

Antes de retornar, verifique:
- [ ] Todos os valores monetários são NÚMEROS
- [ ] Arrays vazios são `[]`, não null
- [ ] tipo_documento = "LDO"
- [ ] ano_exercicio correto (ano da publicação)
- [ ] ano_referencia correto (ano seguinte)
- [ ] Resultado primário e nominal extraídos (obrigatórios)
- [ ] Pelo menos 3 riscos fiscais identificados

## 🚀 IMPORTANTE

**SE O DOCUMENTO NÃO SEGUIR PADRÕES:**
- Seja criativo na busca de informações
- Adapte terminologias
- Priorize anexos obrigatórios
- Se algo estiver mal formatado, tente extrair mesmo assim
- Se não encontrar, retorne null/[]

**NUNCA INVENTE DADOS** - se não está no documento, retorne null.

Agora, extraia TODOS os dados da LDO fornecida!
'''


def build_ldo_validation_prompt(extracted_data: dict) -> str:
    """
    Prompt para validar e enriquecer dados extraídos da LDO.
    
    Usado em segunda passagem para garantir qualidade.
    """
    
    return f'''# VALIDAÇÃO E ENRIQUECIMENTO DE DADOS LDO

Você recebeu dados extraídos de uma LDO. Sua tarefa é VALIDAR e ENRIQUECER.

## DADOS EXTRAÍDOS

```json
{extracted_data}
```

## TAREFAS

### 1. VALIDAÇÃO
- Verifique se todos os valores monetários são números
- Confirme se arrays vazios são [] (não null)
- Valide se as metas fiscais estão consistentes
- Verifique se os riscos têm categorias válidas

### 2. ENRIQUECIMENTO
- Adicione contexto onde possível
- Calcule percentuais faltantes
- Interpole dados ausentes (se possível)
- Adicione observações relevantes

### 3. CORREÇÕES
- Corrija tipos de dados incorretos
- Normalize terminologias
- Ajuste formatações

Retorne o JSON CORRIGIDO e ENRIQUECIDO.
'''

