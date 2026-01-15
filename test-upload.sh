#!/bin/bash

# ====================================
# Script de Teste de Upload
# Testa o endpoint de upload de documentos
# ====================================

BASE_URL="http://localhost:4001"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Testando Upload de Documentos${NC}"
echo ""

# ====================================
# 1. Criar município de teste
# ====================================
echo -e "${YELLOW}1. Criando Município de Teste (Fortaleza/CE/2023)${NC}"
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
    echo "Municipality ID: $municipality_id"
else
    echo -e "${RED}❌ Falha ao criar município${NC}"
    exit 1
fi
echo ""

# ====================================
# 2. Criar arquivo PDF de teste
# ====================================
echo -e "${YELLOW}2. Criando PDF de Teste${NC}"

# Criar um PDF simples para teste
cat > test_loa.pdf << 'EOF'
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
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
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
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(LOA 2023 - Teste) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF
EOF

if [ -f "test_loa.pdf" ]; then
    echo -e "${GREEN}✅ PDF de teste criado: test_loa.pdf${NC}"
    ls -lh test_loa.pdf
else
    echo -e "${RED}❌ Falha ao criar PDF de teste${NC}"
    exit 1
fi
echo ""

# ====================================
# 3. Upload do documento LOA
# ====================================
echo -e "${YELLOW}3. Fazendo Upload do Documento LOA${NC}"
response=$(curl -s -w "\n%{http_code}" -X POST $BASE_URL/api/documents/upload \
  -F "file=@test_loa.pdf" \
  -F "municipality_id=$municipality_id" \
  -F "doc_type=LOA")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✅ Upload realizado com sucesso${NC}"
    echo "$body" | python -m json.tool
    document_id=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['document_id'])")
    echo ""
    echo "Document ID: $document_id"
else
    echo -e "${RED}❌ Falha no upload (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# ====================================
# 4. Verificar status do documento
# ====================================
if [ ! -z "$document_id" ]; then
    echo -e "${YELLOW}4. Verificando Status do Documento${NC}"
    sleep 1  # Aguardar um pouco
    
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/documents/$document_id)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Status obtido${NC}"
        echo "$body" | python -m json.tool
        
        status=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['status'])")
        echo ""
        echo "Status atual: $status"
    else
        echo -e "${RED}❌ Falha ao obter status${NC}"
    fi
    echo ""
fi

# ====================================
# 5. Verificar status do município
# ====================================
if [ ! -z "$municipality_id" ]; then
    echo -e "${YELLOW}5. Verificando Status do Município${NC}"
    
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities/$municipality_id/status)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Status do município obtido${NC}"
        echo "$body" | python -m json.tool | head -30
        
        loa_processed=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['loa_processed'])")
        ready=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['ready_for_chat'])")
        
        echo ""
        echo "LOA Processada: $loa_processed"
        echo "Pronto para Chat: $ready"
    else
        echo -e "${RED}❌ Falha ao obter status do município${NC}"
    fi
    echo ""
fi

# ====================================
# 6. Listar todos os documentos
# ====================================
echo -e "${YELLOW}6. Listando Todos os Documentos${NC}"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/documents?municipality_id=$municipality_id")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Documentos listados${NC}"
    count=$(echo "$body" | python -c "import sys, json; print(len(json.load(sys.stdin)))")
    echo "Total de documentos: $count"
    echo "$body" | python -m json.tool | head -40
else
    echo -e "${RED}❌ Falha ao listar documentos${NC}"
fi
echo ""

# ====================================
# Limpeza
# ====================================
echo -e "${YELLOW}7. Limpando Arquivos de Teste${NC}"
if [ -f "test_loa.pdf" ]; then
    rm test_loa.pdf
    echo -e "${GREEN}✅ Arquivo de teste removido${NC}"
fi
echo ""

# ====================================
# Resumo
# ====================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Testes de Upload Concluídos!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Para testar com um PDF real:"
echo "  ${YELLOW}curl -X POST http://localhost:4001/api/documents/upload \\${NC}"
echo "  ${YELLOW}    -F 'file=@/caminho/para/LOA_2023.pdf' \\${NC}"
echo "  ${YELLOW}    -F 'municipality_id=$municipality_id' \\${NC}"
echo "  ${YELLOW}    -F 'doc_type=LOA'${NC}"
echo ""
echo "Documentação completa:"
echo "  ${YELLOW}http://localhost:4001/docs${NC}"
echo ""

