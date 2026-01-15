# 🚀 GUIA RÁPIDO: TESTANDO A IMPLEMENTAÇÃO LDO

## ⚡ Teste Rápido (5 minutos)

### 1. Verificar se as tabelas foram criadas

```bash
docker-compose exec backend python -c "
from app.core.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()

ldo_tables = [t for t in tables if 'ldo' in t]
print('\\n📊 Tabelas LDO:')
for table in sorted(ldo_tables):
    print(f'  ✅ {table}')
"
```

**Resultado esperado:**
```
📊 Tabelas LDO:
  ✅ avaliacao_anterior_ldo
  ✅ metas_fiscais_ldo
  ✅ metas_prioridades_ldo
  ✅ politicas_setoriais_ldo
  ✅ riscos_fiscais_ldo
```

---

### 2. Processar a LDO_2025.pdf

```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.document import Document
from app.services.dashboard_extraction_service import DashboardExtractionService

db = SessionLocal()

# Buscar LDO_2025.pdf
doc = db.query(Document).filter(
    Document.filename.like('%LDO%2025%')
).first()

if doc:
    print(f'✅ Documento encontrado: {doc.filename}')
    print(f'   Caminho: {doc.file_path}')
    print('\\n🚀 Iniciando processamento...')
    
    service = DashboardExtractionService()
    exercicio = service.extract_ldo_from_pdf(
        pdf_path=doc.file_path,
        db=db,
        municipality_id=doc.municipality_id
    )
    
    print(f'\\n✅ Sucesso! LDO {exercicio.ano} processada!')
else:
    print('❌ LDO_2025.pdf não encontrado')

db.close()
"
```

**⏱️ Tempo estimado:** 3-5 minutos (depende do tamanho da LDO e resposta da API do Gemini)

---

### 3. Verificar dados extraídos

```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.ldo_models import *
from app.models.dashboard_models import ExercicioOrcamentario

db = SessionLocal()

# Buscar exercícios LDO
exercicios = db.query(ExercicioOrcamentario).filter(
    ExercicioOrcamentario.tipo_documento == 'LDO'
).all()

print('\\n📋 EXERCÍCIOS LDO PROCESSADOS:')
print('=' * 60)

for ex in exercicios:
    print(f'\\nAno: {ex.ano} | Município: {ex.municipio}')
    print(f'Prefeito: {ex.prefeito or \"N/D\"}')
    print(f'Processado em: {ex.processado_em}')
    
    # Verificar tabelas relacionadas
    metas_prioridades = db.query(MetasPrioridadesLDO).filter(
        MetasPrioridadesLDO.exercicio_id == ex.id
    ).first()
    
    metas_fiscais = db.query(MetasFiscaisLDO).filter(
        MetasFiscaisLDO.exercicio_id == ex.id
    ).first()
    
    riscos_fiscais = db.query(RiscosFiscaisLDO).filter(
        RiscosFiscaisLDO.exercicio_id == ex.id
    ).first()
    
    print('\\nDados extraídos:')
    print(f'  Metas e Prioridades: {\"✅\" if metas_prioridades else \"❌\"}')
    if metas_prioridades and metas_prioridades.prioridades:
        print(f'    → {len(metas_prioridades.prioridades)} prioridades')
    
    print(f'  Metas Fiscais: {\"✅\" if metas_fiscais else \"❌\"}')
    if metas_fiscais and metas_fiscais.resultado_primario_meta:
        print(f'    → Resultado Primário: R$ {metas_fiscais.resultado_primario_meta:,.2f}')
    
    print(f'  Riscos Fiscais: {\"✅\" if riscos_fiscais else \"❌\"}')
    if riscos_fiscais and riscos_fiscais.riscos:
        print(f'    → {len(riscos_fiscais.riscos)} riscos identificados')
        print(f'    → Avaliação geral: {riscos_fiscais.avaliacao_geral_risco or \"N/D\"}')

db.close()
"
```

