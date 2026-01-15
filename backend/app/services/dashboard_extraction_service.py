"""
Serviço de Extração Estruturada para Dashboard LOA/LDO.

Este serviço utiliza o Gemini para extrair dados estruturados de PDFs
de LOA/LDO e armazená-los no PostgreSQL para exibição nos dashboards.
"""

import json
import re
import unicodedata
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal
import structlog
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.models.ldo_models import (
    MetasPrioridadesLDO,
    MetasFiscaisLDO,
    RiscosFiscaisLDO,
    PoliticasSetoriaisLDO,
    AvaliacaoAnteriorLDO
)

logger = structlog.get_logger()


class DashboardExtractionService:
    """Serviço para extração estruturada de dados de LOA/LDO."""
    
    def __init__(self):
        """Inicializa o serviço com configuração do Gemini."""
        # Configurar Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Usar Gemini 2.5 Pro - modelo mais poderoso para extração completa
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    def extract_from_pdf(self, pdf_path: str, db: Session, municipality_id: str = None) -> ExercicioOrcamentario:
        """
        Extrai dados estruturados de um PDF de LOA/LDO.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            db: Sessão do banco de dados
            municipality_id: ID do município (opcional)
            
        Returns:
            ExercicioOrcamentario: Objeto com todos os dados extraídos
        """
        logger.info("Iniciando extração estruturada", pdf_path=pdf_path)
        
        # 1. Extrair texto do PDF
        logger.info("Extraindo texto do PDF...")
        pdf_text = self._extract_pdf_text(pdf_path)
        
        # Limitar o texto para caber no contexto e evitar timeouts
        # Usar ~80k caracteres para capturar mais dados (especialmente regionais)
        # O prompt é mais longo mas é processamento anual - vale investir mais
        max_chars = 80000
        if len(pdf_text) > max_chars:
            logger.info(f"PDF muito grande ({len(pdf_text)} chars), usando amostragem estratégica...")
            pdf_text = self._sample_pdf_strategically(pdf_text, max_chars)
        
        # 2. Gerar prompt de extração
        prompt = self._build_extraction_prompt()
        
        # 3. Chamar o Gemini com o texto do PDF
        logger.info("Chamando Gemini para extração estruturada...")
        full_prompt = f"{prompt}\n\n---\n\nCONTEÚDO DO DOCUMENTO:\n\n{pdf_text}"
        
        # Chamar Gemini 2.5 Pro com timeout de 10 minutos
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Baixa temperatura para precisão
                max_output_tokens=65536  # Máximo para extração completa
            ),
            request_options={"timeout": 600}  # 10 minutos
        )
        
        # 4. Parsear o JSON retornado
        json_data = self._parse_json_response(response.text)
        
        if not json_data:
            logger.error("Falha ao extrair JSON da resposta do Gemini")
            raise ValueError("Não foi possível extrair dados estruturados do documento")
        
        # 5. Salvar no banco de dados
        exercicio = self._save_to_database(json_data, db, municipality_id)
        
        # 6. SEGUNDA ETAPA: Extração determinística de dados regionais
        # Esta etapa usa parser específico para garantir captura de regionais
        logger.info("Iniciando extração determinística de regionais...")
        regional_data = self._extract_regional_data_deterministic(pdf_path)
        
        if regional_data:
            self._save_regionais_deterministic(regional_data, exercicio, db)
            logger.info(f"Regionais extraídas: {len(regional_data)}")
        else:
            logger.warning("Nenhum dado regional encontrado pelo parser determinístico")
        
        logger.info(
            "Extração concluída com sucesso",
            ano=exercicio.ano,
            orcamento_total=str(exercicio.orcamento_total)
        )
        
        return exercicio
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extrai texto completo do PDF."""
        from pypdf import PdfReader
        
        reader = PdfReader(pdf_path)
        text_parts = []
        
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- PÁGINA {i+1} ---\n{page_text}")
            except Exception as e:
                logger.warning(f"Erro ao extrair página {i+1}: {e}")
                continue
        
        return "\n\n".join(text_parts)
    
    def _sample_pdf_strategically(self, full_text: str, max_chars: int) -> str:
        """
        Strategic PDF sampling optimized for LOA data extraction.
        Prioritizes: summary, revenues, expenses, regional investment, programs.
        """
        pages = full_text.split("--- PÁGINA ")
        
        if len(pages) <= 1:
            return full_text[:max_chars]
        
        # Extended keywords for comprehensive extraction
        priority_keywords = [
            # General budget
            'ORÇAMENTO', 'FISCAL', 'SEGURIDADE', 'TOTAL GERAL',
            # Revenues
            'RECEITA', 'TRIBUTÁRIA', 'TRANSFERÊNCIA', 'CORRENTE', 'CAPITAL',
            'RESUMO GERAL DA RECEITA',
            # Expenses  
            'DESPESA', 'NATUREZA', 'PESSOAL', 'ENCARGOS', 'INVESTIMENTO',
            'CATEGORIA ECONÔMICA', 'RESUMO GERAL DA DESPESA',
            # Programs
            'PROGRAMA', 'AÇÃO', 'FUNÇÃO', 'SUBFUNÇÃO',
            # Regional/Territorial
            'REGIONAL', 'REGIONALIZAÇÃO', 'TERRITÓRIO', 'REGIÃO',
            'BAIRRO', 'APLICAÇÕES POR ÓRGÃO',
            # Agencies/Entities
            'ÓRGÃO', 'SECRETARIA', 'FUNDO', 'AUTARQUIA',
            # Constitutional limits
            'EDUCAÇÃO', 'SAÚDE', 'LIMITE', 'CONSTITUCIONAL',
            'ART. 212', 'ART. 29',
            # Social participation
            'PARTICIPAÇÃO', 'SOCIAL', 'AUDIÊNCIA', 'FÓRUM',
            # Summary tables
            'DEMONSTRATIVO', 'CONSOLIDADO', 'ANEXO'
        ]
        
        # Score each page based on keyword relevance
        scored_pages = []
        for i, page in enumerate(pages[1:], start=1):  # Skip empty first split
            page_upper = page.upper()
            score = 0
            for kw in priority_keywords:
                if kw in page_upper:
                    score += 1
                    # Extra weight for key tables
                    if kw in ['REGIONALIZAÇÃO', 'RESUMO GERAL', 'DEMONSTRATIVO', 'CONSOLIDADO']:
                        score += 3
                    elif kw in ['REGIONAL', 'TERRITÓRIO', 'BAIRRO']:
                        score += 2
            scored_pages.append((i, page, score))
        
        # Sort by score (highest first)
        scored_pages.sort(key=lambda x: x[2], reverse=True)
        
        sampled_pages = []
        chars_used = 0
        pages_included = set()
        
        # Always include first 15 pages (law text, summary, totals)
        for i, page in enumerate(pages[1:16], start=1):
            if chars_used + len(page) < max_chars * 0.25:  # 25% for intro
                sampled_pages.append((i, page))
                pages_included.add(i)
                chars_used += len(page)
        
        # Add high-scoring pages (prioritize variety)
        for page_num, page, score in scored_pages:
            if page_num not in pages_included:
                if chars_used + len(page) < max_chars * 0.85:  # Leave 15% buffer
                    sampled_pages.append((page_num, page))
                    pages_included.add(page_num)
                    chars_used += len(page)
        
        # Sort by page number for logical flow
        sampled_pages.sort(key=lambda x: x[0])
        
        # Rebuild text with page markers
        result_parts = []
        for page_num, page in sampled_pages:
            result_parts.append(f"--- PÁGINA {page_num} ---\n{page}")
        
        result = "\n\n".join(result_parts)
        
        # Final trim if needed
        if len(result) > max_chars:
            result = result[:max_chars]
        
        logger.info(
            f"Strategic sampling: {len(pages)-1} pages -> {len(sampled_pages)} selected "
            f"({len(result)} chars, {len(pages_included)} unique pages)"
        )
        
        return result
    
    def _build_extraction_prompt(self) -> str:
        """
        RIGID extraction prompt with EXACT type specifications.
        Designed for plug & play - works for any Brazilian municipality.
        """
        return '''# LOA BUDGET DATA EXTRACTION - STRICT JSON SCHEMA

You are extracting budget data from a Brazilian Annual Budget Law (LOA).
You MUST return a JSON object that EXACTLY matches the schema below.

## MANDATORY TYPE RULES (VIOLATIONS WILL CAUSE SYSTEM FAILURE)

| Field Type | Correct Example | WRONG Examples |
|------------|-----------------|----------------|
| number | 14776973233.00 | "R$ 14.776.973.233,00", null, "" |
| string | "Fortaleza" | null (use "N/A"), 123 |
| array | ["item1", "item2"] | "item1, item2", null (use []) |
| integer | 2025 | "2025", 2025.0 |

## CRITICAL RULES

1. ALL monetary values MUST be numbers (not strings): 14776973233.00
2. ALL valor_total fields MUST have a number (use 0 if not found, NEVER null)
3. ALL arrays MUST be arrays (use [] if empty, NEVER null or string)
4. The temas_chave field MUST be a string (comma-separated), NOT an array
5. Extract the BUDGET YEAR from the document title (e.g., "LOA 2026" → ano_exercicio: 2026)
6. Look for "REGIONALIZAÇÃO DAS APLICAÇÕES POR ÓRGÃO" table for regional values

## EXACT JSON SCHEMA (copy structure exactly)

```json
{
  "metadados": {
    "tipo_documento": "LOA",
    "ano_exercicio": 2025,
    "municipio": "Fortaleza",
    "estado": "CE",
    "prefeito": "Nome do Prefeito",
    "documento_legal": "Lei nº 11.515"
  },
  "visao_geral": {
    "orcamento_total": 14776973233.00,
    "orcamento_fiscal": 8967255755.00,
    "orcamento_seguridade": 5809717478.00,
    "limite_suplementacao_percentual": 30.0,
    "receita_corrente_liquida": 0.0,
    "variacao_ano_anterior_percentual": 3.5
  },
  "receitas": {
    "correntes": {
      "total": 14000000000.00,
      "categorias": [
        {"nome": "Impostos, Taxas e Contribuições de Melhoria", "valor": 3900000000.00},
        {"nome": "Receita de Contribuições", "valor": 800000000.00},
        {"nome": "Receita Patrimonial", "valor": 500000000.00},
        {"nome": "Receita de Serviços", "valor": 100000000.00},
        {"nome": "Transferências Correntes", "valor": 9000000000.00},
        {"nome": "Outras Receitas Correntes", "valor": 600000000.00}
      ]
    },
    "capital": {
      "total": 700000000.00,
      "categorias": [
        {"nome": "Operações de Crédito", "valor": 500000000.00},
        {"nome": "Alienação de Bens", "valor": 50000000.00},
        {"nome": "Amortização de Empréstimos", "valor": 10000000.00},
        {"nome": "Transferências de Capital", "valor": 140000000.00}
      ]
    }
  },
  "despesas": {
    "por_categoria_economica": [
      {"nome": "Pessoal e Encargos Sociais", "valor_total": 6891721745.00, "valor_fiscal": 3768579921.00, "valor_seguridade": 3123141824.00},
      {"nome": "Juros e Encargos da Dívida", "valor_total": 447500000.00, "valor_fiscal": 447500000.00, "valor_seguridade": 0.00},
      {"nome": "Outras Despesas Correntes", "valor_total": 5615766544.00, "valor_fiscal": 3046366078.00, "valor_seguridade": 2569400466.00},
      {"nome": "Investimentos", "valor_total": 1294347456.00, "valor_fiscal": 1177172268.00, "valor_seguridade": 117175188.00},
      {"nome": "Inversões Financeiras", "valor_total": 7537156.00, "valor_fiscal": 7537156.00, "valor_seguridade": 0.00},
      {"nome": "Amortização da Dívida", "valor_total": 510501000.00, "valor_fiscal": 510501000.00, "valor_seguridade": 0.00},
      {"nome": "Reserva de Contingência", "valor_total": 9599332.00, "valor_fiscal": 9599332.00, "valor_seguridade": 0.00}
    ],
    "por_orgao": [
      {"codigo": "25000", "nome": "Secretaria Municipal da Saúde", "valor_total": 3659147374.00, "valor_fiscal": 923810.00, "valor_seguridade": 3658223564.00},
      {"codigo": "24000", "nome": "Secretaria Municipal da Educação", "valor_total": 3379459437.00, "valor_fiscal": 3379459437.00, "valor_seguridade": 0.00},
      {"codigo": "11205", "nome": "FUNDAÇÃO DE CIÊNCIA, TECNOLOGIA E INOVAÇÃO DE FORTALEZA", "valor_total": 1731140.00, "valor_fiscal": 1731140.00, "valor_seguridade": 0.00}
    ],
    "por_programa": [
      {"codigo": "0001", "nome": "GESTÃO E MANUTENÇÃO", "valor_total": 4000000000.00, "valor_fiscal": 2500000000.00, "valor_seguridade": 1500000000.00},
      {"codigo": "0042", "nome": "DESENVOLVIMENTO DO ENSINO FUNDAMENTAL", "valor_total": 2300000000.00, "valor_fiscal": 2300000000.00, "valor_seguridade": 0.00},
      {"codigo": "0012", "nome": "ENCARGOS GERAIS DO MUNICÍPIO", "valor_total": 1290000000.00, "valor_fiscal": 100000000.00, "valor_seguridade": 1190000000.00},
      {"codigo": "0123", "nome": "ATENÇÃO ESPECIALIZADA À SAÚDE", "valor_total": 1270000000.00, "valor_fiscal": 0.00, "valor_seguridade": 1270000000.00},
      {"codigo": "0119", "nome": "ATENÇÃO PRIMÁRIA À SAÚDE", "valor_total": 838000000.00, "valor_fiscal": 0.00, "valor_seguridade": 838000000.00},
      {"codigo": "0052", "nome": "DESENVOLVIMENTO DA EDUCAÇÃO INFANTIL", "valor_total": 591000000.00, "valor_fiscal": 591000000.00, "valor_seguridade": 0.00},
      {"codigo": "0014", "nome": "FORTALEZA LIMPA", "valor_total": 559000000.00, "valor_fiscal": 559000000.00, "valor_seguridade": 0.00},
      {"codigo": "0101", "nome": "INFRAESTRUTURA URBANA E VIÁRIA", "valor_total": 528000000.00, "valor_fiscal": 528000000.00, "valor_seguridade": 0.00},
      {"codigo": "0153", "nome": "GESTÃO LOGÍSTICA E DE SERVIÇOS", "valor_total": 363000000.00, "valor_fiscal": 50000000.00, "valor_seguridade": 313000000.00},
      {"codigo": "0002", "nome": "ATUAÇÃO LEGISLATIVA", "valor_total": 330000000.00, "valor_fiscal": 330000000.00, "valor_seguridade": 0.00}
    ]
  },
  "investimento_regional": [
    {
      "regional_numero": 1,
      "regional_nome": "Nome da Divisão Territorial Encontrada",
      "valor_total": 438700000.00,
      "bairros": ["Bairro A", "Bairro B", "Bairro C", "Bairro D", "Bairro E"],
      "valores_por_area": {
        "infraestrutura": 180000000.00,
        "saude": 120000000.00,
        "educacao": 98700000.00,
        "social": 40000000.00,
        "urbanismo": 0.00,
        "cultura": 0.00
      },
      "destaques": [
        {
          "categoria": "saude",
          "nome": "Nome do Projeto/Equipamento de Saúde",
          "descricao": "Descrição breve do projeto extraída do documento",
          "prioridade": "alta"
        },
        {
          "categoria": "educacao",
          "nome": "Nome do Projeto/Equipamento Educacional",
          "descricao": "Descrição breve do projeto extraída do documento",
          "prioridade": "alta"
        },
        {
          "categoria": "infraestrutura",
          "nome": "Nome do Projeto de Infraestrutura",
          "descricao": "Descrição breve do projeto extraída do documento",
          "prioridade": "media"
        }
      ]
    },
    {
      "regional_numero": 2,
      "regional_nome": "Nome da Segunda Divisão Territorial",
      "valor_total": 554578086.00,
      "bairros": ["Bairro X", "Bairro Y", "Bairro Z"],
      "valores_por_area": {
        "infraestrutura": 221831234.00,
        "educacao": 138644522.00,
        "saude": 110915617.00,
        "social": 83186713.00,
        "urbanismo": 0.00,
        "cultura": 0.00
      },
      "destaques": [
        {
          "categoria": "saude",
          "nome": "Nome do Equipamento de Saúde Encontrado",
          "descricao": "Descrição conforme documento",
          "prioridade": "alta"
        },
        {
          "categoria": "infraestrutura",
          "nome": "Nome do Projeto de Infraestrutura Encontrado",
          "descricao": "Descrição conforme documento",
          "prioridade": "media"
        }
      ]
    }
  ],
  "participacao_social": {
    "foruns_realizados": 0,
    "temas_chave": "Saúde, Educação, Infraestrutura, Mobilidade",
    "total_priorizado": 0.00,
    "descricao_processo": "Audiências públicas realizadas nas regionais",
    "iniciativas": []
  },
  "limites_constitucionais": {
    "educacao_previsto_percentual": 28.0,
    "educacao_valor": 3379459437.00,
    "saude_previsto_percentual": 18.0,
    "saude_valor": 3659147374.00,
    "pessoal_previsto_percentual": 48.0,
    "pessoal_valor": 6891721745.00,
    "receita_impostos": 0.00,
    "receita_corrente_liquida": 0.00
  },
  "observacoes": "Any additional notes about the extraction"
}
```

## WHERE TO FIND EACH DATA TYPE

| Data | Look for these tables/sections |
|------|-------------------------------|
| visao_geral | "RESUMO DO ORÇAMENTO", "TOTAL GERAL", first pages |
| receitas | "RESUMO GERAL DA RECEITA", "RECEITA POR CATEGORIA" |
| despesas.por_categoria | "DESPESA POR NATUREZA", "DESPESA POR CATEGORIA ECONÔMICA" |
| despesas.por_orgao | "DESPESA POR ÓRGÃO", "DESPESA POR PODER E ÓRGÃO" |
| despesas.por_programa | "DESPESA POR PROGRAMA", "DEMONSTRATIVO DE PROGRAMAS" |
| investimento_regional | Look for territorial divisions like "REGIONALIZAÇÃO", "POR REGIÃO", "POR DISTRITO", "POR ZONA", "DIVISÃO TERRITORIAL", "APLICAÇÕES GEOGRÁFICAS" - Municipality may use different terminology |
| limites_constitucionais | "DEMONSTRATIVO ART. 212", "AÇÕES E SERVIÇOS DE SAÚDE" |

## IMPORTANT: TERRITORIAL INVESTMENT EXTRACTION RULES

**The municipality may organize territorial divisions differently:**
- Some use "Regional 1", "Regional 2", etc. (common in Fortaleza)
- Others use "Distrito 1", "Distrito 2", "Zona Norte", "Zona Sul", etc.
- Extract ALL divisions found, regardless of naming convention
- For each division, extract:
  - Number/identifier and name (as written in document)
  - ALL neighborhoods/territories listed (bairros: array of strings)
  - Total investment value for that area
  - Breakdown by sector if available (valores_por_area: infrastructure, health, education, social, urbanism, culture)
  - Main projects/highlights per category (destaques: array with categoria, nome, descricao, prioridade)
- Look for tables titled: "Aplicações por Região/Distrito", "Investimento Territorial", "Dotação por Área Geográfica"
- If document has 10+ territorial divisions, extract ALL of them
- If some divisions have no detailed data, still include them with available information

## FINAL CHECKLIST BEFORE OUTPUT

1. ✓ ano_exercicio is an INTEGER (2025, 2026) extracted from document title
2. ✓ ALL valor_total fields are NUMBERS (never null, use 0 if not found)
3. ✓ temas_chave is a STRING with comma separation (NOT an array)
4. ✓ bairros is an ARRAY of strings (use [] if none found)
5. ✓ destaques is an ARRAY of objects with categoria, nome, descricao, prioridade (use [] if none found)
6. ✓ valores_por_area is an OBJECT with infraestrutura, saude, educacao, social, urbanismo, cultura (use 0 for each if not found)
7. ✓ iniciativas is an ARRAY (use [] if none found)
8. ✓ All monetary values are unformatted numbers: 14776973233.00
9. ✓ Extract ALL programs found (10, 20, 50+ if available)
10. ✓ Extract ALL territorial divisions found (may be 5, 10, 15+ entries - use whatever naming the municipality uses: "Regional X", "Distrito X", "Zona X", etc.)
11. ✓ **Extract ALL agencies/órgãos (not just top 10) - include ALL units, even small ones**
12. ✓ **For EACH territorial division, extract ALL neighborhoods/territories, investment values by sector (infraestrutura/saude/educacao/social/urbanismo/cultura), and main projects/highlights**

Return ONLY the JSON object, no markdown, no explanation:
'''

    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extrai e valida o JSON da resposta do Gemini."""
        try:
            # Tentar encontrar o JSON na resposta
            # Primeiro, tentar parsear diretamente
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # Tentar encontrar JSON entre ```json e ```
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    # Tentar corrigir erros comuns
                    json_text = self._fix_json_errors(json_text)
                    return json.loads(json_text)
            
            # Tentar encontrar JSON entre { e }
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    # Tentar corrigir erros comuns
                    json_text = self._fix_json_errors(json_text)
                    return json.loads(json_text)
            
            logger.error("Não foi possível encontrar JSON válido na resposta")
            logger.debug(f"Resposta do Gemini (primeiros 500 chars): {response_text[:500]}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.debug(f"Resposta do Gemini (primeiros 500 chars): {response_text[:500]}")
            return None
    
    def _fix_json_errors(self, json_text: str) -> str:
        """Tenta corrigir erros comuns de JSON."""
        # Remover trailing commas
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)
        
        # Remover comentários
        json_text = re.sub(r'//.*?\n', '\n', json_text)
        
        # Substituir aspas simples por duplas
        # (cuidado: só fora de strings)
        
        return json_text
    
    def _save_to_database(
        self, 
        data: Dict[str, Any], 
        db: Session, 
        municipality_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Salva os dados extraídos no banco de dados.
        
        Se já existir um exercício com mesmo ano, município e tipo,
        SUBSTITUI os dados (delete cascade remove todos os relacionamentos).
        """
        
        metadados = data.get("metadados", {})
        visao_geral = data.get("visao_geral", {})
        
        ano = metadados.get("ano_exercicio")
        municipio = metadados.get("municipio", "Fortaleza")
        tipo_doc = metadados.get("tipo_documento", "LOA")
        
        # BUSCAR EXERCÍCIO EXISTENTE
        exercicio = db.query(ExercicioOrcamentario).filter(
            ExercicioOrcamentario.ano == ano,
            ExercicioOrcamentario.municipio == municipio,
            ExercicioOrcamentario.tipo_documento == tipo_doc
        ).first()
        
        if exercicio:
            # REPROCESSAMENTO: Deletar exercício existente (cascade remove filhos)
            logger.info(f"♻️  Reprocessamento detectado: {tipo_doc} {ano} - {municipio}")
            logger.info(f"   Deletando dados antigos (ID: {exercicio.id})...")
            db.delete(exercicio)
            db.flush()  # Garantir que delete cascade executou
            logger.info("   ✅ Dados antigos removidos")
        
        # Criar exercício (novo ou substituindo)
        exercicio = ExercicioOrcamentario(
            ano=ano,
            municipio=municipio,
            estado=metadados.get("estado", "CE"),
            tipo_documento=tipo_doc,
            prefeito=metadados.get("prefeito"),
            documento_legal=metadados.get("documento_legal"),
            documento_referencia=metadados.get("documento_referencia"),
            orcamento_total=self._to_decimal(visao_geral.get("orcamento_total")),
            orcamento_fiscal=self._to_decimal(visao_geral.get("orcamento_fiscal")),
            orcamento_seguridade=self._to_decimal(visao_geral.get("orcamento_seguridade")),
            limite_suplementacao=self._to_decimal(visao_geral.get("limite_suplementacao_percentual")),
            receita_corrente_liquida=self._to_decimal(visao_geral.get("receita_corrente_liquida")),
            variacao_ano_anterior=self._to_decimal(visao_geral.get("variacao_ano_anterior_percentual")),
            municipality_id=municipality_id,
            observacoes=json.dumps(data.get("observacoes")) if data.get("observacoes") else None,
            status="completed",
            processado_em=datetime.utcnow()
        )
        db.add(exercicio)
        db.flush()  # Para obter o ID
        
        logger.info(f"✅ Exercício {'reprocessado' if exercicio else 'criado'}: {tipo_doc} {ano}")
        
        # =========================================================================
        # SALVAMENTO INCREMENTAL COM PROTEÇÃO CONTRA PERDA TOTAL
        # =========================================================================
        # Cada seção é salva separadamente com try/except.
        # Se UMA seção falhar, as OUTRAS ainda são salvas.
        # Isso evita perder 1h+ de processamento por um erro pontual.
        # =========================================================================
        
        sections_status = {}
        
        # 1. Salvar receitas
        try:
            logger.info("💾 Salvando receitas...")
            self._save_receitas(data.get("receitas", {}), exercicio, db)
            db.flush()  # Commit parcial
            sections_status["receitas"] = "✅ OK"
            logger.info("   ✅ Receitas salvas")
        except Exception as e:
            sections_status["receitas"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar receitas (continuando...): {e}", exc_info=True)
        
        # 2. Salvar despesas por categoria
        try:
            logger.info("💾 Salvando categorias de despesa...")
            self._save_despesas_categoria(data.get("despesas", {}).get("por_categoria_economica", []), exercicio, db)
            db.flush()
            sections_status["categorias"] = "✅ OK"
            logger.info("   ✅ Categorias salvas")
        except Exception as e:
            sections_status["categorias"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar categorias (continuando...): {e}", exc_info=True)
        
        # 3. Salvar programas
        try:
            logger.info("💾 Salvando programas...")
            self._save_programas(data.get("despesas", {}).get("por_programa", []), exercicio, db)
            db.flush()
            sections_status["programas"] = "✅ OK"
            logger.info("   ✅ Programas salvos")
        except Exception as e:
            sections_status["programas"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar programas (continuando...): {e}", exc_info=True)
        
        # 4. Salvar órgãos
        try:
            logger.info("💾 Salvando órgãos...")
            self._save_orgaos(data.get("despesas", {}).get("por_orgao", []), exercicio, db)
            db.flush()
            sections_status["orgaos"] = "✅ OK"
            logger.info("   ✅ Órgãos salvos")
        except Exception as e:
            sections_status["orgaos"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar órgãos (continuando...): {e}", exc_info=True)
        
        # 5. Salvar investimento regional
        try:
            logger.info("💾 Salvando investimentos regionais...")
            regionais_data = data.get("investimento_regional", [])
            logger.info(f"   Tipo de regionais_data: {type(regionais_data)}")
            logger.info(f"   Número de regionais: {len(regionais_data) if isinstance(regionais_data, list) else 'N/A'}")
            self._save_regionais(regionais_data, exercicio, db)
            db.flush()
            sections_status["regionais"] = "✅ OK"
            logger.info("   ✅ Regionais salvas")
        except Exception as e:
            sections_status["regionais"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar regionais (continuando...): {e}", exc_info=True)
        
        # 6. Salvar participação social
        try:
            logger.info("💾 Salvando participação social...")
            self._save_participacao_social(data.get("participacao_social"), exercicio, db)
            db.flush()
            sections_status["participacao"] = "✅ OK"
            logger.info("   ✅ Participação social salva")
        except Exception as e:
            sections_status["participacao"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar participação social (continuando...): {e}", exc_info=True)
        
        # 7. Salvar limites constitucionais
        try:
            logger.info("💾 Salvando limites constitucionais...")
            self._save_limites(data.get("limites_constitucionais"), exercicio, db)
            db.flush()
            sections_status["limites"] = "✅ OK"
            logger.info("   ✅ Limites salvos")
        except Exception as e:
            sections_status["limites"] = f"❌ ERRO: {str(e)}"
            logger.error(f"❌ Erro ao salvar limites (continuando...): {e}", exc_info=True)
        
        # Relatório final
        logger.info("\n" + "=" * 70)
        logger.info("📊 RELATÓRIO DE SALVAMENTO")
        logger.info("=" * 70)
        for section, status in sections_status.items():
            logger.info(f"  {section.ljust(20)}: {status}")
        logger.info("=" * 70)
        
        # Se TODAS as seções falharam, lançar exceção
        if all("❌" in status for status in sections_status.values()):
            raise Exception("❌ TODAS as seções falharam ao salvar. Verifique os logs acima.")
        
        db.commit()
        db.refresh(exercicio)
        
        return exercicio
    
    def _to_decimal(self, value) -> Optional[Decimal]:
        """Converte valor para Decimal de forma segura."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None
    
    def _save_receitas(self, receitas_data: Dict, exercicio: ExercicioOrcamentario, db: Session):
        """Salva as receitas no banco."""
        # Receitas correntes
        correntes = receitas_data.get("correntes", {})
        for idx, cat in enumerate(correntes.get("categorias", [])):
            categoria = cat.get("nome") or cat.get("categoria")
            if not categoria:
                logger.warning("Receita corrente sem categoria, pulando item", item=cat)
                continue
            valor_previsto = self._to_decimal(cat.get("valor")) or Decimal(0)
            receita = ReceitaOrcamentaria(
                exercicio_id=exercicio.id,
                tipo="corrente",
                categoria=categoria,
                codigo_receita=cat.get("codigo"),
                valor_previsto=valor_previsto,
                descricao_popular=cat.get("descricao_popular"),
                ordem=idx
            )
            db.add(receita)
        
        # Receitas de capital
        capital = receitas_data.get("capital", {})
        for idx, cat in enumerate(capital.get("categorias", [])):
            categoria = cat.get("nome") or cat.get("categoria")
            if not categoria:
                logger.warning("Receita de capital sem categoria, pulando item", item=cat)
                continue
            valor_previsto = self._to_decimal(cat.get("valor")) or Decimal(0)
            receita = ReceitaOrcamentaria(
                exercicio_id=exercicio.id,
                tipo="capital",
                categoria=categoria,
                codigo_receita=cat.get("codigo"),
                valor_previsto=valor_previsto,
                descricao_popular=cat.get("descricao_popular"),
                ordem=idx
            )
            db.add(receita)
    
    def _save_despesas_categoria(self, categorias: List, exercicio: ExercicioOrcamentario, db: Session):
        """Salva despesas por categoria econômica."""
        for idx, cat in enumerate(categorias):
            categoria = cat.get("nome") or cat.get("categoria")
            if not categoria:
                logger.warning("Despesa por categoria sem nome, pulando item", item=cat)
                continue
            valor_fiscal = self._to_decimal(cat.get("valor_fiscal")) or Decimal(0)
            valor_seguridade = self._to_decimal(cat.get("valor_seguridade")) or Decimal(0)
            valor_total = self._to_decimal(cat.get("valor_total"))
            if valor_total is None:
                valor_total = valor_fiscal + valor_seguridade
            despesa = DespesaCategoria(
                exercicio_id=exercicio.id,
                categoria=categoria,
                codigo_natureza=cat.get("codigo"),
                valor_fiscal=valor_fiscal,
                valor_seguridade=valor_seguridade,
                valor_total=valor_total,
                ordem=idx
            )
            db.add(despesa)
    
    def _save_programas(self, programas: List, exercicio: ExercicioOrcamentario, db: Session):
        """Salva programas de governo."""
        for idx, prog in enumerate(programas):
            valor_fiscal = self._to_decimal(prog.get("valor_fiscal")) or Decimal(0)
            valor_seguridade = self._to_decimal(prog.get("valor_seguridade")) or Decimal(0)
            valor_total = self._to_decimal(prog.get("valor_total")) or (valor_fiscal + valor_seguridade)
            
            # Calcular percentuais
            perc_fiscal = None
            perc_seguridade = None
            if valor_total and valor_total > 0:
                perc_fiscal = (valor_fiscal / valor_total * 100) if valor_fiscal else Decimal(0)
                perc_seguridade = (valor_seguridade / valor_total * 100) if valor_seguridade else Decimal(0)
            
            # Gerar código padrão se não fornecido
            codigo = prog.get("codigo")
            if not codigo:
                codigo = f"PROG{idx+1:04d}"
            
            # Validar nome
            nome = prog.get("nome")
            if not nome:
                continue  # Skip programas sem nome
            
            programa = ProgramaGoverno(
                exercicio_id=exercicio.id,
                codigo_programa=codigo,
                nome=nome,
                objetivo=prog.get("objetivo"),
                valor_fiscal=valor_fiscal,
                valor_seguridade=valor_seguridade,
                valor_total=valor_total,
                percentual_fiscal=perc_fiscal,
                percentual_seguridade=perc_seguridade,
                orgao_responsavel=prog.get("orgao_responsavel"),
                ordem=idx
            )
            db.add(programa)
    
    def _save_orgaos(self, orgaos: List, exercicio: ExercicioOrcamentario, db: Session):
        """Salva órgãos e fundos."""
        for idx, org in enumerate(orgaos):
            nome = org.get("nome")
            if not nome:
                logger.warning("Órgão sem nome, pulando item", item=org)
                continue
            valor_fiscal = self._to_decimal(org.get("valor_fiscal")) or Decimal(0)
            valor_seguridade = self._to_decimal(org.get("valor_seguridade")) or Decimal(0)
            valor_total = self._to_decimal(org.get("valor_total"))
            if valor_total is None:
                valor_total = valor_fiscal + valor_seguridade
            orgao = OrgaoFundo(
                exercicio_id=exercicio.id,
                codigo_orgao=org.get("codigo"),
                nome=nome,
                tipo=org.get("tipo"),
                sigla=org.get("sigla"),
                valor_total=valor_total,
                valor_fiscal=valor_fiscal,
                valor_seguridade=valor_seguridade,
                ordem=idx
            )
            db.add(orgao)
    
    def _save_regionais(self, regionais: List, exercicio: ExercicioOrcamentario, db: Session):
        """Salva investimento por regional."""
        if not regionais:
            logger.info("   ⚠️  Nenhuma regional para salvar (lista vazia)")
            return
        
        # Validação de tipo de entrada
        if not isinstance(regionais, list):
            logger.error(f"❌ regionais não é uma lista, é {type(regionais)}. Convertendo...")
            # Tentar converter para lista
            if isinstance(regionais, dict):
                regionais = [regionais]
            else:
                logger.error(f"❌ Não foi possível converter regionais para lista. Abortando.")
                return
        
        logger.info(f"   Processando {len(regionais)} regionais...")
        saved_count = 0
        skipped_count = 0
            
        for idx, regional in enumerate(regionais):
            # Validar que regional é um dicionário
            if not isinstance(regional, dict):
                logger.warning(f"   ⚠️  Regional {idx} não é um dicionário (tipo: {type(regional)}), pulando...")
                skipped_count += 1
                continue
            
            # Obter número e nome da regional
            regional_num = regional.get("regional_numero")
            regional_nome = regional.get("regional_nome")
            
            # Se não tiver número, usar índice
            if regional_num is None:
                regional_num = idx + 1
            
            # Se não tiver nome, gerar baseado no número
            if not regional_nome:
                regional_nome = f"Regional {regional_num}"
            
            # Valor pode ser null - será preenchido pelo parser determinístico
            valor = self._to_decimal(regional.get("valor_total"))
            if valor is None:
                valor = Decimal(0)
            
            inv = InvestimentoRegional(
                exercicio_id=exercicio.id,
                regional_numero=regional_num,
                regional_nome=regional_nome,
                valor_total=valor
            )
            
            # Salvar bairros (como JSON)
            bairros = regional.get("bairros")
            if bairros:
                import json
                inv.bairros_json = json.dumps(bairros)
            
            # Salvar destaques (como JSON)
            destaques = regional.get("destaques")
            if destaques:
                import json
                inv.destaques_json = json.dumps(destaques)
            
            # Salvar valores por área (como JSON)
            valores_por_area = regional.get("valores_por_area")
            if valores_por_area:
                import json
                inv.valores_por_area_json = json.dumps(valores_por_area)
            
            db.add(inv)
            saved_count += 1
        
        # Log de resumo
        logger.info(f"   ✅ Regionais processadas: {saved_count} salvas, {skipped_count} puladas")
    
    def _save_participacao_social(self, data: Optional[Dict], exercicio: ExercicioOrcamentario, db: Session):
        """Salva dados de participação social."""
        if not data:
            return
        
        # O prompt instrui Gemini a retornar temas_chave como string
        # Mas por segurança, converter se vier como lista
        temas_chave = data.get("temas_chave", "")
        if isinstance(temas_chave, list):
            temas_chave = ", ".join(str(t) for t in temas_chave)
        
        participacao = ParticipacaoSocial(
            exercicio_id=exercicio.id,
            foruns_realizados=data.get("foruns_realizados", 0) or 0,
            temas_chave=temas_chave,
            total_priorizado=self._to_decimal(data.get("total_priorizado")) or Decimal(0),
            descricao_processo=data.get("descricao_processo", "")
        )
        # Usar setter para campo JSON
        iniciativas = data.get("iniciativas", [])
        if isinstance(iniciativas, list):
            participacao.iniciativas = iniciativas
        db.add(participacao)
    
    def _save_limites(self, data: Optional[Dict], exercicio: ExercicioOrcamentario, db: Session):
        """Salva limites constitucionais."""
        if not data:
            return
        
        edu_perc = self._to_decimal(data.get("educacao_previsto_percentual"))
        saude_perc = self._to_decimal(data.get("saude_previsto_percentual"))
        pessoal_perc = self._to_decimal(data.get("pessoal_previsto_percentual"))
        
        limites = LimiteConstitucional(
            exercicio_id=exercicio.id,
            educacao_previsto_percentual=edu_perc,
            educacao_valor=self._to_decimal(data.get("educacao_valor")),
            educacao_cumprindo=edu_perc >= 25 if edu_perc else None,
            saude_previsto_percentual=saude_perc,
            saude_valor=self._to_decimal(data.get("saude_valor")),
            saude_cumprindo=saude_perc >= 15 if saude_perc else None,
            pessoal_previsto_percentual=pessoal_perc,
            pessoal_valor=self._to_decimal(data.get("pessoal_valor")),
            pessoal_dentro_limite=pessoal_perc <= 54 if pessoal_perc else None,
            receita_impostos=self._to_decimal(data.get("receita_impostos")),
            receita_corrente_liquida=self._to_decimal(data.get("receita_corrente_liquida"))
        )
        db.add(limites)
    
    def get_exercicio_by_ano(self, ano: int, db: Session, municipio: str = "Fortaleza") -> Optional[ExercicioOrcamentario]:
        """Busca um exercício por ano."""
        return db.query(ExercicioOrcamentario).filter(
            ExercicioOrcamentario.ano == ano,
            ExercicioOrcamentario.municipio == municipio
        ).first()
    
    def list_exercicios(self, db: Session, municipio: str = "Fortaleza") -> List[ExercicioOrcamentario]:
        """Lista todos os exercícios disponíveis."""
        return db.query(ExercicioOrcamentario).filter(
            ExercicioOrcamentario.municipio == municipio
        ).order_by(ExercicioOrcamentario.ano.desc()).all()
    
    # =========================================================================
    # SEGUNDA ETAPA: Extração Determinística de Dados Regionais
    # =========================================================================
    
    def _extract_regional_data_deterministic(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extrai dados de regionalização de forma determinística usando parser específico.
        
        Esta função busca a tabela "REGIONALIZAÇÃO DAS APLICAÇÕES POR ÓRGÃO" no PDF
        e extrai os totais por regional de forma confiável.
        
        Returns:
            Lista de dicionários com dados de cada regional
        """
        from pypdf import PdfReader

        def _normalize(text: str) -> str:
            """Remove acentuação e coloca em caixa alta para comparações robustas."""
            return unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode().upper()

        try:
            reader = PdfReader(pdf_path)

            # Coletar todas as páginas que contenham a tabela de regionalização
            target_pages = []
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    norm = _normalize(text)
                    if "REGIONALIZACAO DAS APLICACOES" in norm:
                        target_pages.append((page_num + 1, text))
                except Exception as e:
                    logger.warning(f"Erro ao ler página {page_num}: {e}")
                    continue

            # Fallback: procurar páginas com a palavra REGIONALIZAÇÃO mesmo sem header completo
            if not target_pages:
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text() or ""
                        norm = _normalize(text)
                        if "REGIONALIZA" in norm and "APLICAC" in norm:
                            target_pages.append((page_num + 1, text))
                    except Exception as e:
                        logger.warning(f"Erro ao ler página {page_num}: {e}")
                        continue

            if not target_pages:
                logger.warning("Tabela de regionalização não encontrada no PDF")
                return []

            combined_text = "\n\n".join(text for _, text in target_pages)
            pages_str = ", ".join(str(p) for p, _ in target_pages)
            logger.info(f"Tabela de regionalização encontrada nas páginas {pages_str}")

            regionais = self._parse_regional_table(combined_text)

            # Enriquecer com bairros e destaques encontrados no PDF (quando existirem)
            try:
                detalhes = self._extract_regional_details_from_pdf(pdf_path)
                if detalhes:
                    for regional in regionais:
                        reg_num = regional.get("regional_numero")
                        if reg_num in detalhes:
                            regional.update(detalhes[reg_num])
            except Exception as e:
                logger.warning(f"Falha ao enriquecer regionais com detalhes: {e}")

            return regionais

        except Exception as e:
            logger.error(f"Erro na extração determinística de regionais: {e}")
            return []
    
    def _parse_regional_table(self, table_text: str) -> List[Dict[str, Any]]:
        """
        Parseia a tabela de regionalização extraída do PDF.
        
        O formato típico da linha TOTAL é:
        TOTAL [TOTAL_GERAL] [MUNICIPIO] [REG1] [REG2] [REG3] [REG5] [REG4] [REG6] [REG7]
        
        Nota: A ordem das colunas pode variar (ex: REG5 antes de REG4), 
        então precisamos identificar pela header.
        """
        import re

        if not table_text:
            return []

        def _normalize(text: str) -> str:
            return unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode().upper()

        def _roman_to_int(roman: str) -> int:
            values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
            total = 0
            prev = 0
            for char in roman.upper():
                val = values.get(char, 0)
                total += val
                if val > prev:
                    total -= 2 * prev
                prev = val
            return total

        # Limpar e normalizar linhas
        lines = [ln.strip() for ln in table_text.split("\n") if ln.strip()]
        if not lines:
            logger.warning("Tabela de regionalização vazia após normalização")
            return []

        num_pattern = r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?"

        def _parse_header_regionals(header: str) -> List[int]:
            order: List[int] = []
            matches_digits = re.findall(r"REGIONAL\s*(\d+)", _normalize(header))
            matches_romans = re.findall(r"REGIONAL\s*([IVXLCDM]+)", _normalize(header))
            for token in matches_digits:
                try:
                    order.append(int(token))
                except ValueError:
                    continue
            for token in matches_romans:
                order.append(_roman_to_int(token))
            return [r for r in order if r > 0]

        def _numbers_from_line(line: str) -> List[Decimal]:
            values: List[Decimal] = []
            for num in re.findall(num_pattern, line):
                try:
                    normalized = num.replace(".", "").replace(",", ".")
                    values.append(Decimal(normalized))
                except Exception:
                    continue
            return values

        regionais_map: Dict[int, Decimal] = {}
        current_header = None
        current_order: List[int] = []

        for line in lines:
            norm_line = _normalize(line)

            if "REGIONAL" in norm_line:
                current_header = line
                current_order = _parse_header_regionals(line)
                continue

            if not current_order:
                continue

            if norm_line.startswith("TOTAL") and "TOTAL GERAL" not in norm_line:
                values = _numbers_from_line(line)
                if not values:
                    continue

                # Heurísticas para alinhar valores com regionais
                has_municipio = current_header and ("MUNIC" in _normalize(current_header))
                expected = len(current_order)

                if has_municipio and len(values) >= expected + 2:
                    regional_values = values[2:2 + expected]
                elif len(values) >= expected + 1:
                    regional_values = values[:expected]
                else:
                    regional_values = values[:expected]

                for reg_num, valor in zip(current_order, regional_values):
                    regionais_map[reg_num] = valor

        if not regionais_map:
            logger.warning("Não foi possível mapear valores de regionais a partir das tabelas")
            return []

        regionais: List[Dict[str, Any]] = [
            {
                "regional_numero": reg_num,
                "regional_nome": f"Regional {reg_num}",
                "valor_total": valor,
                "bairros": [],
                "destaques": {},
            }
            for reg_num, valor in regionais_map.items()
        ]

        regionais.sort(key=lambda x: x["regional_numero"])
        logger.info(f"Regionais mapeadas do parser: {len(regionais)}")
        return regionais

    def _extract_regional_details_from_pdf(self, pdf_path: str) -> Dict[int, Dict[str, Any]]:
        """
        Extrai bairros e destaques a partir de linhas do PDF que mencionam Regionais.
        Usa somente informações presentes no documento (sem dados fictícios).
        """
        from pypdf import PdfReader
        import re

        def _normalize(text: str) -> str:
            return unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode().upper()

        def _to_value(num_str: str) -> Optional[Decimal]:
            try:
                return Decimal(num_str.replace(".", "").replace(",", "."))
            except Exception:
                return None

        def _extract_bairros(line: str) -> List[str]:
            bairros = []
            # Captura "BAIRRO X" ou "BAIRROS X"
            for match in re.finditer(r"BAIRR(?:O|OS)\s+([A-Z0-9\s\-]+)", line.upper()):
                raw = match.group(1)
                raw = re.split(r"\s+-\s+|\s+EP/LOM|\s+EP\s|\s+REGIONAL\s|\s+REGIAO\s", raw)[0].strip()
                if raw and len(raw) > 2:
                    cleaned = re.sub(r"\bEp\b", "", raw, flags=re.IGNORECASE).strip()
                    # Remover tokens muito curtos e duplicados óbvios
                    if len(cleaned) < 4 and cleaned.title() not in {"Pici", "Coco"}:
                        continue
                    bairros.append(cleaned.title())
            return bairros

        def _categorize(text: str) -> str:
            t = _normalize(text)
            if any(k in t for k in ["SAUDE", "HOSPITAL", "UPA", "UBS", "ATENCAO BASICA"]):
                return "saude"
            if any(k in t for k in ["ESCOLA", "EDUC", "CRECHE", "ENSINO"]):
                return "educacao"
            if any(k in t for k in ["URBANIZA", "PAVIMENT", "DRENAGEM", "ASFALTO", "PRACA", "VIARIA", "CICLO", "REQUALIFICA", "REFORMA", "OBRA", "SANEAMENTO"]):
                return "infraestrutura"
            return "social"

        num_pattern = r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?"
        regionais: Dict[int, Dict[str, Any]] = {}

        reader = PdfReader(pdf_path)
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text:
                continue

            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for idx, line in enumerate(lines):
                upper = _normalize(line)
                if "REGIONALIZACAO DAS APLICACOES" in upper:
                    continue
                if "TOTAL ORGAO" in upper or upper.startswith("TOTAL GERAL") or upper.startswith("TOTAL "):
                    continue
                if "SECRETARIA REGIONAL" in upper or "IPTU SECRETARIA REGIONAL" in upper:
                    continue

                m = re.search(r"REGIONAL\s*(\d+)", upper)
                if not m:
                    continue

                reg_num = int(m.group(1))
                values = [_to_value(v) for v in re.findall(num_pattern, line)]
                values = [v for v in values if v is not None]
                if not values:
                    continue

                # Usar o último valor monetário da linha como referência
                valor = values[-1]

                def _has_letters(text: str) -> bool:
                    return bool(re.search(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]", text.upper()))

                # Descrição pode estar na linha anterior (tabela quebrada)
                description = re.split(r"REGIONAL\s*\d+", line, flags=re.IGNORECASE)[0].strip(" -")
                if (not description or not _has_letters(description)) and idx > 0:
                    description = lines[idx - 1].strip()

                description = re.split(r"EP/LOM.*", description, flags=re.IGNORECASE)[0]
                description = re.sub(r"^\\d+\\s*-?\\s*", "", description).strip(" -")
                if not description or len(description) < 6 or not _has_letters(description):
                    continue

                desc_upper = _normalize(description)
                if any(term in desc_upper for term in [
                    "PRODUTO ORCAMENTARIO", "UNIDADE", "META FISICA", "META FINANCEIRA", "REGIONAL", "MUNICIPIO"
                ]):
                    continue

                bairros = _extract_bairros(line)
                if idx > 0:
                    bairros.extend(_extract_bairros(lines[idx - 1]))
                categoria = _categorize(description)

                entry = regionais.setdefault(reg_num, {"bairros": set(), "destaques": {}})
                for b in bairros:
                    entry["bairros"].add(b)

                # Guardar apenas o maior destaque por categoria
                current = entry["destaques"].get(categoria)
                if not current or (current.get("valor", 0) < (valor or 0)):
                    entry["destaques"][categoria] = {
                        "nome": description,
                        "descricao": description,
                        "prioridade": "media",
                        "valor": float(valor)
                    }

        # Fallback com filtros mais permissivos caso nada tenha sido encontrado
        if not regionais:
            for page in reader.pages:
                text = page.extract_text() or ""
                if not text:
                    continue
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                for idx, line in enumerate(lines):
                    upper = _normalize(line)
                    if "REGIONALIZACAO DAS APLICACOES" in upper:
                        continue
                    m = re.search(r"REGIONAL\s*(\d+)", upper)
                    if not m:
                        continue
                    reg_num = int(m.group(1))
                    values = [_to_value(v) for v in re.findall(num_pattern, line)]
                    values = [v for v in values if v is not None]
                    if not values:
                        continue
                    valor = values[-1]
                    description = line
                    if idx > 0 and not _has_letters(description):
                        description = lines[idx - 1].strip()
                    description = re.split(r"EP/LOM.*", description, flags=re.IGNORECASE)[0]
                    description = re.sub(r"^\\d+\\s*-?\\s*", "", description).strip(" -")
                    if not description or not _has_letters(description):
                        continue
                    desc_upper = _normalize(description)
                    if "REGIONAL" in desc_upper or "MUNICIPIO" in desc_upper:
                        continue
                    categoria = _categorize(description)
                    entry = regionais.setdefault(reg_num, {"bairros": set(), "destaques": {}})
                    for b in _extract_bairros(line):
                        entry["bairros"].add(b)
                    if idx > 0:
                        for b in _extract_bairros(lines[idx - 1]):
                            entry["bairros"].add(b)
                    current = entry["destaques"].get(categoria)
                    if not current or (current.get("valor", 0) < (valor or 0)):
                        entry["destaques"][categoria] = {
                            "nome": description,
                            "descricao": description,
                            "prioridade": "media",
                            "valor": float(valor)
                        }

        # Finalizar estrutura
        normalized: Dict[int, Dict[str, Any]] = {}
        for reg_num, data in regionais.items():
            bairros = sorted(data["bairros"])
            normalized[reg_num] = {
                "bairros": bairros,
                "destaques": data["destaques"]
            }

        logger.info(f"Detalhes regionais extraídos: {len(normalized)} regionais")
        return normalized
    
    def _detect_regional_order(self, header_line: str) -> List[int]:
        """
        Detecta a ordem das regionais no cabeçalho da tabela.
        
        Exemplo de header: "MUNICíPIO REGIONAL 1 REGIONAL 2 REGIONAL 3 REGIONAL 5 REGIONAL 4 REGIONAL 6 REGIONAL 7"
        """
        import re
        
        if not header_line:
            return []
        
        # Buscar padrão "REGIONAL X" no header
        matches = re.findall(r'REGIONAL\s*(\d+)', header_line, re.IGNORECASE)
        
        if matches:
            order = [int(m) for m in matches]
            logger.info(f"Ordem das regionais detectada: {order}")
            return order
        
        return []
    
    def _to_roman(self, num: int) -> str:
        """Converte número para algarismo romano."""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syms[i]
                num -= val[i]
            i += 1
        return roman_num
    
    def _save_regionais_deterministic(
        self, 
        regional_data: List[Dict[str, Any]], 
        exercicio: ExercicioOrcamentario, 
        db: Session
    ):
        """
        Salva os dados regionais extraídos de forma determinística.
        
        Esta função substitui quaisquer dados regionais existentes para o exercício,
        garantindo que os dados do parser determinístico prevaleçam.
        """
        import json

        if not regional_data:
            logger.warning("Parser determinístico não retornou regionais; mantendo dados existentes.")
            return

        # Verificar se já existem regionais para este exercício
        existing_count = db.query(InvestimentoRegional).filter(
            InvestimentoRegional.exercicio_id == exercicio.id
        ).count()

        if existing_count > 0:
            db.query(InvestimentoRegional).filter(
                InvestimentoRegional.exercicio_id == exercicio.id
            ).delete()
            logger.info(f"Substituindo {existing_count} regionais por {len(regional_data)} do parser")
        else:
            logger.info(f"Inserindo {len(regional_data)} regionais do parser determinístico")
        
        # Inserir novos dados
        for regional in regional_data:
            inv = InvestimentoRegional(
                exercicio_id=exercicio.id,
                regional_numero=regional.get("regional_numero"),
                regional_nome=regional.get("regional_nome"),
                valor_total=self._to_decimal(regional.get("valor_total"))
            )
            
            # Salvar bairros e destaques como JSON
            bairros = regional.get("bairros")
            if bairros:
                inv.bairros_json = json.dumps(bairros)
            
            destaques = regional.get("destaques")
            if destaques:
                inv.destaques_json = json.dumps(destaques)
            
            valores_por_area = regional.get("valores_por_area")
            if valores_por_area:
                inv.valores_por_area_json = json.dumps(valores_por_area)
            
            db.add(inv)
        
        db.flush()  # Garantir que os dados são persistidos
        logger.info(f"Regionais salvas: {len(regional_data)}")

    # ===============================================
    # MÉTODOS DE EXTRAÇÃO DE LDO
    # ===============================================
    
    def extract_ldo_from_pdf(
        self, 
        pdf_path: str, 
        db: Session, 
        municipality_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Extrai dados estruturados de um PDF de LDO.
        
        Args:
            pdf_path: Caminho para o arquivo PDF da LDO
            db: Sessão do banco de dados
            municipality_id: ID do município (opcional)
            
        Returns:
            ExercicioOrcamentario: Objeto com todos os dados extraídos
        """
        from app.services.ldo_extraction_prompts import build_ldo_extraction_prompt
        
        logger.info("=" * 70)
        logger.info("INICIANDO EXTRAÇÃO DE LDO")
        logger.info("=" * 70)
        logger.info(f"Arquivo: {pdf_path}")
        
        # 1. Extrair texto do PDF
        logger.info("[1/6] Extraindo texto do PDF...")
        pdf_text = self._extract_pdf_text(pdf_path)
        
        # Limitar texto para evitar timeouts (LDO geralmente é menor que LOA)
        max_chars = 60000  # LDO é menor, então usamos menos caracteres
        if len(pdf_text) > max_chars:
            logger.info(f"PDF grande ({len(pdf_text)} chars), usando amostragem estratégica...")
            pdf_text = self._sample_ldo_strategically(pdf_text, max_chars)
        
        # 2. Gerar prompt de extração LDO
        logger.info("[2/6] Gerando prompt de extração LDO...")
        prompt = build_ldo_extraction_prompt()
        
        # 3. Chamar Gemini 2.5 Pro
        logger.info("[3/6] Chamando Gemini 2.5 Pro para extração...")
        full_prompt = f"{prompt}\n\n---\n\nCONTEÚDO DA LDO:\n\n{pdf_text}"
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,  # Baixa temperatura para precisão
                max_output_tokens=32768  # LDO tem menos dados que LOA
            ),
            request_options={"timeout": 600}  # 10 minutos
        )
        
        # 4. Parsear JSON
        logger.info("[4/6] Parseando resposta JSON...")
        ldo_data = self._parse_json_response(response.text)
        
        if not ldo_data:
            logger.error("Falha ao extrair JSON da resposta do Gemini")
            raise ValueError("Não foi possível extrair dados estruturados da LDO")
        
        logger.info("✅ JSON extraído com sucesso!")
        
        # 5. Salvar no banco de dados
        logger.info("[5/6] Salvando dados da LDO no banco...")
        exercicio = self._save_ldo_to_database(ldo_data, db, municipality_id)
        
        logger.info("[6/6] Extração de LDO concluída!")
        logger.info("=" * 70)
        logger.info(f"✅ LDO {exercicio.ano} processada com sucesso!")
        logger.info("=" * 70)
        
        return exercicio
    
    def _sample_ldo_strategically(self, full_text: str, max_chars: int) -> str:
        """
        Amostragem estratégica de LDO priorizando anexos obrigatórios.
        """
        pages = full_text.split("--- PÁGINA ")
        
        if len(pages) <= 1:
            return full_text[:max_chars]
        
        # Palavras-chave prioritárias para LDO
        priority_keywords = [
            # Anexos obrigatórios (LRF)
            'METAS FISCAIS', 'ANEXO DE METAS', 'RESULTADO PRIMÁRIO',
            'RESULTADO NOMINAL', 'DÍVIDA CONSOLIDADA', 'RCL',
            'RISCOS FISCAIS', 'ANEXO DE RISCOS', 'PASSIVOS CONTINGENTES',
            # Prioridades
            'PRIORIDADES', 'DIRETRIZES', 'METAS', 'OBJETIVOS',
            'PROGRAMAS PRIORITÁRIOS', 'AÇÕES PRIORITÁRIAS',
            # Setores
            'SAÚDE', 'EDUCAÇÃO', 'ASSISTÊNCIA SOCIAL', 'SEGURANÇA',
            'INFRAESTRUTURA', 'MOBILIDADE',
            # Projeções
            'PROJEÇÕES', 'PLURIANUAL', 'TRIENAL',
            # Avaliação
            'CUMPRIMENTO', 'AVALIAÇÃO', 'ANO ANTERIOR',
            # Tabelas
            'DEMONSTRATIVO', 'TABELA', 'QUADRO'
        ]
        
        # Pontuar páginas
        scored_pages = []
        for i, page in enumerate(pages[1:], start=1):
            page_upper = page.upper()
            score = 0
            for kw in priority_keywords:
                if kw in page_upper:
                    score += 1
                    # Peso extra para anexos obrigatórios
                    if kw in ['METAS FISCAIS', 'RISCOS FISCAIS', 'ANEXO DE METAS', 'ANEXO DE RISCOS']:
                        score += 5
                    elif kw in ['PRIORIDADES', 'DIRETRIZES']:
                        score += 3
            scored_pages.append((i, page, score))
        
        # Ordenar por score
        scored_pages.sort(key=lambda x: x[2], reverse=True)
        
        sampled_pages = []
        chars_used = 0
        pages_included = set()
        
        # Sempre incluir primeiras 10 páginas (introdução, cabeçalho)
        for i, page in enumerate(pages[1:11], start=1):
            if chars_used + len(page) < max_chars * 0.2:  # 20% para início
                sampled_pages.append((i, page))
                pages_included.add(i)
                chars_used += len(page)
        
        # Adicionar páginas com alto score
        for page_num, page, score in scored_pages:
            if page_num not in pages_included:
                if chars_used + len(page) < max_chars * 0.9:
                    sampled_pages.append((page_num, page))
                    pages_included.add(page_num)
                    chars_used += len(page)
        
        # Ordenar por número de página
        sampled_pages.sort(key=lambda x: x[0])
        
        # Reconstruir texto
        result_parts = []
        for page_num, page in sampled_pages:
            result_parts.append(f"--- PÁGINA {page_num} ---\n{page}")
        
        result = "\n\n".join(result_parts)
        
        if len(result) > max_chars:
            result = result[:max_chars]
        
        logger.info(
            f"Amostragem LDO: {len(pages)-1} páginas → {len(sampled_pages)} selecionadas "
            f"({len(result)} chars)"
        )
        
        return result
    
    def _safe_get(self, data: dict, *keys, default=None):
        """
        Acessa valores aninhados de forma segura, tratando None.
        Exemplo: _safe_get(data, "metas_fiscais", "resultado_primario", "meta")
        """
        result = data
        for key in keys:
            if result is None or not isinstance(result, dict):
                return default
            result = result.get(key, default)
        return result
    
    def _save_ldo_to_database(
        self, 
        ldo_data: dict, 
        db: Session, 
        municipality_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Salva dados extraídos da LDO no banco de dados.
        """
        from datetime import datetime
        
        # Validar dados recebidos
        if not ldo_data:
            logger.error("ldo_data é None ou vazio!")
            raise ValueError("Dados da LDO estão vazios")
        
        if not isinstance(ldo_data, dict):
            logger.error(f"ldo_data não é dict! Tipo: {type(ldo_data)}")
            raise ValueError(f"ldo_data deve ser dict, recebido: {type(ldo_data)}")
        
        # Log dos dados recebidos
        logger.info(f"Chaves recebidas no ldo_data: {list(ldo_data.keys())}")
        
        metadados = ldo_data.get("metadados", {})
        
        if not metadados:
            logger.warning("metadados está vazio! Usando valores padrão")
            # Tentar inferir ano do nome do arquivo ou usar ano atual
            metadados = {
                "ano_exercicio": 2025,  # TODO: inferir do filename
                "municipio": "Fortaleza",
                "estado": "CE"
            }
        
        logger.info(f"Metadados da LDO: ano={metadados.get('ano_exercicio')}, municipio={metadados.get('municipio')}")
        
        # 1. Criar ou buscar ExercicioOrcamentario
        exercicio = db.query(ExercicioOrcamentario).filter(
            ExercicioOrcamentario.ano == metadados.get("ano_exercicio"),
            ExercicioOrcamentario.municipio == metadados.get("municipio", "Fortaleza"),
            ExercicioOrcamentario.tipo_documento == "LDO"
        ).first()
        
        if not exercicio:
            exercicio = ExercicioOrcamentario(
                ano=metadados.get("ano_exercicio"),
                municipio=metadados.get("municipio", "Fortaleza"),
                estado=metadados.get("estado", "CE"),
                tipo_documento="LDO",
                prefeito=metadados.get("prefeito"),
                documento_legal=metadados.get("documento_legal"),
                municipality_id=municipality_id,
                processado_em=datetime.utcnow(),
                status="completed"
            )
            db.add(exercicio)
            db.flush()
        
        # 2. Salvar Metas e Prioridades
        metas_prioridades_data = ldo_data.get("metas_prioridades") or {}
        if metas_prioridades_data:
            metas_prioridades = MetasPrioridadesLDO(
                exercicio_id=exercicio.id,
                prioridades=metas_prioridades_data.get("prioridades") or [],
                diretrizes_gerais=metas_prioridades_data.get("diretrizes_gerais") or [],
                metas_setoriais=metas_prioridades_data.get("metas_setoriais") or {},
                programas_prioritarios=metas_prioridades_data.get("programas_prioritarios") or [],
                diretrizes_setoriais=metas_prioridades_data.get("diretrizes_setoriais") or {}
            )
            db.add(metas_prioridades)
        
        # 3. Salvar Metas Fiscais
        metas_fiscais_data = ldo_data.get("metas_fiscais") or {}
        if metas_fiscais_data:
            metas_fiscais = MetasFiscaisLDO(
                exercicio_id=exercicio.id,
                resultado_primario_meta=self._to_decimal(self._safe_get(metas_fiscais_data, "resultado_primario", "meta")),
                resultado_primario_ano_anterior=self._to_decimal(self._safe_get(metas_fiscais_data, "resultado_primario", "ano_anterior")),
                resultado_primario_dois_anos_antes=self._to_decimal(self._safe_get(metas_fiscais_data, "resultado_primario", "dois_anos_antes")),
                resultado_nominal_meta=self._to_decimal(self._safe_get(metas_fiscais_data, "resultado_nominal", "meta")),
                resultado_nominal_ano_anterior=self._to_decimal(self._safe_get(metas_fiscais_data, "resultado_nominal", "ano_anterior")),
                divida_consolidada_meta=self._to_decimal(self._safe_get(metas_fiscais_data, "divida_consolidada", "meta")),
                divida_consolidada_percentual_rcl=self._to_decimal(self._safe_get(metas_fiscais_data, "divida_consolidada", "percentual_rcl")),
                divida_consolidada_ano_anterior=self._to_decimal(self._safe_get(metas_fiscais_data, "divida_consolidada", "ano_anterior")),
                rcl_prevista=self._to_decimal(metas_fiscais_data.get("rcl_prevista")),
                rcl_ano_anterior=self._to_decimal(metas_fiscais_data.get("rcl_ano_anterior")),
                receita_total_prevista=self._to_decimal(metas_fiscais_data.get("receita_total_prevista")),
                despesa_total_prevista=self._to_decimal(metas_fiscais_data.get("despesa_total_prevista")),
                projecoes_trienio=metas_fiscais_data.get("projecoes_trienio") or {},
                premissas_macroeconomicas=metas_fiscais_data.get("premissas_macroeconomicas") or {},
                margem_expansao_despesas_obrigatorias=self._to_decimal(metas_fiscais_data.get("margem_expansao_despesas_obrigatorias")),
                renuncias_receita_total=self._to_decimal(self._safe_get(metas_fiscais_data, "renuncias_receita", "total")),
                renuncias_receita_detalhes=self._safe_get(metas_fiscais_data, "renuncias_receita", "detalhes", default=[]),
                metodologia_calculo=metas_fiscais_data.get("metodologia_calculo"),
                observacoes=metas_fiscais_data.get("observacoes")
            )
            db.add(metas_fiscais)
        
        # 4. Salvar Riscos Fiscais
        riscos_fiscais_data = ldo_data.get("riscos_fiscais") or {}
        if riscos_fiscais_data:
            riscos_fiscais = RiscosFiscaisLDO(
                exercicio_id=exercicio.id,
                riscos=riscos_fiscais_data.get("riscos") or [],
                passivos_contingentes_total=self._to_decimal(self._safe_get(riscos_fiscais_data, "passivos_contingentes", "total")),
                passivos_contingentes_detalhes=self._safe_get(riscos_fiscais_data, "passivos_contingentes", "detalhes", default=[]),
                demandas_judiciais_total=self._to_decimal(self._safe_get(riscos_fiscais_data, "demandas_judiciais", "total")),
                demandas_judiciais_detalhes=self._safe_get(riscos_fiscais_data, "demandas_judiciais", "detalhes", default=[]),
                garantias_concedidas_total=self._to_decimal(self._safe_get(riscos_fiscais_data, "garantias_concedidas", "total")),
                garantias_concedidas_detalhes=self._safe_get(riscos_fiscais_data, "garantias_concedidas", "detalhes", default=[]),
                operacoes_credito_riscos=riscos_fiscais_data.get("operacoes_credito_riscos") or [],
                riscos_macroeconomicos=riscos_fiscais_data.get("riscos_macroeconomicos") or {},
                riscos_especificos_municipio=riscos_fiscais_data.get("riscos_especificos_municipio") or [],
                avaliacao_geral_risco=riscos_fiscais_data.get("avaliacao_geral_risco"),
                total_exposicao_risco=self._to_decimal(riscos_fiscais_data.get("total_exposicao_risco")),
                percentual_exposicao_orcamento=self._to_decimal(riscos_fiscais_data.get("percentual_exposicao_orcamento"))
            )
            db.add(riscos_fiscais)
        
        # 5. Salvar Políticas Setoriais
        politicas_setoriais_data = ldo_data.get("politicas_setoriais") or {}
        if politicas_setoriais_data:
            politicas_setoriais = PoliticasSetoriaisLDO(
                exercicio_id=exercicio.id,
                politicas=politicas_setoriais_data
            )
            db.add(politicas_setoriais)
        
        # 6. Salvar Avaliação Ano Anterior
        avaliacao_anterior_data = ldo_data.get("avaliacao_ano_anterior") or {}
        if avaliacao_anterior_data:
            avaliacao_anterior = AvaliacaoAnteriorLDO(
                exercicio_id=exercicio.id,
                ano_avaliado=avaliacao_anterior_data.get("ano_avaliado"),
                metas_fiscais_cumpridas=avaliacao_anterior_data.get("metas_fiscais_cumpridas") or {},
                metas_setoriais_cumpridas=avaliacao_anterior_data.get("metas_setoriais_cumpridas") or {},
                avaliacao_geral=avaliacao_anterior_data.get("avaliacao_geral"),
                percentual_geral_cumprimento=self._to_decimal(avaliacao_anterior_data.get("percentual_geral_cumprimento")),
                justificativas_nao_cumprimento=avaliacao_anterior_data.get("justificativas_nao_cumprimento") or []
            )
            db.add(avaliacao_anterior)
        
        # Commit final
        db.commit()
        db.refresh(exercicio)
        
        logger.info(f"✅ LDO salva: {exercicio.tipo_documento} {exercicio.ano} - {exercicio.municipio}")
        
        return exercicio

