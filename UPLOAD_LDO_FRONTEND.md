# 📤 PROCESSANDO LDO PELO FRONTEND (UPLOAD)

## ✅ SIM! FUNCIONA PERFEITAMENTE!

Acabei de atualizar o endpoint `/dashboard/processar-documento` para **detectar automaticamente** se o arquivo é LOA ou LDO e usar o método de extração correto.

---

## 🎯 COMO FUNCIONA

### Detecção Automática

O sistema detecta o tipo de documento pelo **nome do arquivo**:

```python
# Se o nome contém "LDO" ou "DIRETRIZES"
if 'LDO' in filename_upper or 'DIRETRIZES' in filename_upper:
    # Usa extração específica de LDO
    exercicio = service.extract_ldo_from_pdf(temp_path, db)
else:
    # Usa extração padrão de LOA
    exercicio = service.extract_from_pdf(temp_path, db)
```

### Nomes de Arquivo Reconhecidos como LDO

✅ **LDO_2025.pdf**  
✅ **LDO-2025.pdf**  
✅ **ldo_fortaleza_2025.pdf**  
✅ **Lei_Diretrizes_Orcamentarias_2025.pdf**  
✅ **diretrizes-orcamentarias-2025.pdf**  

❌ **orcamento_2025.pdf** (será processado como LOA)  
❌ **LOA_2025.pdf** (será processado como LOA)  

---

## 📋 PASSO A PASSO PELO FRONTEND

### 1. Acessar a Tela de Upload

1. Abra o navegador: **http://localhost:4000**
2. Clique no menu **"Upload"**
3. Você verá a tela de upload de documentos

### 2. Fazer Upload da LDO

1. Clique em **"Escolher arquivo"** ou arraste o PDF
2. Selecione o arquivo **LDO_2025.pdf**
3. (Opcional) Ajuste o nome do município se necessário
4. Clique em **"Processar Documento"**

### 3. Aguardar Processamento

⏱️ **Tempo estimado:** 3-5 minutos

Durante o processamento você verá:
- ⏳ Indicador de loading
- 📊 "Processando documento..."
- ✅ Mensagem de sucesso ao finalizar

### 4. Visualizar Resultados

Após o processamento:

1. **Navegue para a aba "LDO"** no menu principal
2. **Selecione o ano 2025** no seletor
3. **Explore as 3 abas:**
   - Metas e Prioridades
   - Metas Fiscais  
   - Riscos Fiscais

---

## 🎬 EXEMPLO PRÁTICO

```bash
# 1. Certifique-se que os serviços estão rodando
docker-compose ps

# Resultado esperado:
# backend   Up (healthy)
# frontend  Up
```

**No navegador:**

1. **http://localhost:4000** → Menu "Upload"
2. Arraste **LDO_2025.pdf**
3. Clique **"Processar"**
4. Aguarde 3-5 minutos ⏳
5. ✅ Sucesso! "LDO 2025 processada"
6. Menu "LDO" → Selecionar "2025" → Ver dados!

---

## ⚡ VANTAGENS DO UPLOAD PELO FRONTEND

### ✅ Mais Simples
- Interface visual intuitiva
- Drag & drop de arquivos
- Feedback visual do progresso

### ✅ Mais Seguro
- Validação de formato (apenas PDF)
- Detecção automática LOA vs LDO
- Tratamento de erros com mensagens claras

### ✅ Mais Completo
- Armazena metadados do upload
- Rastreia status de processamento
- Permite reprocessamento se necessário

---

## 🔍 VERIFICAÇÃO DO PROCESSAMENTO

### Via Frontend (Recomendado)

1. Menu **"LDO"**
2. Verifique se **2025** aparece no seletor
3. Navegue pelas abas e confirme os dados

### Via API

```bash
# Verificar se foi processado
curl http://localhost:4001/api/ldo/exercicios | jq

# Deve retornar algo como:
[
  {
    "ano": 2025,
    "municipio": "Fortaleza",
    "prefeito": "Nome do Prefeito",
    "documento_legal": "Lei nº XXX...",
    "processado_em": "2026-01-09T..."
  }
]
```

### Via Banco de Dados

