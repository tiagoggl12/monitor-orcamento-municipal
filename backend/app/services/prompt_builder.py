"""
Construtor de prompts estruturados para o Gemini AI.

Este módulo constrói prompts otimizados que guiam o Gemini a:
1. Analisar a pergunta do usuário
2. Buscar contexto relevante (LOA/LDO e Portal)
3. Cruzar dados de múltiplas fontes
4. Gerar respostas estruturadas em JSON
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class PromptBuilder:
    """Construtor de prompts para o Gemini AI."""

    def __init__(self):
        self.system_context = self._build_system_context()

    def _build_system_context(self) -> str:
        """Constrói o contexto do sistema que define o papel do Gemini."""
        return """Você é um assistente especializado em análise de orçamento público municipal.

Seu papel é ajudar cidadãos a entender como o dinheiro público é planejado e executado,
cruzando dados da Lei Orçamentária Anual (LOA) e Lei de Diretrizes Orçamentárias (LDO)
com dados reais de execução orçamentária do Portal da Transparência.

CAPACIDADES:
- Analisar documentos orçamentários (LOA/LDO)
- Consultar dados de execução do Portal da Transparência
- Cruzar dados planejados vs executados
- Identificar desvios, tendências e anomalias
- Gerar explicações claras e acessíveis
- Criar visualizações (gráficos, tabelas, métricas)

PRINCÍPIOS:
- Transparência: Sempre cite fontes de dados
- Clareza: Use linguagem acessível, evite jargões
- Precisão: Base respostas em dados reais
- Contexto: Explique o significado dos números
- Imparcialidade: Apresente fatos, não opiniões
"""

    def _build_response_format_instructions(self) -> str:
        """Instruções sobre o formato de resposta esperado."""
        return """FORMATO DE RESPOSTA:

Você DEVE retornar uma resposta estruturada em JSON seguindo este formato EXATO:

{
  "components": [
    {
      "type": "text",
      "content": "Texto em Markdown explicando a resposta"
    },
    {
      "type": "metric",
      "label": "Rótulo da métrica",
      "value": "Valor formatado",
      "change": "+15%" (opcional),
      "trend": "up|down|neutral" (opcional)
    },
    {
      "type": "chart",
      "chart_type": "bar|line|pie|area",
      "title": "Título do gráfico",
      "data": {
        "labels": ["Label1", "Label2"],
        "datasets": [
          {
            "label": "Dataset 1",
            "data": [100, 200]
          }
        ]
      }
    },
    {
      "type": "table",
      "title": "Título da tabela",
      "columns": ["Coluna1", "Coluna2"],
      "rows": [
        ["Valor1", "Valor2"],
        ["Valor3", "Valor4"]
      ]
    },
    {
      "type": "comparison",
      "title": "Título da comparação",
      "items": [
        {
          "label": "Item A",
          "value": "100.000",
          "percentage": 60
        }
      ]
    },
    {
      "type": "alert",
      "level": "info|warning|error|success",
      "message": "Mensagem importante"
    }
  ],
  "sources": [
    "LOA 2023 - Capítulo X",
    "Portal da Transparência - Despesas 2023"
  ],
  "confidence": "high|medium|low",
  "suggestions": [
    "Pergunta relacionada 1?",
    "Pergunta relacionada 2?"
  ]
}

