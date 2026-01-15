"""
Serviço de Extração em Batches para documentos grandes.

Quebra PDFs grandes em batches menores e processa cada um separadamente,
depois consolida os resultados.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal
import structlog
import google.generativeai as genai
from sqlalchemy.orm import Session
from pypdf import PdfReader

from app.core.config import settings
from app.models.dashboard_models import ExercicioOrcamentario
from app.services.dashboard_extraction_service import DashboardExtractionService
from app.services.gemini_with_timeout import GeminiWithTimeout

logger = structlog.get_logger()


class BatchExtractionService:
    """Serviço para processar documentos grandes em batches."""
    
    def __init__(self, pages_per_batch: int = 100):
        """
        Inicializa o serviço.
        
        Args:
            pages_per_batch: Número de páginas por batch (padrão: 100)
        """
        # Usar cliente customizado com timeout de 10 minutos
        self.model = GeminiWithTimeout(
            api_key=settings.GEMINI_API_KEY,
            model_name='gemini-2.5-pro',
            timeout=600  # 10 minutos por batch
        )
        self.pages_per_batch = pages_per_batch
        self.base_service = DashboardExtractionService()
        self.checkpoint_root = Path("/tmp/dashboard_batches")
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
    
    def extract_from_pdf_in_batches(
        self,
        pdf_path: str,
        db: Session,
        municipality_id: str = None,
        document_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Extrai dados de um PDF grande processando em batches.
        
        Args:
            pdf_path: Caminho do PDF
            db: Sessão do banco
            municipality_id: ID do município
            
        Returns:
            ExercicioOrcamentario com dados consolidados
        """
        logger.info("=" * 70)
        logger.info("EXTRAÇÃO EM BATCHES INICIADA")
        logger.info("=" * 70)
        
        # 1. Ler PDF e determinar batches
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        logger.info(f"PDF: {total_pages} páginas")
        logger.info(f"Batch size: {self.pages_per_batch} páginas")
        
        num_batches = (total_pages + self.pages_per_batch - 1) // self.pages_per_batch
        logger.info(f"Total de batches: {num_batches}")
        
        # 2. Definir checkpoint/cache
        cache_dir = None
        progress_file = None
        if document_id:
            cache_dir = self.checkpoint_root / document_id
            cache_dir.mkdir(parents=True, exist_ok=True)
            progress_file = Path(f"/tmp/processing_{document_id}.txt")
        
        processed_batches = set()
        if cache_dir and cache_dir.exists():
            for file in cache_dir.glob("batch_*.json"):
                try:
                    num = int(file.stem.split("_")[1])
                    processed_batches.add(num)
                except Exception:
                    continue
        
        # 3. Processar cada batch (com retry) e salvar checkpoint
        all_data = []
        
        for batch_num in range(num_batches):
            start_page = batch_num * self.pages_per_batch
            end_page = min((batch_num + 1) * self.pages_per_batch, total_pages)
            
            logger.info(f"\n📦 BATCH {batch_num + 1}/{num_batches}")
            logger.info(f"   Páginas: {start_page + 1} - {end_page}")
            
            # Se já existe em cache, pular chamada ao modelo
            if (batch_num + 1) in processed_batches:
                logger.info(f"   ↩️  Batch {batch_num + 1} já em cache, pulando Gemini")
                continue
            
            attempts = 0
            max_attempts = 3
            batch_data = None
            while attempts < max_attempts:
                attempts += 1
                try:
                    batch_data = self._process_batch(
                        reader,
                        start_page,
                        end_page,
                        batch_num,
                        num_batches
                    )
                    if batch_data:
                        logger.info(f"   ✅ Batch {batch_num + 1} processado (tentativa {attempts})")
                        break
                    else:
                        logger.warning(f"   ⚠️  Batch {batch_num + 1} vazio (tentativa {attempts})")
                except Exception as e:
                    logger.error(f"   ❌ Erro no batch {batch_num + 1} (tentativa {attempts}): {e}")
                time.sleep(attempts)  # backoff simples
            
            if not batch_data:
                logger.warning(f"   ⚠️  Batch {batch_num + 1} não pôde ser processado após {max_attempts} tentativas")
                continue
            
            all_data.append(batch_data)
            
            # Salvar checkpoint do batch
            if cache_dir:
                try:
                    batch_path = cache_dir / f"batch_{batch_num + 1}.json"
                    with open(batch_path, "w", encoding="utf-8") as f:
                        json.dump(batch_data, f, ensure_ascii=False)
                except Exception as e:
                    logger.warning(f"   ⚠️  Falha ao salvar checkpoint do batch {batch_num + 1}: {e}")
            
            # Atualizar progresso visível para /progress
            if progress_file:
                try:
                    progress_file.write_text(str(batch_num + 1))
                except Exception:
                    pass
        
        # 4. Recarregar batches do cache (incluindo os já existentes) para consolidar sem Gemini
        if cache_dir and cache_dir.exists():
            cached_batches = []
            for file in sorted(cache_dir.glob("batch_*.json")):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        cached_batches.append(json.load(f))
                except Exception as e:
                    logger.warning(f"   ⚠️  Falha ao ler checkpoint {file}: {e}")
            if cached_batches:
                logger.info(f"\n🔄 Usando {len(cached_batches)} batches do cache para consolidar")
                all_data = cached_batches
        
        # 5. Consolidar todos os batches
        logger.info(f"\n🔄 Consolidando {len(all_data)} batches...")
        consolidated_data = self._consolidate_batches(all_data)
        
        # Salvar consolidado em disco para retomada
        if document_id:
            try:
                consolidated_path = self.checkpoint_root / f"consolidated_{document_id}.json"
                with open(consolidated_path, "w", encoding="utf-8") as f:
                    json.dump(consolidated_data, f, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"⚠️  Não foi possível salvar consolidado: {e}")
        
        # 6. Salvar no banco usando o serviço base
        logger.info("💾 Salvando dados consolidados no banco...")
        exercicio = self.base_service._save_to_database(
            consolidated_data,
            db,
            municipality_id
        )
        
        # GARANTIR COMMIT FINAL (db.commit já é feito em _save_to_database, mas garantir)
        try:
            db.flush()  # Força escrita no banco
            logger.info("✅ Flush executado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro no flush: {e}")
        
        # 7. EXTRAÇÃO DETERMINÍSTICA DE REGIONAIS
        # O Gemini frequentemente falha em extrair a tabela de regionalização corretamente
        # Usa parser com regex para garantir extração precisa
        logger.info("\n" + "=" * 70)
        logger.info("🎯 ETAPA 2: EXTRAÇÃO DETERMINÍSTICA DE REGIONAIS")
        logger.info("=" * 70)
        logger.info("Usando parser especializado para tabela de regionalização...")
        
        try:
            regional_data = self.base_service._extract_regional_data_deterministic(pdf_path)
            
            if regional_data:
                logger.info(f"✅ Parser encontrou {len(regional_data)} regionais na tabela")
                
                # Deletar regionais incorretas do Gemini
                from app.models.dashboard_models import InvestimentoRegional
                regionais_antigas = db.query(InvestimentoRegional).filter(
                    InvestimentoRegional.exercicio_id == exercicio.id
                ).count()
                
                if regionais_antigas > 0:
                    logger.info(f"🗑️  Removendo {regionais_antigas} regionais incorretas do Gemini...")
                    db.query(InvestimentoRegional).filter(
                        InvestimentoRegional.exercicio_id == exercicio.id
                    ).delete()
                    db.flush()
                
                # Salvar regionais corretas do parser
                self.base_service._save_regionais_deterministic(regional_data, exercicio, db)
                logger.info(f"✅ {len(regional_data)} regionais corretas salvas com valores reais")
            else:
                logger.warning("⚠️  Parser determinístico não encontrou tabela de regionalização")
                logger.warning("   Mantendo dados do Gemini (podem estar incompletos)")
        except Exception as e:
            logger.error(f"❌ Erro na extração determinística de regionais: {e}")
            logger.warning("   Mantendo dados do Gemini (podem estar incompletos)")
        
        logger.info("=" * 70)
        logger.info("✅ EXTRAÇÃO EM BATCHES CONCLUÍDA")
        logger.info(f"📝 Exercício salvo: ID={exercicio.id}, Ano={exercicio.ano}")
        logger.info("=" * 70)
        
        return exercicio
    
    def _process_batch(
        self,
        reader: PdfReader,
        start_page: int,
        end_page: int,
        batch_num: int,
        total_batches: int
    ) -> Optional[Dict[str, Any]]:
        """Processa um batch de páginas."""
        
        # Extrair texto das páginas do batch
        batch_text_parts = []
        for i in range(start_page, end_page):
            try:
                page_text = reader.pages[i].extract_text()
                if page_text:
                    batch_text_parts.append(f"--- PÁGINA {i+1} ---\n{page_text}")
            except Exception as e:
                logger.warning(f"Erro ao extrair página {i+1}: {e}")
                continue
        
        if not batch_text_parts:
            return None
        
        batch_text = "\n\n".join(batch_text_parts)
        
        # Criar prompt específico para batch
        prompt = self._build_batch_prompt(batch_num, total_batches)
        
        full_prompt = f"{prompt}\n\n---\n\nCONTEÚDO DO BATCH:\n\n{batch_text}"
        
        # Chamar Gemini
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=32768
                )
            )
            
            # Parsear JSON
            return self.base_service._parse_json_response(response.text)
            
        except Exception as e:
            logger.error(f"Erro ao processar batch: {e}")
            return None
    
    def _build_batch_prompt(self, batch_num: int, total_batches: int) -> str:
        """Constrói prompt para processar um batch específico."""
        return f'''# EXTRAÇÃO DE DADOS ORÇAMENTÁRIOS - BATCH {batch_num + 1} de {total_batches}

Você está processando parte de um documento orçamentário brasileiro (LOA).

## SUA MISSÃO

Extraia TODOS os dados estruturados deste batch de páginas e retorne em JSON.

## IMPORTANTE

- Este é o batch {batch_num + 1} de {total_batches}
- Extraia TUDO que encontrar neste batch
- Não assuma nada - use apenas o que está nas páginas
- Se não encontrar dados de uma seção, use arrays/objetos vazios

## ESTRUTURA DO JSON

```json
{{
  "metadados": {{
    "tipo_documento": "LOA",
    "ano_exercicio": null,  // Extrair se encontrar
    "municipio": null,
    "estado": null,
    "batch_info": {{
      "batch_numero": {batch_num + 1},
      "total_batches": {total_batches}
    }}
  }},
  "visao_geral": {{
    "orcamento_total": 0.0,
    "orcamento_fiscal": 0.0,
    "orcamento_seguridade": 0.0
  }},
  "receitas": {{
    "correntes": {{
      "categorias": []  // Lista de {{nome, valor}}
    }},
    "capital": {{
      "categorias": []
    }}
  }},
  "despesas": {{
    "por_categoria_economica": [],  // Lista de {{nome, valor_total, valor_fiscal, valor_seguridade}}
    "por_orgao": [],  // Lista de {{codigo, nome, valor_total, valor_fiscal, valor_seguridade}}
    "por_programa": []  // Lista de {{codigo, nome, valor_total, valor_fiscal, valor_seguridade}}
  }},
  "investimento_regional": [],  // Se houver
  "participacao_social": {{}},
  "limites_constitucionais": {{}}
}}
```

## REGRAS CRÍTICAS

1. TODOS os valores monetários como NÚMEROS (não strings): 1234567.89
2. Arrays sempre como arrays (nunca null ou string)
3. Extraia TODOS os órgãos, programas e categorias deste batch
4. Se não encontrar, retorne estrutura vazia (não omita)

Retorne APENAS o JSON (sem markdown, sem explicações):
'''
    
    def _consolidate_batches(self, batches_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolida dados de múltiplos batches em um único dataset.
        """
        if not batches_data:
            raise ValueError("Nenhum batch foi processado com sucesso")
        
        # Inicializar estrutura consolidada
        consolidated = {
            "metadados": {},
            "visao_geral": {
                "orcamento_total": 0.0,
                "orcamento_fiscal": 0.0,
                "orcamento_seguridade": 0.0
            },
            "receitas": {
                "correntes": {"categorias": []},
                "capital": {"categorias": []}
            },
            "despesas": {
                "por_categoria_economica": [],
                "por_orgao": [],
                "por_programa": []
            },
            "investimento_regional": [],
            "participacao_social": {},
            "limites_constitucionais": {}
        }
        
        # Consolidar metadados (pegar do primeiro batch que tiver)
        for batch in batches_data:
            meta = batch.get("metadados", {})
            if meta.get("ano_exercicio"):
                consolidated["metadados"] = meta
                break
        
        # Se não encontrou metadados, usar padrão
        if not consolidated["metadados"]:
            consolidated["metadados"] = {
                "tipo_documento": "LOA",
                "ano_exercicio": 2025,  # Assumir ano atual
                "municipio": "Fortaleza",
                "estado": "CE"
            }
        
        # Consolidar visão geral (pegar maior valor encontrado)
        for batch in batches_data:
            vg = batch.get("visao_geral", {})
            if vg.get("orcamento_total", 0) > consolidated["visao_geral"]["orcamento_total"]:
                consolidated["visao_geral"] = vg
        
        # Consolidar listas (remover duplicatas)
        seen_orgaos = set()
        seen_programas = set()
        seen_categorias = set()
        seen_receitas_correntes = set()
        seen_receitas_capital = set()
        
        for batch in batches_data:
            # Órgãos
            for orgao in batch.get("despesas", {}).get("por_orgao", []):
                codigo = orgao.get("codigo", orgao.get("nome", ""))
                if codigo and codigo not in seen_orgaos:
                    seen_orgaos.add(codigo)
                    consolidated["despesas"]["por_orgao"].append(orgao)
            
            # Programas
            for prog in batch.get("despesas", {}).get("por_programa", []):
                codigo = prog.get("codigo", prog.get("nome", ""))
                if codigo and codigo not in seen_programas:
                    seen_programas.add(codigo)
                    consolidated["despesas"]["por_programa"].append(prog)
            
            # Categorias econômicas
            for cat in batch.get("despesas", {}).get("por_categoria_economica", []):
                nome = cat.get("nome", "")
                if nome and nome not in seen_categorias:
                    seen_categorias.add(nome)
                    consolidated["despesas"]["por_categoria_economica"].append(cat)
            
            # Receitas correntes
            for rec in batch.get("receitas", {}).get("correntes", {}).get("categorias", []):
                nome = rec.get("nome", "")
                if nome and nome not in seen_receitas_correntes:
                    seen_receitas_correntes.add(nome)
                    consolidated["receitas"]["correntes"]["categorias"].append(rec)
            
            # Receitas de capital
            for rec in batch.get("receitas", {}).get("capital", {}).get("categorias", []):
                nome = rec.get("nome", "")
                if nome and nome not in seen_receitas_capital:
                    seen_receitas_capital.add(nome)
                    consolidated["receitas"]["capital"]["categorias"].append(rec)
            
            # Regionais (manter todos, podem ter dados diferentes)
            # VALIDAÇÃO: garantir que cada regional é um dicionário válido
            for regional in batch.get("investimento_regional", []):
                # Validar tipo antes de adicionar
                if isinstance(regional, dict):
                    consolidated["investimento_regional"].append(regional)
                elif isinstance(regional, list):
                    # Se regional for uma lista, extrair dicionários válidos
                    logger.warning(f"Regional veio como lista, extraindo items: {regional}")
                    for item in regional:
                        if isinstance(item, dict):
                            consolidated["investimento_regional"].append(item)
                else:
                    logger.warning(f"Regional inválido ignorado (tipo {type(regional)}): {regional}")
        
        # Pegar participação social e limites do último batch que tiver
        for batch in reversed(batches_data):
            if batch.get("participacao_social"):
                consolidated["participacao_social"] = batch["participacao_social"]
                break
        
        for batch in reversed(batches_data):
            if batch.get("limites_constitucionais"):
                consolidated["limites_constitucionais"] = batch["limites_constitucionais"]
                break
        
        logger.info(f"Consolidação completa:")
        logger.info(f"  - Órgãos: {len(consolidated['despesas']['por_orgao'])}")
        logger.info(f"  - Programas: {len(consolidated['despesas']['por_programa'])}")
        logger.info(f"  - Categorias despesa: {len(consolidated['despesas']['por_categoria_economica'])}")
        logger.info(f"  - Receitas correntes: {len(consolidated['receitas']['correntes']['categorias'])}")
        
        return consolidated
    
    def extract_ldo_from_pdf_in_batches(
        self,
        pdf_path: str,
        db: Session,
        municipality_id: str = None,
        document_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Extrai dados de LDO de um PDF processando em batches.
        Similar ao método de LOA mas usa prompt e salvamento específicos de LDO.
        
        Args:
            pdf_path: Caminho do PDF
            db: Sessão do banco
            municipality_id: ID do município
            
        Returns:
            ExercicioOrcamentario com dados de LDO
        """
        logger.info("=" * 70)
        logger.info("EXTRAÇÃO LDO EM BATCHES INICIADA")
        logger.info("=" * 70)
        
        # 1. Ler PDF e determinar batches
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        logger.info(f"PDF LDO: {total_pages} páginas")
        logger.info(f"Batch size: {self.pages_per_batch} páginas")
        
        num_batches = (total_pages + self.pages_per_batch - 1) // self.pages_per_batch
        logger.info(f"Total de batches: {num_batches}")
        
        # 2. Processar cada batch usando prompt de LDO
        all_data = []
        progress_file = Path(f"/tmp/processing_{document_id}.txt") if document_id else None
        
        for batch_num in range(num_batches):
            start_page = batch_num * self.pages_per_batch
            end_page = min((batch_num + 1) * self.pages_per_batch, total_pages)
            
            logger.info(f"\n📦 BATCH {batch_num + 1}/{num_batches}")
            logger.info(f"   Páginas: {start_page + 1} - {end_page}")
            
            try:
                batch_data = self._process_ldo_batch(
                    reader,
                    start_page,
                    end_page,
                    batch_num,
                    num_batches
                )
                
                if batch_data:
                    all_data.append(batch_data)
                    logger.info(f"   ✅ Batch {batch_num + 1} processado")
                else:
                    logger.warning(f"   ⚠️  Batch {batch_num + 1} retornou vazio")
                    
            except Exception as e:
                logger.error(f"   ❌ Erro no batch {batch_num + 1}: {e}")
                continue
            
            if progress_file:
                try:
                    progress_file.write_text(str(batch_num + 1))
                except Exception:
                    pass
        
        # 3. Consolidar batches de LDO
        logger.info(f"\n🔄 Consolidando {len(all_data)} batches de LDO...")
        consolidated_data = self._consolidate_ldo_batches(all_data)
        
        # 4. Salvar usando método específico de LDO
        logger.info("💾 Salvando dados LDO consolidados no banco...")
        exercicio = self.base_service._save_ldo_to_database(
            consolidated_data,
            db,
            municipality_id
        )
        
        logger.info("=" * 70)
        logger.info("✅ EXTRAÇÃO LDO EM BATCHES CONCLUÍDA")
        logger.info("=" * 70)
        
        return exercicio
    
    def _process_ldo_batch(
        self,
        reader: PdfReader,
        start_page: int,
        end_page: int,
        batch_num: int,
        total_batches: int
    ) -> Optional[Dict]:
        """Processa um batch de páginas específico para LDO."""
        from app.services.ldo_extraction_prompts import LDO_EXTRACTION_PROMPT
        
        # Extrair texto das páginas do batch
        batch_text_parts = []
        for page_num in range(start_page, end_page):
            try:
                page = reader.pages[page_num]
                text = page.extract_text()
                batch_text_parts.append(f"=== PÁGINA {page_num + 1} ===\n{text}")
            except Exception as e:
                logger.warning(f"Erro ao extrair página {page_num + 1}: {e}")
                continue
        
        batch_text = "\n\n".join(batch_text_parts)
        
        # Usar prompt de LDO
        full_prompt = f"{LDO_EXTRACTION_PROMPT}\n\n---\n\nCONTEÚDO DO BATCH {batch_num + 1}/{total_batches}:\n\n{batch_text}"
        
        # Chamar Gemini
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=32768
                )
            )
            
            # Parsear JSON
            return self.base_service._parse_json_response(response.text)
            
        except Exception as e:
            logger.error(f"Erro ao processar batch LDO: {e}")
            return None
    
    def _consolidate_ldo_batches(self, batches_data: List[Dict]) -> Dict:
        """
        Consolida múltiplos batches de dados de LDO em uma estrutura única.
        Mescla informações complementares e remove duplicatas.
        """
        if not batches_data:
            raise ValueError("Nenhum batch LDO foi processado com sucesso")
        
        # Começar com estrutura do primeiro batch
        consolidated = batches_data[0].copy()
        
        # Mesclar dados dos outros batches
        for batch in batches_data[1:]:
            # Mesclar metas e prioridades
            if batch.get("metas_prioridades"):
                mp = batch["metas_prioridades"]
                if not consolidated.get("metas_prioridades"):
                    consolidated["metas_prioridades"] = mp
                else:
                    # Adicionar prioridades únicas
                    if mp.get("prioridades"):
                        consolidated["metas_prioridades"].setdefault("prioridades", []).extend(
                            p for p in mp["prioridades"] 
                            if p not in consolidated["metas_prioridades"]["prioridades"]
                        )
                    # Adicionar metas setoriais únicas
                    if mp.get("metas_setoriais"):
                        consolidated["metas_prioridades"].setdefault("metas_setoriais", []).extend(
                            m for m in mp["metas_setoriais"]
                            if m not in consolidated["metas_prioridades"]["metas_setoriais"]
                        )
            
            # Mesclar metas fiscais (usar a mais completa)
            if batch.get("metas_fiscais"):
                if not consolidated.get("metas_fiscais") or \
                   len(str(batch["metas_fiscais"])) > len(str(consolidated.get("metas_fiscais", {}))):
                    consolidated["metas_fiscais"] = batch["metas_fiscais"]
            
            # Mesclar riscos fiscais
            if batch.get("riscos_fiscais"):
                rf = batch["riscos_fiscais"]
                if not consolidated.get("riscos_fiscais"):
                    consolidated["riscos_fiscais"] = rf
                else:
                    # Adicionar riscos únicos
                    if rf.get("riscos_identificados"):
                        consolidated["riscos_fiscais"].setdefault("riscos_identificados", []).extend(
                            r for r in rf["riscos_identificados"]
                            if r not in consolidated["riscos_fiscais"]["riscos_identificados"]
                        )
        
        logger.info(f"Consolidação LDO completa")
        
        return consolidated