```bash
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.models.dashboard_models import ExercicioOrcamentario

db = SessionLocal()
ldo = db.query(ExercicioOrcamentario).filter(
    ExercicioOrcamentario.tipo_documento == 'LDO',
    ExercicioOrcamentario.ano == 2025
).first()

if ldo:
    print(f'✅ LDO 2025 processada!')
    print(f'   Município: {ldo.municipio}')
    print(f'   Prefeito: {ldo.prefeito}')
else:
    print('❌ LDO 2025 não encontrada')
"
```

---

## 🐛 TROUBLESHOOTING

### Erro: "Apenas arquivos PDF são aceitos"

**Causa:** Arquivo não é PDF ou tem extensão incorreta

**Solução:**
- Certifique-se que o arquivo termina com `.pdf`
- Verifique se não é um arquivo corrompido

### Erro: "Timeout durante processamento"

**Causa:** PDF muito grande ou API do Gemini lenta

**Solução:**
```python
# Aumentar timeout no código (já está em 600s = 10min)
# Se ainda assim timeout, o PDF pode ser muito grande
# Considere dividir ou usar amostragem mais agressiva
```

### Erro: "Não foi possível extrair dados estruturados"

**Causa:** PDF mal formatado, escaneado ou com proteção

**Solução:**
1. Verifique se o PDF permite cópia de texto
2. Se for PDF escaneado, faça OCR primeiro
3. Tente outro PDF da mesma LDO

### Processamento Completo mas Sem Dados

**Causa:** Gemini retornou JSON vazio ou incompleto

**Solução:**
```bash
# Ver logs do processamento
docker-compose logs backend | grep -A 20 "Iniciando extração"

# Reprocessar com mais contexto
# (ajustar max_chars em ldo_extraction_service.py)
```

---

## 📊 COMPARAÇÃO: FRONTEND vs COMANDO

| Aspecto | Frontend Upload | Comando Python |
|---------|----------------|----------------|
| **Simplicidade** | ⭐⭐⭐⭐⭐ Visual e intuitivo | ⭐⭐⭐ Requer terminal |
| **Feedback** | ⭐⭐⭐⭐⭐ Tempo real | ⭐⭐⭐ Apenas logs |
| **Rastreamento** | ⭐⭐⭐⭐⭐ Histórico completo | ⭐⭐ Apenas momento |
| **Erros** | ⭐⭐⭐⭐⭐ Mensagens claras | ⭐⭐⭐ Stack traces |
| **Velocidade** | ⭐⭐⭐⭐ Mesma | ⭐⭐⭐⭐ Mesma |
| **Controle** | ⭐⭐⭐⭐ Parâmetros básicos | ⭐⭐⭐⭐⭐ Controle total |

**Recomendação:** Use o **Frontend** para uso normal, **Comando** para debugging.

---

## 🎯 PRÓXIMOS PASSOS APÓS UPLOAD

1. ✅ **Visualizar no Dashboard LDO**
   - Metas e Prioridades
   - Metas Fiscais com gráficos
   - Riscos Fiscais

2. 🔍 **Comparar com LOA**
   - Menu "Dashboard LOA" → Ano 2025
   - Verificar se as prioridades da LDO estão sendo cumpridas

3. 💬 **Consultar via Chat**
   - Menu "Chat" → "Quais são as 3 principais prioridades da LDO 2025?"
   - "Como está o cumprimento das metas fiscais?"

4. 📊 **Exportar Dados**
   - (Funcionalidade futura) Gerar relatórios comparativos

---

## ✅ RESUMO

**SIM, você pode processar a LDO pelo frontend usando a tela de Upload!**

O sistema:
- ✅ Detecta automaticamente que é LDO (pelo nome do arquivo)
- ✅ Usa o prompt específico de extração de LDO
- ✅ Salva todos os dados nas tabelas corretas
- ✅ Disponibiliza para visualização na aba "LDO"

**É a forma mais simples e recomendada de processar documentos!** 🚀

---

## 🎉 BÔNUS: PROCESSAMENTO EM LOTE

Você pode fazer upload de **múltiplas LDOs** sequencialmente:

1. Upload **LDO_2024.pdf** → Processar
2. Upload **LDO_2025.pdf** → Processar  
3. Upload **LDO_2026.pdf** → Processar

O sistema manterá **histórico completo** de todos os anos!

Depois você pode comparar:
- Evolução das metas fiscais ao longo dos anos
- Mudanças nas prioridades governamentais
- Aumento/diminuição de riscos fiscais

**Agora é só usar!** 🎊

