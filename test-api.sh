#!/bin/bash

# ====================================
# Script de Teste da API
# Testa os principais endpoints do backend
# ====================================

BASE_URL="http://localhost:4001"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Testando API do Monitor de Orçamento Público${NC}"
echo ""

# ====================================
# 1. Health Check
# ====================================
echo -e "${YELLOW}1. Health Check${NC}"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/health)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Health check OK${NC}"
    echo "$body" | python -m json.tool
else
    echo -e "${RED}❌ Health check failed (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# ====================================
# 2. Root Endpoint
# ====================================
echo -e "${YELLOW}2. Root Endpoint${NC}"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Root endpoint OK${NC}"
    echo "$body" | python -m json.tool
else
    echo -e "${RED}❌ Root endpoint failed (HTTP $http_code)${NC}"
fi
echo ""

# ====================================
# 3. Criar Município
# ====================================
echo -e "${YELLOW}3. Criando Município (Fortaleza/CE/2023)${NC}"
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
    echo "$body" | python -m json.tool
    municipality_id=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
else
    echo -e "${RED}❌ Falha ao criar município (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# ====================================
# 4. Listar Municípios
# ====================================
echo -e "${YELLOW}4. Listando Municípios${NC}"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Municípios listados${NC}"
    count=$(echo "$body" | python -c "import sys, json; print(len(json.load(sys.stdin)))")
    echo "Total de municípios: $count"
    echo "$body" | python -m json.tool
else
    echo -e "${RED}❌ Falha ao listar municípios (HTTP $http_code)${NC}"
fi
echo ""

# ====================================
# 5. Buscar Município por ID
# ====================================
if [ ! -z "$municipality_id" ]; then
    echo -e "${YELLOW}5. Buscando Município por ID${NC}"
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities/$municipality_id)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Município encontrado${NC}"
        echo "$body" | python -m json.tool
    else
        echo -e "${RED}❌ Município não encontrado (HTTP $http_code)${NC}"
    fi
    echo ""
fi

# ====================================
# 6. Verificar Status dos Documentos
# ====================================
if [ ! -z "$municipality_id" ]; then
    echo -e "${YELLOW}6. Verificando Status dos Documentos${NC}"
    response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities/$municipality_id/status)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅ Status obtido${NC}"
        echo "$body" | python -m json.tool
        
        loa_processed=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['loa_processed'])")
        ldo_processed=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['ldo_processed'])")
        ready=$(echo "$body" | python -c "import sys, json; print(json.load(sys.stdin)['ready_for_chat'])")
        
        echo ""
        echo "LOA Processada: $loa_processed"
        echo "LDO Processada: $ldo_processed"
        echo "Pronto para Chat: $ready"
        
        if [ "$ready" = "False" ]; then
            echo -e "${YELLOW}⚠️  Sistema não está pronto para chat. Faça upload dos documentos LOA e LDO.${NC}"
        else
            echo -e "${GREEN}✅ Sistema pronto para chat!${NC}"
        fi
    else
        echo -e "${RED}❌ Falha ao obter status (HTTP $http_code)${NC}"
    fi
    echo ""
fi

# ====================================
# 7. Buscar por Parâmetros
# ====================================
echo -e "${YELLOW}7. Buscando Município por Parâmetros (Fortaleza/CE/2023)${NC}"
response=$(curl -s -w "\n%{http_code}" $BASE_URL/api/municipalities/search/Fortaleza/CE/2023)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Município encontrado por parâmetros${NC}"
    echo "$body" | python -m json.tool | head -20
    echo "..."
else
    echo -e "${RED}❌ Município não encontrado (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# ====================================
# Resumo
# ====================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Testes Concluídos!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Para ver a documentação completa da API:"
echo "  ${YELLOW}http://localhost:4001/docs${NC}"
echo ""
echo "Para testar upload de documentos (quando implementado):"
echo "  ${YELLOW}curl -X POST http://localhost:4001/api/documents/upload \\${NC}"
echo "  ${YELLOW}  -F 'file=@LOA_2023.pdf' \\${NC}"
echo "  ${YELLOW}  -F 'municipality_id=$municipality_id' \\${NC}"
echo "  ${YELLOW}  -F 'type=LOA'${NC}"
echo ""

