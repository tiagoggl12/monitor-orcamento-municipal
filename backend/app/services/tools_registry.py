"""
Tools Registry for Gemini Function Calling
===========================================

Define todas as ferramentas (tools) que o Gemini pode usar para
buscar dados de forma inteligente e estruturada.
"""

from typing import Dict, List, Any

# Definição das ferramentas seguindo o formato do Gemini Function Calling
# https://ai.google.dev/gemini-api/docs/function-calling


TOOL_SEARCH_LICITACOES = {
    "name": "search_licitacoes",
    "description": (
        "Busca licitações do Portal da Transparência com filtros específicos. "
        "Use esta ferramenta quando o usuário perguntar sobre licitações, editais, "
        "pregões, concorrências, ou qualquer processo licitatório. "
        "Você pode filtrar por órgão (ORIGEM), número de edital, modalidade, "
        "intervalo de datas, ou valores. Use filtros sempre que possível para "
        "aumentar a precisão dos resultados."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Texto da busca semântica. Descreva o que está buscando de forma "
                    "natural, por exemplo: 'aquisição de materiais de informática', "
                    "'serviços de manutenção', 'obras de infraestrutura'."
                )
            },
            "origem": {
                "type": "string",
                "description": (
                    "Nome do órgão responsável pela licitação. Exemplos: 'SEINF', 'SME', "
                    "'SMS', 'IJF', 'URBFOR'. Use MAIÚSCULAS e a sigla exata do órgão. "
                    "IMPORTANTE: Se o usuário mencionar um órgão específico, SEMPRE use este filtro."
                )
            },
            "edital": {
                "type": "integer",
                "description": "Número específico do edital. Exemplo: 10365"
            },
            "edital_min": {
                "type": "integer",
                "description": "Número mínimo do edital para busca em intervalo"
            },
            "edital_max": {
                "type": "integer",
                "description": "Número máximo do edital para busca em intervalo"
            },
            "modalidade": {
                "type": "string",
                "description": (
                    "Modalidade da licitação. Valores comuns: 'PE' (Pregão Eletrônico), "
                    "'CC' (Carta Convite), 'TP' (Tomada de Preços), 'CN' (Concorrência). "
                    "Use MAIÚSCULAS."
                )
            },
            "data_inicio": {
                "type": "string",
                "description": "Data inicial no formato YYYY-MM-DD. Exemplo: '2024-01-01'"
            },
            "data_fim": {
                "type": "string",
                "description": "Data final no formato YYYY-MM-DD. Exemplo: '2024-12-31'"
            },
            "valor_min": {
                "type": "number",
                "description": "Valor mínimo da licitação em reais"
            },
            "valor_max": {
                "type": "number",
                "description": "Valor máximo da licitação em reais"
            },
            "limit": {
                "type": "integer",
                "description": "Número máximo de resultados a retornar. Padrão: 5"
            }
        },
        "required": ["query"]
    }
}


TOOL_SEARCH_LOA = {
    "name": "search_loa",
    "description": (
        "Busca dados na LOA (Lei Orçamentária Anual) - o orçamento detalhado do município. "
        "Use esta ferramenta quando o usuário perguntar sobre orçamento, despesas previstas, "
        "dotações orçamentárias, programas, ações, funções, subfunções, ou qualquer informação "
        "relacionada ao planejamento financeiro anual. Você pode filtrar por ano, órgão, "
        "função orçamentária, programa, ou ação."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Texto da busca semântica. Descreva o que está buscando, por exemplo: "
                    "'despesas com educação', 'programa de saúde básica', "
                    "'ação de pavimentação de ruas'."
                )
            },
            "ano": {
                "type": "integer",
                "description": "Ano da LOA. Exemplo: 2024"
            },
            "orgao": {
                "type": "string",
                "description": (
                    "Nome ou código do órgão. Exemplos: 'SEINF', 'Secretaria de Educação'. "
                    "Se o usuário mencionar um órgão, SEMPRE use este filtro."
                )
            },
            "funcao": {
                "type": "string",
                "description": (
                    "Função orçamentária. Exemplos: 'Educação', 'Saúde', 'Urbanismo', "
                    "'Transporte', 'Segurança Pública'."
                )
            },
            "programa": {
                "type": "string",
                "description": "Nome do programa orçamentário"
            },
            "acao": {
                "type": "string",
                "description": "Nome da ação orçamentária"
            },
            "limit": {
                "type": "integer",
                "description": "Número máximo de resultados a retornar. Padrão: 5"
            }
        },
        "required": ["query"]
    }
}