---

### 4. Testar API

```bash
# Listar exercícios LDO
curl http://localhost:4001/api/ldo/exercicios | jq

# Obter metas e prioridades de 2025
curl http://localhost:4001/api/ldo/metas-prioridades/2025 | jq '.prioridades'

# Obter metas fiscais de 2025
curl http://localhost:4001/api/ldo/metas-fiscais/2025 | jq '.resultado_primario'

# Obter riscos fiscais de 2025
curl http://localhost:4001/api/ldo/riscos-fiscais/2025 | jq '.riscos | length'
```

---

### 5. Testar Frontend

1. Abra o navegador: http://localhost:4000
2. Clique no menu **"LDO"** (novo item com ícone de alvo)
3. Selecione o ano **2025**
4. Navegue pelas 3 abas:
   - **Metas e Prioridades**: Veja as prioridades governamentais
   - **Metas Fiscais**: Veja os gráficos de evolução fiscal
   - **Riscos Fiscais**: Veja os riscos identificados

**✅ Checklist visual:**
- [ ] Aba "Metas e Prioridades" carrega dados
- [ ] Prioridades estão ordenadas por número
- [ ] Badges de setores têm cores diferentes
- [ ] Gráficos de Metas Fiscais são renderizados
- [ ] Cards mostram valores formatados (R$ XXM ou R$ XXB)
- [ ] Riscos Fiscais mostram badges coloridos por nível
- [ ] Gráfico de pizza mostra distribuição de riscos

---

## 🐛 Troubleshooting

### Erro: "LDO não encontrada"

**Solução:**
```bash
# Verificar se existe documento LDO no banco
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.document import Document

db = SessionLocal()
docs = db.query(Document).all()

print('Documentos no banco:')
for doc in docs:
    print(f'  - {doc.filename} (Tipo: {doc.type})')
"
```

### Erro: "Gemini API timeout"

**Possíveis causas:**
1. PDF muito grande (>150 páginas)
2. Conexão lenta com API do Google
3. API do Gemini indisponível

**Soluções:**
- Aumentar timeout em `extract_ldo_from_pdf()` (linha: `request_options={"timeout": 900}`)
- Reduzir `max_chars` para amostragem mais agressiva
- Verificar se a chave API do Gemini está configurada: `echo $GEMINI_API_KEY`

### Erro: "Frontend não carrega dados"

**Verificar:**
```bash
# Backend está rodando?
curl http://localhost:4001/health

# API retorna dados?
curl http://localhost:4001/api/ldo/exercicios

# Frontend está rodando?
curl http://localhost:4000
```

### Erro: "TypeError: Cannot read property 'prioridades'"

**Causa:** Dados LDO não foram processados corretamente.

**Solução:**
1. Verificar logs do processamento: `docker-compose logs backend`
2. Reprocessar o documento
3. Verificar se o JSON retornado pelo Gemini está correto

---

## 📊 Verificação de Qualidade dos Dados

### Script de Análise Completa