IMPORTANTE:
- SEMPRE retorne JSON válido
- Use componentes apropriados para cada tipo de informação
- Cite todas as fontes de dados
- Forneça sugestões de perguntas relacionadas
"""

    def _build_data_sources_info(
        self,
        loa_context: Optional[List[Dict[str, Any]]] = None,
        ldo_context: Optional[List[Dict[str, Any]]] = None,
        portal_packages: Optional[List[str]] = None,
        portal_data: Optional[List[Dict[str, Any]]] = None,
        portal_ingested_context: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Constrói informações sobre as fontes de dados disponíveis."""
        sections = ["FONTES DE DADOS DISPONÍVEIS:\n"]

        # LOA
        if loa_context and len(loa_context) > 0:
            sections.append("1. LEI ORÇAMENTÁRIA ANUAL (LOA):")
            sections.append(f"   - {len(loa_context)} trechos relevantes encontrados")
            for i, ctx in enumerate(loa_context[:3], 1):
                content = ctx.get("content", "")[:200]
                sections.append(f"   Trecho {i}: {content}...")
            if len(loa_context) > 3:
                sections.append(f"   ... e mais {len(loa_context) - 3} trechos")
            sections.append("")
        else:
            sections.append("1. LEI ORÇAMENTÁRIA ANUAL (LOA): Nenhum documento processado ainda\n")

        # LDO
        if ldo_context and len(ldo_context) > 0:
            sections.append("2. LEI DE DIRETRIZES ORÇAMENTÁRIAS (LDO):")
            sections.append(f"   - {len(ldo_context)} trechos relevantes encontrados")
            for i, ctx in enumerate(ldo_context[:3], 1):
                content = ctx.get("content", "")[:200]
                sections.append(f"   Trecho {i}: {content}...")
            if len(ldo_context) > 3:
                sections.append(f"   ... e mais {len(ldo_context) - 3} trechos")
            sections.append("")
        else:
            sections.append("2. LEI DE DIRETRIZES ORÇAMENTÁRIAS (LDO): Nenhum documento processado ainda\n")

        # Portal - Dados Ingeridos (novo)
        if portal_ingested_context and len(portal_ingested_context) > 0:
            sections.append("3. PORTAL DA TRANSPARÊNCIA (DADOS INGERIDOS E PROCESSADOS):")
            sections.append(f"   - {len(portal_ingested_context)} registros relevantes encontrados no banco de dados")
            for i, ctx in enumerate(portal_ingested_context[:5], 1):
                text = ctx.get("text", "")[:150]
                source = ctx.get("source", "").replace("portal_", "")
                sections.append(f"   Registro {i} ({source}): {text}...")
            if len(portal_ingested_context) > 5:
                sections.append(f"   ... e mais {len(portal_ingested_context) - 5} registros")
            sections.append("")
        
        # Portal - Datasets disponíveis
        if portal_packages and len(portal_packages) > 0:
            sections.append("4. PORTAL DA TRANSPARÊNCIA (DATASETS DISPONÍVEIS):")
            sections.append(f"   - {len(portal_packages)} datasets identificados como relevantes")
            sections.append(f"   Exemplos: {', '.join(portal_packages[:5])}")
            if len(portal_packages) > 5:
                sections.append(f"   ... e mais {len(portal_packages) - 5} datasets")
            sections.append("")

        if portal_data and len(portal_data) > 0:
            sections.append("   METADADOS DOS DATASETS:")
            for i, data in enumerate(portal_data[:2], 1):
                sections.append(f"   Dataset {i}: {data.get('title', 'Sem título')}")
                sections.append(f"   - Recursos: {len(data.get('resources', []))}")
            if len(portal_data) > 2:
                sections.append(f"   ... e mais {len(portal_data) - 2} datasets")
            sections.append("")

        return "\n".join(sections)

    def _build_examples(self) -> str:
        """Exemplos de perguntas e respostas esperadas."""
        return """EXEMPLOS DE RESPOSTAS:

Exemplo 1 - Pergunta: "Qual foi o orçamento total previsto para 2023?"

{
  "components": [
    {
      "type": "text",
      "content": "## Orçamento Total Previsto para 2023\\n\\nSegundo a LOA 2023, o orçamento total previsto foi de **R$ 10,5 bilhões**."
    },
    {
      "type": "metric",
      "label": "Orçamento Total 2023",
      "value": "R$ 10,5 bilhões"
    }
  ],
  "sources": ["LOA 2023 - Art. 1º"],
  "confidence": "high",
  "suggestions": [
    "Como esse orçamento está distribuído por área?",
    "Quanto foi efetivamente executado?"
  ]
}

Exemplo 2 - Pergunta: "Compare os gastos em saúde e educação"

{
  "components": [
    {
      "type": "text",
      "content": "## Comparação: Saúde vs Educação\\n\\nAnalisei os dados de 2023 e encontrei:"
    },
    {
      "type": "comparison",
      "title": "Orçamento Saúde vs Educação (2023)",
      "items": [
        {
          "label": "Saúde",
          "value": "R$ 1,8 bi",
          "percentage": 45
        },
        {
          "label": "Educação",
          "value": "R$ 2,2 bi",
          "percentage": 55
        }
      ]
    },
    {
      "type": "chart",
      "chart_type": "bar",
      "title": "Execução Orçamentária",
      "data": {
        "labels": ["Saúde", "Educação"],
        "datasets": [{
          "label": "Previsto (LOA)",
          "data": [1800000000, 2200000000]
        }, {
          "label": "Executado (Portal)",
          "data": [1650000000, 2100000000]
        }]
      }
    }
  ],
  "sources": ["LOA 2023", "Portal da Transparência - Despesas 2023"],
  "confidence": "high"
}
"""

    def build_analysis_prompt(
        self,
        question: str,
        municipality: str,
        state: str,
        year: int,
        loa_context: Optional[List[Dict[str, Any]]] = None,
        ldo_context: Optional[List[Dict[str, Any]]] = None,
        portal_packages: Optional[List[str]] = None,
        portal_data: Optional[List[Dict[str, Any]]] = None,
        portal_ingested_context: Optional[List[Dict[str, Any]]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Constrói o prompt completo para análise.

        Args:
            question: Pergunta do usuário
            chat_history: Histórico de mensagens anteriores
            municipality: Nome do município
            state: Estado (UF)
            year: Ano de referência
            loa_context: Contexto relevante da LOA
            ldo_context: Contexto relevante da LDO
            portal_packages: Lista de packages disponíveis
            portal_data: Dados do portal da transparência

        Returns:
            Prompt completo formatado
        """
        prompt_parts = [
            self.system_context,
            "\n" + "=" * 80 + "\n",
            f"MUNICÍPIO: {municipality} - {state}",
            f"ANO DE REFERÊNCIA: {year}",
            f"DATA DA CONSULTA: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC",
            "\n" + "=" * 80 + "\n",
        ]
        
        # Adicionar histórico do chat se existir
        if chat_history and len(chat_history) > 0:
            prompt_parts.extend([
                "HISTÓRICO DA CONVERSA:",
                "=" * 80,
            ])
            for msg in chat_history:
                role_label = "USUÁRIO" if msg["role"] == "user" else "ASSISTENTE"
                prompt_parts.append(f"\n{role_label}: {msg['content'][:200]}")
            prompt_parts.extend([
                "\n" + "=" * 80 + "\n",
            ])
        
        prompt_parts.extend([
            self._build_data_sources_info(
                loa_context, ldo_context, portal_packages, portal_data, portal_ingested_context
            ),
            "\n" + "=" * 80 + "\n",
            self._build_response_format_instructions(),
            "\n" + "=" * 80 + "\n",
            self._build_examples(),
            "\n" + "=" * 80 + "\n",
            f"PERGUNTA ATUAL DO USUÁRIO:\n{question}",
            "\n" + "=" * 80 + "\n",
            "INSTRUÇÕES FINAIS:",
            "1. Analise a pergunta cuidadosamente",
            "2. Use APENAS os dados fornecidos acima",
            "3. Se não houver dados suficientes, indique claramente",
            "4. Retorne JSON válido seguindo o formato especificado",
            "5. Seja claro, preciso e objetivo",
            "6. Sempre cite as fontes dos dados",
            "\nRESPOSTA (JSON):"
        ])

        return "\n".join(prompt_parts)

    def build_package_identification_prompt(
        self,
        question: str,
        available_packages: List[str],
        municipality: str,
    ) -> str:
        """
        Constrói prompt para identificar packages relevantes do portal.

        Args:
            question: Pergunta do usuário
            available_packages: Lista de packages disponíveis
            municipality: Nome do município

        Returns:
            Prompt para identificação de packages
        """
        packages_list = "\n".join([f"  - {pkg}" for pkg in available_packages[:50]])
        if len(available_packages) > 50:
            packages_list += f"\n  ... e mais {len(available_packages) - 50} packages"

        prompt = f"""Você é um assistente especializado em dados de transparência pública.

TAREFA: Identificar quais datasets do Portal da Transparência são relevantes para responder a pergunta do usuário.

MUNICÍPIO: {municipality}

PERGUNTA DO USUÁRIO:
{question}

DATASETS DISPONÍVEIS NO PORTAL:
{packages_list}

INSTRUÇÕES:
1. Analise a pergunta e identifique palavras-chave
2. Selecione os datasets mais relevantes (máximo 5)
3. Priorize datasets que contenham:
   - Dados de execução orçamentária
   - Despesas e receitas
   - Contratos e licitações
   - Dados do ano/período mencionado

Retorne APENAS um JSON no seguinte formato:

{{
  "relevant_packages": ["package1", "package2", ...],
  "keywords": ["palavra1", "palavra2", ...],
  "reasoning": "Breve explicação da escolha"
}}

RESPOSTA (JSON):"""

        return prompt

    def build_clarification_prompt(self, question: str, municipality: str) -> str:
        """
        Constrói prompt para pedir esclarecimentos quando a pergunta é ambígua.

        Args:
            question: Pergunta do usuário
            municipality: Nome do município

        Returns:
            Prompt para gerar perguntas de esclarecimento
        """
        prompt = f"""Você é um assistente de análise orçamentária.

MUNICÍPIO: {municipality}

PERGUNTA DO USUÁRIO:
{question}

A pergunta acima está AMBÍGUA ou FALTA INFORMAÇÃO.

TAREFA: Gere perguntas de esclarecimento para ajudar o usuário.

Retorne JSON no formato:

{{
  "components": [
    {{
      "type": "text",
      "content": "Preciso de mais informações para responder melhor. Você poderia esclarecer:"
    }},
    {{
      "type": "alert",
      "level": "info",
      "message": "Pergunta precisa de esclarecimento"
    }}
  ],
  "sources": [],
  "confidence": "low",
  "suggestions": [
    "Pergunta esclarecedora 1?",
    "Pergunta esclarecedora 2?",
    "Pergunta esclarecedora 3?"
  ]
}}

RESPOSTA (JSON):"""

        return prompt


# Função auxiliar para criar instância
def get_prompt_builder() -> PromptBuilder:
    """Retorna uma instância do PromptBuilder."""
    return PromptBuilder()