TOOL_SEARCH_LDO = {
    "name": "search_ldo",
    "description": (
        "Busca dados na LDO (Lei de Diretrizes Orçamentárias) - as diretrizes e metas "
        "para elaboração do orçamento. Use esta ferramenta quando o usuário perguntar sobre "
        "prioridades orçamentárias, metas fiscais, políticas de aplicação, ou diretrizes "
        "para o orçamento anual."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Texto da busca semântica. Descreva o que está buscando, por exemplo: "
                    "'metas fiscais para 2024', 'prioridades da administração', "
                    "'política de aplicação de recursos'."
                )
            },
            "ano": {
                "type": "integer",
                "description": "Ano da LDO. Exemplo: 2024"
            },
            "limit": {
                "type": "integer",
                "description": "Número máximo de resultados a retornar. Padrão: 5"
            }
        },
        "required": ["query"]
    }
}


TOOL_CROSS_REFERENCE = {
    "name": "cross_reference",
    "description": (
        "Cruza dados entre Portal da Transparência (licitações, contratos, empenhos), "
        "LOA (orçamento) e LDO (diretrizes). Use esta ferramenta quando o usuário pedir "
        "análises comparativas, como: 'comparar licitações da SEINF com o orçamento previsto', "
        "'verificar se os gastos estão de acordo com as prioridades da LDO', "
        "'analisar execução orçamentária vs licitações realizadas'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "analysis_type": {
                "type": "string",
                "enum": [
                    "licitacoes_vs_orcamento",
                    "despesas_vs_prioridades",
                    "execucao_vs_planejamento",
                    "orgao_completo"
                ],
                "description": (
                    "Tipo de análise cruzada: "
                    "'licitacoes_vs_orcamento' - Compara licitações realizadas com orçamento previsto. "
                    "'despesas_vs_prioridades' - Compara despesas com prioridades da LDO. "
                    "'execucao_vs_planejamento' - Compara execução real com planejamento. "
                    "'orgao_completo' - Análise completa de um órgão específico."
                )
            },
            "orgao": {
                "type": "string",
                "description": "Nome do órgão para análise. Exemplo: 'SEINF', 'SME'"
            },
            "ano": {
                "type": "integer",
                "description": "Ano para análise. Exemplo: 2024"
            },
            "periodo_inicio": {
                "type": "string",
                "description": "Período inicial no formato YYYY-MM-DD"
            },
            "periodo_fim": {
                "type": "string",
                "description": "Período final no formato YYYY-MM-DD"
            }
        },
        "required": ["analysis_type"]
    }
}


TOOL_ANALYZE_BUDGET_EXECUTION = {
    "name": "analyze_budget_execution",
    "description": (
        "Analisa a execução orçamentária, comparando valores empenhados, liquidados e pagos "
        "com as dotações previstas. Use quando o usuário perguntar sobre percentual de execução, "
        "recursos não utilizados, ou desempenho na execução do orçamento."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "orgao": {
                "type": "string",
                "description": "Órgão específico para análise"
            },
            "funcao": {
                "type": "string",
                "description": "Função orçamentária específica"
            },
            "ano": {
                "type": "integer",
                "description": "Ano para análise"
            },
            "periodo_inicio": {
                "type": "string",
                "description": "Período inicial (YYYY-MM-DD)"
            },
            "periodo_fim": {
                "type": "string",
                "description": "Período final (YYYY-MM-DD)"
            }
        },
        "required": []
    }
}


# Registry completo de ferramentas
TOOLS_REGISTRY = [
    TOOL_SEARCH_LICITACOES,
    TOOL_SEARCH_LOA,
    TOOL_SEARCH_LDO,
    TOOL_CROSS_REFERENCE,
    TOOL_ANALYZE_BUDGET_EXECUTION
]


def get_tools() -> List[Dict[str, Any]]:
    """
    Retorna lista de todas as ferramentas disponíveis
    
    Returns:
        Lista de dicionários com definição das ferramentas
    """
    return TOOLS_REGISTRY


def get_tool_by_name(tool_name: str) -> Dict[str, Any]:
    """
    Retorna definição de uma ferramenta específica pelo nome
    
    Args:
        tool_name: Nome da ferramenta
        
    Returns:
        Definição da ferramenta
        
    Raises:
        ValueError: Se a ferramenta não existir
    """
    for tool in TOOLS_REGISTRY:
        if tool["name"] == tool_name:
            return tool
    
    raise ValueError(f"Tool '{tool_name}' not found in registry")


def get_tools_summary() -> str:
    """
    Retorna resumo textual de todas as ferramentas disponíveis
    (útil para incluir no system prompt)
    
    Returns:
        String com resumo das ferramentas
    """
    summary = "FERRAMENTAS DISPONÍVEIS:\n\n"
    
    for tool in TOOLS_REGISTRY:
        summary += f"- **{tool['name']}**: {tool['description']}\n\n"
    
    summary += "\nUSO: Analise a pergunta do usuário e decida quais ferramentas usar. "
    summary += "Você pode chamar múltiplas ferramentas sequencialmente se necessário. "
    summary += "SEMPRE use filtros específicos (origem, edital, ano) quando mencionados pelo usuário."
    
    return summary