```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.ldo_models import *
from app.models.dashboard_models import ExercicioOrcamentario
import json

db = SessionLocal()

exercicio = db.query(ExercicioOrcamentario).filter(
    ExercicioOrcamentario.tipo_documento == 'LDO',
    ExercicioOrcamentario.ano == 2025
).first()

if not exercicio:
    print('❌ LDO 2025 não encontrada')
    exit(1)

print('\\n' + '=' * 70)
print('ANÁLISE DE QUALIDADE DOS DADOS - LDO 2025')
print('=' * 70)

# 1. Metas e Prioridades
metas_prioridades = db.query(MetasPrioridadesLDO).filter(
    MetasPrioridadesLDO.exercicio_id == exercicio.id
).first()

if metas_prioridades:
    print('\\n✅ METAS E PRIORIDADES')
    print(f'  Prioridades: {len(metas_prioridades.prioridades or [])}')
    print(f'  Diretrizes Gerais: {len(metas_prioridades.diretrizes_gerais or [])}')
    print(f'  Metas Setoriais: {len(metas_prioridades.metas_setoriais or {})} setores')
    print(f'  Programas Prioritários: {len(metas_prioridades.programas_prioritarios or [])}')
    
    if metas_prioridades.prioridades:
        print('\\n  Top 3 Prioridades:')
        for p in metas_prioridades.prioridades[:3]:
            print(f'    {p[\"ordem\"]}. [{p[\"setor\"]}] {p[\"titulo\"]}')

# 2. Metas Fiscais
metas_fiscais = db.query(MetasFiscaisLDO).filter(
    MetasFiscaisLDO.exercicio_id == exercicio.id
).first()

if metas_fiscais:
    print('\\n✅ METAS FISCAIS (ANEXO OBRIGATÓRIO LRF)')
    print(f'  Resultado Primário Meta: R$ {float(metas_fiscais.resultado_primario_meta or 0):,.2f}')
    print(f'  Resultado Nominal Meta: R$ {float(metas_fiscais.resultado_nominal_meta or 0):,.2f}')
    print(f'  Dívida Consolidada: R$ {float(metas_fiscais.divida_consolidada_meta or 0):,.2f}')
    print(f'  RCL Prevista: R$ {float(metas_fiscais.rcl_prevista or 0):,.2f}')
    
    if metas_fiscais.projecoes_trienio:
        print(f'  Projeções Trienio: {len(metas_fiscais.projecoes_trienio)} anos')
    
    if metas_fiscais.premissas_macroeconomicas:
        print(f'  Premissas Macro: {len(metas_fiscais.premissas_macroeconomicas)} indicadores')

# 3. Riscos Fiscais
riscos_fiscais = db.query(RiscosFiscaisLDO).filter(
    RiscosFiscaisLDO.exercicio_id == exercicio.id
).first()

if riscos_fiscais:
    print('\\n✅ RISCOS FISCAIS (ANEXO OBRIGATÓRIO LRF)')
    print(f'  Riscos Identificados: {len(riscos_fiscais.riscos or [])}')
    print(f'  Avaliação Geral: {riscos_fiscais.avaliacao_geral_risco or \"N/D\"}')
    print(f'  Exposição Total: R$ {float(riscos_fiscais.total_exposicao_risco or 0):,.2f}')
    print(f'  Passivos Contingentes: R$ {float(riscos_fiscais.passivos_contingentes_total or 0):,.2f}')
    
    if riscos_fiscais.riscos:
        print('\\n  Riscos por Categoria:')
        categorias = {}
        for r in riscos_fiscais.riscos:
            cat = r['categoria']
            categorias[cat] = categorias.get(cat, 0) + 1
        for cat, count in categorias.items():
            print(f'    {cat}: {count} riscos')

print('\\n' + '=' * 70)
print('FIM DA ANÁLISE')
print('=' * 70)

db.close()
"
```

---

## ✅ Checklist Final

- [ ] Tabelas LDO criadas no banco
- [ ] LDO_2025.pdf processada com sucesso
- [ ] Dados de metas e prioridades salvos
- [ ] Dados de metas fiscais salvos
- [ ] Dados de riscos fiscais salvos
- [ ] API `/ldo/exercicios` retorna dados
- [ ] API `/ldo/metas-prioridades/2025` retorna dados
- [ ] API `/ldo/metas-fiscais/2025` retorna dados
- [ ] API `/ldo/riscos-fiscais/2025` retorna dados
- [ ] Frontend mostra menu "LDO"
- [ ] Aba "Metas e Prioridades" renderiza
- [ ] Aba "Metas Fiscais" renderiza com gráficos
- [ ] Aba "Riscos Fiscais" renderiza com gráfico de pizza

---

**Tudo funcionando? Parabéns! 🎉**

O sistema está pronto para processar LDOs de qualquer município brasileiro!

