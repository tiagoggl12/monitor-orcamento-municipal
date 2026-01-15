"""
Serviço de Extração Adaptativa e Inteligente para Documentos Orçamentários.

Este serviço usa uma abordagem multi-fase com o Gemini:
1. DESCOBERTA: Analisa o documento para identificar estrutura, seções, tabelas
2. EXTRAÇÃO: Processa cada seção identificada de forma específica
3. CONSOLIDAÇÃO: Agrupa e valida todos os dados extraídos

Vantagens:
- 100% adaptativo - não precisa saber a estrutura antecipadamente
- Processa documentos completos (1000+ páginas) em batches
- Sem hardcoding de schemas ou palavras-chave
- Funciona com qualquer município, ano ou formato
"""

import json
import re
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime
import structlog
import google.generativeai as genai
from sqlalchemy.orm import Session
from pypdf import PdfReader

from app.core.config import settings

logger = structlog.get_logger()


class AdaptiveExtractionService:
    """
    Serviço de extração adaptativa que descobre a estrutura do documento
    antes de extrair os dados, sem schemas fixos ou hardcoding.
    """
    
    def __init__(self):
        """Inicializa com Gemini 2.5 Pro."""
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
    # =========================================================================
    # FASE 1: DESCOBERTA DA ESTRUTURA
    # =========================================================================
    
    def discover_document_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        FASE 1: Analisa o documento para identificar sua estrutura, seções e tabelas.
        
        Returns:
            {
                "tipo_documento": "LOA" | "LDO" | "PPA" | "Outro",
                "metadados": {...},
                "secoes_identificadas": [
                    {
                        "nome": "Receitas Orçamentárias",
                        "tipo": "tabela_estruturada",
                        "paginas": [10, 11, 12],
                        "colunas_identificadas": ["Categoria", "Valor"],
                        "importancia": 10
                    },
                    ...
                ],
                "total_paginas": 1155,
                "sugestao_processamento": "batch_de_100_paginas"
            }
        """
        logger.info("=" * 70)
        logger.info("FASE 1: DESCOBERTA DA ESTRUTURA DO DOCUMENTO")
        logger.info("=" * 70)
        
        # Extrair metadados do PDF
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        logger.info(f"Total de páginas: {total_pages}")
        
        # Amostrar páginas estratégicas para análise inicial
        sample_pages = self._strategic_sample_for_discovery(reader, max_pages=50)
        
        # Construir prompt de descoberta (SEM SCHEMA FIXO!)
        prompt = self._build_discovery_prompt()
        
        # Preparar texto das páginas amostradas
        sample_text = "\n\n".join([
            f"--- PÁGINA {num} ---\n{text}"
            for num, text in sample_pages
        ])
        
        full_prompt = f"{prompt}\n\n---\n\nAMOSTRA DO DOCUMENTO ({len(sample_pages)} páginas de {total_pages}):\n\n{sample_text}"
        
        logger.info("Chamando Gemini para análise de estrutura...")
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=16384
            )
        )
        
        # Parsear resposta JSON
        structure = self._parse_json_response(response.text)
        
        if not structure:
            raise ValueError("Falha ao descobrir estrutura do documento")
        
        structure["total_paginas"] = total_pages
        
        logger.info(f"✅ Estrutura descoberta: {structure.get('tipo_documento')}")
        logger.info(f"   Seções identificadas: {len(structure.get('secoes_identificadas', []))}")
        
        return structure
    
    def _strategic_sample_for_discovery(self, reader: PdfReader, max_pages: int = 50) -> List[Tuple[int, str]]:
        """
        Amostra estratégica de páginas para descoberta de estrutura.
        Inclui: início, meio, fim, e páginas com alta densidade de informação.
        """
        total_pages = len(reader.pages)
        sampled_pages = []
        
        # 1. Primeiras 15 páginas (introdução, sumário, metadados)
        for i in range(min(15, total_pages)):
            try:
                text = reader.pages[i].extract_text() or ""
                if len(text) > 100:  # Ignorar páginas vazias
                    sampled_pages.append((i + 1, text))
            except:
                continue
        
        # 2. Páginas do meio (distribuídas uniformemente)
        step = max(1, total_pages // (max_pages - 20))
        for i in range(15, total_pages - 5, step):
            if len(sampled_pages) >= max_pages - 5:
                break
            try:
                text = reader.pages[i].extract_text() or ""
                if len(text) > 200:  # Preferir páginas com conteúdo
                    sampled_pages.append((i + 1, text))
            except:
                continue
        
        # 3. Últimas 5 páginas (anexos, totalizações)
        for i in range(max(0, total_pages - 5), total_pages):
            try:
                text = reader.pages[i].extract_text() or ""
                if len(text) > 100:
                    sampled_pages.append((i + 1, text))
            except:
                continue
        
        logger.info(f"Amostra para descoberta: {len(sampled_pages)} páginas de {total_pages}")
        return sampled_pages[:max_pages]
    
    def _build_discovery_prompt(self) -> str:
        """
        Prompt de descoberta - SEM SCHEMAS FIXOS!
        O Gemini deve descobrir organicamente o que existe no documento.
        """
        return '''# DESCOBERTA INTELIGENTE DE ESTRUTURA DE DOCUMENTO ORÇAMENTÁRIO

Você é um especialista em análise de documentos orçamentários brasileiros (LOA, LDO, PPA).

## SUA MISSÃO

Analise a amostra do documento fornecida e **DESCUBRA ORGANICAMENTE** a estrutura, sem assumir nada.

**NÃO FORCE SCHEMAS FIXOS!** Cada documento é único. Identifique o que REALMENTE existe.

## O QUE VOCÊ DEVE DESCOBRIR

### 1. METADADOS BÁSICOS
- Tipo de documento (LOA, LDO, PPA, Relatório, outro)
- Ano do exercício
- Município/Estado
- Lei/Decreto (número e data)
- Órgão emissor

### 2. SEÇÕES/CAPÍTULOS IDENTIFICADOS
Para CADA seção importante encontrada, retorne:
```json
{
  "nome": "Nome da seção como aparece no documento",
  "tipo": "tabela_estruturada" | "texto_narrativo" | "grafico" | "mapa" | "lista",
  "descricao": "Breve descrição do conteúdo",
  "paginas_inicio": 10,
  "paginas_fim": 25,
  "colunas_ou_campos": ["campo1", "campo2"],  // Se for tabela
  "palavras_chave": ["termo1", "termo2"],  // Termos específicos desta seção
  "importancia": 1-10,  // Relevância (1=baixa, 10=crítica)
  "volume_estimado": "pequeno" | "medio" | "grande"  // Qtd de dados
}
```

### 3. ENTIDADES IDENTIFICADAS
Liste TODAS as entidades/unidades mencionadas (órgãos, secretarias, fundos, programas):
```json
{
  "tipo": "orgao" | "programa" | "fundo" | "regional",
  "nomes_encontrados": ["Nome 1", "Nome 2", ...],
  "formato_codigo": "99999" | "XXXX-YY" | null,  // Padrão de código se identificado
  "quantidade_estimada": 50
}
```

### 4. ANÁLISE ESTRUTURAL
```json
{
  "formato_predominante": "tabelas" | "narrativo" | "misto",
  "qualidade_extracao_texto": "alta" | "media" | "baixa",
  "presenca_imagens_tabelas": true/false,
  "nivel_complexidade": "simples" | "moderado" | "complexo",
  "recomendacao_processamento": "leitura_completa" | "batch_paginas" | "extracao_seletiva"
}
```

## REGRAS CRÍTICAS

1. ✅ **DESCUBRA, NÃO ASSUMA**: Se não encontrou algo, NÃO invente
2. ✅ **USE OS TERMOS EXATOS** do documento (não traduza/normalize)
3. ✅ **IDENTIFIQUE PADRÕES**: Códigos, formatações, estruturas repetidas
4. ✅ **PRIORIZE**: Marque importância 10 para dados críticos (valores, totais)
5. ✅ **SEJA ESPECÍFICO**: "Despesas por Órgão - páginas 45-120" não "Despesas"

## OUTPUT

Retorne APENAS JSON (sem markdown, sem explicações):

```json
{
  "tipo_documento": "LOA",
  "metadados": {...},
  "secoes_identificadas": [...],
  "entidades_identificadas": {...},
  "analise_estrutural": {...},
  "sugestao_proxima_fase": "string descrevendo como processar este documento"
}
```

**LEMBRE-SE**: Cada documento é ÚNICO. Não force padrões que não existem!
'''
    
    # =========================================================================
    # FASE 2: EXTRAÇÃO ADAPTATIVA EM BATCHES
    # =========================================================================
    
    def extract_section_batch(
        self, 
        pdf_path: str, 
        section_info: Dict[str, Any],
        page_start: int,
        page_end: int
    ) -> Dict[str, Any]:
        """
        FASE 2: Extrai dados de uma seção específica usando informações da descoberta.
        
        Args:
            pdf_path: Caminho do PDF
            section_info: Informações da seção (da fase de descoberta)
            page_start: Página inicial
            page_end: Página final
            
        Returns:
            Dados extraídos em formato flexível (JSONB-ready)
        """
        logger.info(f"Extraindo seção: {section_info.get('nome')} (págs {page_start}-{page_end})")
        
        # Extrair páginas
        reader = PdfReader(pdf_path)
        pages_text = []
        
        for i in range(page_start - 1, min(page_end, len(reader.pages))):
            try:
                text = reader.pages[i].extract_text() or ""
                if text:
                    pages_text.append(f"--- PÁGINA {i+1} ---\n{text}")
            except Exception as e:
                logger.warning(f"Erro ao ler página {i+1}: {e}")
        
        batch_text = "\n\n".join(pages_text)
        
        # Construir prompt adaptativo para esta seção
        prompt = self._build_adaptive_extraction_prompt(section_info)
        
        full_prompt = f"{prompt}\n\n---\n\nCONTEÚDO DA SEÇÃO:\n\n{batch_text}"
        
        logger.info("Chamando Gemini para extração...")
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=65536
            )
        )
        
        data = self._parse_json_response(response.text)
        
        if not data:
            logger.warning(f"Falha ao extrair seção {section_info.get('nome')}")
            return {}
        
        logger.info(f"✅ Seção extraída: {len(str(data))} chars de dados")
        
        return {
            "secao": section_info.get('nome'),
            "paginas": f"{page_start}-{page_end}",
            "tipo": section_info.get('tipo'),
            "dados": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _build_adaptive_extraction_prompt(self, section_info: Dict[str, Any]) -> str:
        """
        Constrói um prompt de extração ADAPTADO à seção específica.
        Usa as informações descobertas na Fase 1.
        """
        section_name = section_info.get('nome', 'Seção')
        section_type = section_info.get('tipo', 'desconhecido')
        columns = section_info.get('colunas_ou_campos', [])
        keywords = section_info.get('palavras_chave', [])
        
        prompt = f'''# EXTRAÇÃO ADAPTATIVA: {section_name}

## CONTEXTO
Você está extraindo dados da seção "{section_name}" de um documento orçamentário.

**Tipo identificado**: {section_type}
**Campos/Colunas esperados**: {", ".join(columns) if columns else "descobrir dinamicamente"}
**Palavras-chave**: {", ".join(keywords) if keywords else "n/a"}

## SUA MISSÃO

Extraia TODOS os dados desta seção de forma estruturada e completa.

### REGRAS CRÍTICAS

1. ✅ **EXTRAIA TUDO**: Não limite quantidade - inclua TODAS as linhas/registros
2. ✅ **VALORES NUMÉRICOS**: Sempre como números (sem formatação): 1234567.89
3. ✅ **CÓDIGOS**: Preserve formato original exato
4. ✅ **NOMES**: Use nome completo como aparece no documento
5. ✅ **ESTRUTURA FLEXÍVEL**: Adapte o JSON ao conteúdo real, não force schemas

'''
        
        if section_type == "tabela_estruturada":
            prompt += '''
### FORMATO DE SAÍDA PARA TABELAS

```json
{
  "tipo": "tabela",
  "colunas": ["col1", "col2", "col3"],  // Nomes reais das colunas
  "registros": [
    {"col1": "valor1", "col2": 123.45, "col3": "valor3"},
    // ... TODOS os registros
  ],
  "total_registros": 999,
  "totalizacao": {
    "col2_soma": 999999.99,
    // outros totais se houver
  }
}
```
'''
        elif section_type == "texto_narrativo":
            prompt += '''
### FORMATO DE SAÍDA PARA TEXTO NARRATIVO

```json
{
  "tipo": "texto",
  "secoes": [
    {"titulo": "Subtítulo 1", "conteudo": "Texto completo..."},
    {"titulo": "Subtítulo 2", "conteudo": "Texto completo..."}
  ],
  "principais_pontos": ["ponto 1", "ponto 2"],
  "valores_mencionados": [
    {"descricao": "Receita total", "valor": 12345.67}
  ]
}
```
'''
        else:
            prompt += '''
### FORMATO DE SAÍDA GENÉRICO

```json
{
  "tipo": "dados",
  "conteudo": {
    // Estruture de acordo com o conteúdo real
    // Use arrays para listas, objetos para estruturas aninhadas
  }
}
```
'''
        
        prompt += '''

## IMPORTANTE

- **NÃO OMITA DADOS**: Se há 100 registros, extraia os 100
- **NÃO RESUMA**: Queremos dados completos, não sumários
- **NÃO INVENTE**: Se não tem certeza, use null

Retorne APENAS JSON (sem markdown):
'''
        
        return prompt
    
    # =========================================================================
    # FASE 3: CONSOLIDAÇÃO E VALIDAÇÃO
    # =========================================================================
    
    def consolidate_extracted_data(
        self, 
        all_extractions: List[Dict[str, Any]],
        document_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        FASE 3: Consolida todos os dados extraídos, resolve conflitos e valida.
        
        Args:
            all_extractions: Lista de todos os batches extraídos
            document_structure: Estrutura descoberta na Fase 1
            
        Returns:
            Dados consolidados e validados
        """
        logger.info("=" * 70)
        logger.info("FASE 3: CONSOLIDAÇÃO DOS DADOS EXTRAÍDOS")
        logger.info("=" * 70)
        
        # Preparar resumo para o Gemini
        summary = {
            "documento": document_structure.get("tipo_documento"),
            "total_secoes_extraidas": len(all_extractions),
            "secoes": [
                {
                    "nome": ext.get("secao"),
                    "paginas": ext.get("paginas"),
                    "tamanho_dados": len(str(ext.get("dados", {})))
                }
                for ext in all_extractions
            ]
        }
        
        # Construir prompt de consolidação
        prompt = self._build_consolidation_prompt(document_structure, summary)
        
        # Preparar dados para consolidação (pode ser grande!)
        extractions_json = json.dumps(all_extractions, ensure_ascii=False, indent=2)
        
        full_prompt = f"{prompt}\n\n---\n\nDADOS EXTRAÍDOS:\n\n{extractions_json}"
        
        logger.info("Chamando Gemini para consolidação...")
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                max_output_tokens=65536
            )
        )
        
        consolidated = self._parse_json_response(response.text)
        
        if not consolidated:
            logger.error("Falha na consolidação")
            # Fallback: retornar dados brutos
            return {
                "status": "parcial",
                "dados_brutos": all_extractions
            }
        
        logger.info("✅ Dados consolidados com sucesso!")
        
        return consolidated
    
    def _build_consolidation_prompt(
        self, 
        structure: Dict[str, Any],
        summary: Dict[str, Any]
    ) -> str:
        """Prompt para consolidação final dos dados."""
        return f'''# CONSOLIDAÇÃO FINAL DE DADOS ORÇAMENTÁRIOS

## CONTEXTO

Você recebeu dados extraídos de múltiplas seções de um documento {structure.get('tipo_documento')}.

Total de seções: {summary.get('total_secoes_extraidas')}

## SUA MISSÃO

Consolide TODOS os dados em uma estrutura final coerente e validada.

### TAREFAS

1. **AGREGAR**: Junte dados relacionados de diferentes seções
2. **VALIDAR**: Verifique consistência de totais e valores
3. **RESOLVER CONFLITOS**: Se houver valores duplicados, use o mais completo
4. **ESTRUTURAR**: Organize hierarquicamente (overview → detalhes)
5. **METADADOS**: Inclua metadados do documento

### FORMATO DE SAÍDA

```json
{{
  "metadados": {{
    "tipo_documento": "LOA",
    "ano": 2026,
    "municipio": "...",
    "data_processamento": "2026-01-12T...",
    "total_secoes_processadas": {summary.get('total_secoes_extraidas')}
  }},
  "dados": {{
    // Estrutura hierárquica completa
    // Exemplo para LOA:
    "visao_geral": {{...}},
    "receitas": {{...}},
    "despesas": {{
      "por_orgao": [...],  // TODOS os órgãos
      "por_programa": [...],
      "por_categoria": [...]
    }},
    "investimentos_regionais": [...],
    // ... outras seções descobertas
  }},
  "validacao": {{
    "totais_conferidos": true,
    "inconsistencias": [],
    "dados_faltantes": [],
    "qualidade_extracao": "alta" | "media" | "baixa"
  }}
}}
```

### REGRAS

- ✅ Preserve TODOS os dados extraídos
- ✅ Use a terminologia EXATA do documento
- ✅ Valores sempre como números
- ✅ Arrays sempre como arrays (não strings)

Retorne APENAS JSON consolidado:
'''
    
    # =========================================================================
    # UTILITÁRIOS
    # =========================================================================
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extrai JSON da resposta do Gemini."""
        try:
            # Tentar parse direto
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Tentar extrair de code blocks
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'\{.*\}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                json_text = match.group(1) if '```' in pattern else match.group(0)
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    continue
        
        logger.error("Não foi possível parsear JSON")
        logger.debug(f"Resposta (primeiros 500 chars): {response_text[:500]}")
        return None
    
    # =========================================================================
    # FLUXO COMPLETO
    # =========================================================================
    
    def extract_document_adaptive(
        self, 
        pdf_path: str,
        max_pages_per_batch: int = 100
    ) -> Dict[str, Any]:
        """
        Fluxo completo de extração adaptativa.
        
        Args:
            pdf_path: Caminho do PDF
            max_pages_per_batch: Máximo de páginas por batch
            
        Returns:
            Dados completos consolidados
        """
        logger.info("=" * 70)
        logger.info("EXTRAÇÃO ADAPTATIVA COMPLETA")
        logger.info("=" * 70)
        
        # FASE 1: Descoberta
        structure = self.discover_document_structure(pdf_path)
        
        # FASE 2: Extração em batches
        all_extractions = []
        
        sections = structure.get('secoes_identificadas', [])
        # Ordenar por importância (críticas primeiro)
        sections.sort(key=lambda s: s.get('importancia', 0), reverse=True)
        
        for section in sections:
            page_start = section.get('paginas_inicio', 1)
            page_end = section.get('paginas_fim', page_start + 10)
            
            # Dividir seção grande em batches
            current = page_start
            while current <= page_end:
                batch_end = min(current + max_pages_per_batch, page_end)
                
                try:
                    extraction = self.extract_section_batch(
                        pdf_path, 
                        section, 
                        current, 
                        batch_end
                    )
                    all_extractions.append(extraction)
                except Exception as e:
                    logger.error(f"Erro ao extrair batch {current}-{batch_end}: {e}")
                
                current = batch_end + 1
        
        # FASE 3: Consolidação
        consolidated = self.consolidate_extracted_data(all_extractions, structure)
        
        logger.info("=" * 70)
        logger.info("✅ EXTRAÇÃO ADAPTATIVA CONCLUÍDA")
        logger.info("=" * 70)
        
        return consolidated

