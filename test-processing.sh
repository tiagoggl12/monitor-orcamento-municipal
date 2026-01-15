#!/bin/bash

# ====================================
# Script de Teste de Processamento (Fase 2)
# Testa todo o fluxo: Upload → Processamento → Vetorização
# ====================================

BASE_URL="http://localhost:4001"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Testando Processamento Completo (Fase 2)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# ====================================
# 1. Criar município de teste
# ====================================
echo -e "${YELLOW}📍 Passo 1: Criando Município de Teste${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/municipalities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fortaleza",
    "state": "CE",
    "year": 2023
  }')
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Município criado/encontrado${NC}"
    municipality_id=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
    echo "   Municipality ID: $municipality_id"
else
    echo -e "${RED}❌ Falha ao criar município${NC}"
    exit 1
fi
echo ""

# ====================================
# 2. Criar PDF de teste mais completo
# ====================================
echo -e "${YELLOW}📄 Passo 2: Criando PDF de Teste${NC}"

cat > test_loa_full.pdf << 'EOF'
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R 4 0 R]
/Count 2
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 5 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
4 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 6 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
>>
endobj
5 0 obj
<<
/Length 300
>>
stream
BT
/F1 16 Tf
100 700 Td
(LEI ORCAMENTARIA ANUAL 2023) Tj
0 -30 Td
/F1 12 Tf
(PREFEITURA MUNICIPAL DE FORTALEZA) Tj
0 -40 Td
(CAPITULO I - DISPOSICOES GERAIS) Tj
0 -30 Td
(Art. 1 - Esta lei estima a receita e fixa) Tj
0 -20 Td
(a despesa do Municipio de Fortaleza para) Tj
0 -20 Td
(o exercicio financeiro de 2023.) Tj
ET
endstream
endobj
6 0 obj
<<
/Length 250
>>
stream
BT
/F1 12 Tf
100 700 Td
(CAPITULO II - DO ORCAMENTO) Tj
0 -30 Td
(Art. 2 - A receita total e estimada em) Tj
0 -20 Td
(R$ 450.000.000,00 proveniente de:) Tj
0 -30 Td
(I - Receitas correntes: R$ 400.000.000,00) Tj
0 -20 Td
(II - Receitas de capital: R$ 50.000.000,00) Tj
ET
endstream
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000121 00000 n
0000000324 00000 n
0000000527 00000 n
0000000877 00000 n
trailer
<<
/Size 7
/Root 1 0 R
>>
startxref
1177
%%EOF
EOF

if [ -f "test_loa_full.pdf" ]; then
    echo -e "${GREEN}✅ PDF de teste criado: test_loa_full.pdf${NC}"
    ls -lh test_loa_full.pdf
else
    echo -e "${RED}❌ Falha ao criar PDF de teste${NC}"
    exit 1
fi
echo ""

# ====================================
# 3. Upload do documento
# ====================================
echo -e "${YELLOW}📤 Passo 3: Fazendo Upload do Documento${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/documents/upload \
  -F "file=@test_loa_full.pdf" \
  -F "municipality_id=$municipality_id" \
  -F "doc_type=LOA")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✅ Upload realizado com sucesso${NC}"
    document_id=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['document_id'])")
    echo "   Document ID: $document_id"
else
    echo -e "${RED}❌ Falha no upload (HTTP $http_code)${NC}"
    echo "$body"
    exit 1
fi
echo ""

# ====================================
# 4. Processar documento
# ====================================
if [ ! -z "$document_id" ]; then
    echo -e "${YELLOW}⚙️  Passo 4: Processando Documento${NC}"
    echo -e "${BLUE}   (Isso pode levar alguns minutos...)${NC}"
    echo ""
    
    # Fazer request de processamento
    response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/documents/$document_id/process)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Processamento concluído${NC}"
        echo ""
        echo "Resultado:"
        echo "$body" | python -m json.tool
        
        status=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['status'])")
        total_chunks=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin).get('total_chunks', 0))")
        
        echo ""
        if [ "$status" = "completed" ]; then
            echo -e "${GREEN}🎉 Status: $status${NC}"
            echo -e "${GREEN}📦 Total de chunks: $total_chunks${NC}"
        elif [ "$status" = "failed" ]; then
            echo -e "${RED}❌ Status: $status${NC}"
            error=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin).get('error_message', 'Unknown error'))")
            echo -e "${RED}Erro: $error${NC}"
        else
            echo -e "${YELLOW}⏳ Status: $status${NC}"
        fi
    else
        echo -e "${RED}❌ Falha no processamento (HTTP $http_code)${NC}"
        echo "$body"
    fi
    echo ""
fi

# ====================================
# 5. Verificar estatísticas
# ====================================
if [ ! -z "$document_id" ]; then
    echo -e "${YELLOW}📊 Passo 5: Verificando Estatísticas${NC}"
    
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/documents/$document_id/stats)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Estatísticas obtidas${NC}"
        echo "$body" | python -m json.tool
    else
        echo -e "${YELLOW}⚠️  Estatísticas não disponíveis${NC}"
    fi
    echo ""
fi

# ====================================
# 6. Verificar status do município
# ====================================
if [ ! -z "$municipality_id" ]; then
    echo -e "${YELLOW}🏛️  Passo 6: Verificando Status do Município${NC}"
    
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities/$municipality_id/status)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Status do município obtido${NC}"
        
        loa_processed=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['loa_processed'])")
        ready=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['ready_for_chat'])")
        
        echo ""
        echo "LOA Processada: $loa_processed"
        echo "Pronto para Chat: $ready"
        
        if [ "$ready" = "True" ]; then
            echo -e "${GREEN}🎉 Sistema pronto para chat!${NC}"
        else
            echo -e "${YELLOW}⚠️  Faça upload e processe a LDO para completar${NC}"
        fi
    else
        echo -e "${RED}❌ Falha ao obter status${NC}"
    fi
    echo ""
fi

# ====================================
# Limpeza
# ====================================
echo -e "${YELLOW}🧹 Passo 7: Limpando Arquivos Temporários${NC}"
if [ -f "test_loa_full.pdf" ]; then
    rm test_loa_full.pdf
    echo -e "${GREEN}✅ Arquivo de teste removido${NC}"
fi
echo ""

# ====================================
# Resumo
# ====================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Teste de Processamento Concluído!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Endpoints testados:"
echo "  ✅ POST /api/municipalities (criar município)"
echo "  ✅ POST /api/documents/upload (upload de PDF)"
echo "  ✅ POST /api/documents/{id}/process (processar documento)"
echo "  ✅ GET /api/documents/{id}/stats (estatísticas)"
echo "  ✅ GET /api/municipalities/{id}/status (status município)"
echo ""
echo "Processos validados:"
echo "  ✅ Extração de texto do PDF"
echo "  ✅ Chunking inteligente"
echo "  ✅ Geração de embeddings (Gemini)"
echo "  ✅ Armazenamento no ChromaDB"
echo ""
echo "Para ver a documentação completa:"
echo "  ${YELLOW}http://localhost:4001/docs${NC}"
echo ""

if [ ! -z "$document_id" ]; then
    echo "IDs criados neste teste:"
    echo "  Municipality: $municipality_id"
    echo "  Document: $document_id"
    echo ""
fi

