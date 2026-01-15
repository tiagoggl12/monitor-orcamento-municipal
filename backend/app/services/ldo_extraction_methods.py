"""
Adição ao dashboard_extraction_service.py - Métodos para Extração de LDO
"""

# ADICIONAR AO FINAL DA CLASSE DashboardExtractionService:

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
        from app.models.ldo_models import (
            MetasPrioridadesLDO,
            MetasFiscaisLDO,
            RiscosFiscaisLDO,
            PoliticasSetoriaisLDO,
            AvaliacaoAnteriorLDO
        )
        
        logger.info("=" * 70)
        logger.info("INICIANDO EXTRAÇÃO DE LDO")
        logger.info("=" * 70)
        logger.info("Arquivo:", pdf_path=pdf_path)
        
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
    
    def _save_ldo_to_database(
        self, 
        ldo_data: dict, 
        db: Session, 
        municipality_id: str = None
    ) -> ExercicioOrcamentario:
        """
        Salva dados extraídos da LDO no banco de dados.
        """
        from app.models.ldo_models import (
            MetasPrioridadesLDO,
            MetasFiscaisLDO,
            RiscosFiscaisLDO,
            PoliticasSetoriaisLDO,
            AvaliacaoAnteriorLDO
        )
        
        metadados = ldo_data.get("metadados", {})
        
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
        metas_prioridades_data = ldo_data.get("metas_prioridades", {})
        if metas_prioridades_data:
            metas_prioridades = MetasPrioridadesLDO(
                exercicio_id=exercicio.id,
                prioridades=metas_prioridades_data.get("prioridades", []),
                diretrizes_gerais=metas_prioridades_data.get("diretrizes_gerais", []),
                metas_setoriais=metas_prioridades_data.get("metas_setoriais", {}),
                programas_prioritarios=metas_prioridades_data.get("programas_prioritarios", []),
                diretrizes_setoriais=metas_prioridades_data.get("diretrizes_setoriais", {})
            )
            db.add(metas_prioridades)
        
        # 3. Salvar Metas Fiscais
        metas_fiscais_data = ldo_data.get("metas_fiscais", {})
        if metas_fiscais_data:
            metas_fiscais = MetasFiscaisLDO(
                exercicio_id=exercicio.id,
                resultado_primario_meta=self._to_decimal(metas_fiscais_data.get("resultado_primario", {}).get("meta")),
                resultado_primario_ano_anterior=self._to_decimal(metas_fiscais_data.get("resultado_primario", {}).get("ano_anterior")),
                resultado_primario_dois_anos_antes=self._to_decimal(metas_fiscais_data.get("resultado_primario", {}).get("dois_anos_antes")),
                resultado_nominal_meta=self._to_decimal(metas_fiscais_data.get("resultado_nominal", {}).get("meta")),
                resultado_nominal_ano_anterior=self._to_decimal(metas_fiscais_data.get("resultado_nominal", {}).get("ano_anterior")),
                divida_consolidada_meta=self._to_decimal(metas_fiscais_data.get("divida_consolidada", {}).get("meta")),
                divida_consolidada_percentual_rcl=self._to_decimal(metas_fiscais_data.get("divida_consolidada", {}).get("percentual_rcl")),
                divida_consolidada_ano_anterior=self._to_decimal(metas_fiscais_data.get("divida_consolidada", {}).get("ano_anterior")),
                rcl_prevista=self._to_decimal(metas_fiscais_data.get("rcl_prevista")),
                rcl_ano_anterior=self._to_decimal(metas_fiscais_data.get("rcl_ano_anterior")),
                receita_total_prevista=self._to_decimal(metas_fiscais_data.get("receita_total_prevista")),
                despesa_total_prevista=self._to_decimal(metas_fiscais_data.get("despesa_total_prevista")),
                projecoes_trienio=metas_fiscais_data.get("projecoes_trienio", {}),
                premissas_macroeconomicas=metas_fiscais_data.get("premissas_macroeconomicas", {}),
                margem_expansao_despesas_obrigatorias=self._to_decimal(metas_fiscais_data.get("margem_expansao_despesas_obrigatorias")),
                renuncias_receita_total=self._to_decimal(metas_fiscais_data.get("renuncias_receita", {}).get("total")),
                renuncias_receita_detalhes=metas_fiscais_data.get("renuncias_receita", {}).get("detalhes", []),
                metodologia_calculo=metas_fiscais_data.get("metodologia_calculo"),
                observacoes=metas_fiscais_data.get("observacoes")
            )
            db.add(metas_fiscais)
        
        # 4. Salvar Riscos Fiscais
        riscos_fiscais_data = ldo_data.get("riscos_fiscais", {})
        if riscos_fiscais_data:
            riscos_fiscais = RiscosFiscaisLDO(
                exercicio_id=exercicio.id,
                riscos=riscos_fiscais_data.get("riscos", []),
                passivos_contingentes_total=self._to_decimal(riscos_fiscais_data.get("passivos_contingentes", {}).get("total")),
                passivos_contingentes_detalhes=riscos_fiscais_data.get("passivos_contingentes", {}).get("detalhes", []),
                demandas_judiciais_total=self._to_decimal(riscos_fiscais_data.get("demandas_judiciais", {}).get("total")),
                demandas_judiciais_detalhes=riscos_fiscais_data.get("demandas_judiciais", {}).get("detalhes", []),
                garantias_concedidas_total=self._to_decimal(riscos_fiscais_data.get("garantias_concedidas", {}).get("total")),
                garantias_concedidas_detalhes=riscos_fiscais_data.get("garantias_concedidas", {}).get("detalhes", []),
                operacoes_credito_riscos=riscos_fiscais_data.get("operacoes_credito_riscos", []),
                riscos_macroeconomicos=riscos_fiscais_data.get("riscos_macroeconomicos", {}),
                riscos_especificos_municipio=riscos_fiscais_data.get("riscos_especificos_municipio", []),
                avaliacao_geral_risco=riscos_fiscais_data.get("avaliacao_geral_risco"),
                total_exposicao_risco=self._to_decimal(riscos_fiscais_data.get("total_exposicao_risco")),
                percentual_exposicao_orcamento=self._to_decimal(riscos_fiscais_data.get("percentual_exposicao_orcamento"))
            )
            db.add(riscos_fiscais)
        
        # 5. Salvar Políticas Setoriais
        politicas_setoriais_data = ldo_data.get("politicas_setoriais", {})
        if politicas_setoriais_data:
            politicas_setoriais = PoliticasSetoriaisLDO(
                exercicio_id=exercicio.id,
                politicas=politicas_setoriais_data
            )
            db.add(politicas_setoriais)
        
        # 6. Salvar Avaliação Ano Anterior
        avaliacao_anterior_data = ldo_data.get("avaliacao_ano_anterior", {})
        if avaliacao_anterior_data:
            avaliacao_anterior = AvaliacaoAnteriorLDO(
                exercicio_id=exercicio.id,
                ano_avaliado=avaliacao_anterior_data.get("ano_avaliado"),
                metas_fiscais_cumpridas=avaliacao_anterior_data.get("metas_fiscais_cumpridas", {}),
                metas_setoriais_cumpridas=avaliacao_anterior_data.get("metas_setoriais_cumpridas", {}),
                avaliacao_geral=avaliacao_anterior_data.get("avaliacao_geral"),
                percentual_geral_cumprimento=self._to_decimal(avaliacao_anterior_data.get("percentual_geral_cumprimento")),
                justificativas_nao_cumprimento=avaliacao_anterior_data.get("justificativas_nao_cumprimento", [])
            )
            db.add(avaliacao_anterior)
        
        # Commit final
        db.commit()
        db.refresh(exercicio)
        
        logger.info(f"✅ LDO salva: {exercicio.tipo_documento} {exercicio.ano} - {exercicio.municipio}")
        
        return exercicio

