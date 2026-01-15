#!/bin/bash

# ====================================
# Script de Teste - Portal da Transparência
# ====================================
# Este script testa a integração com o Portal da Transparência de Fortaleza
# e o sistema de cache com Redis.

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URL base da API
BASE_URL="http://localhost:4001/api"

# Função para imprimir mensagens coloridas
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Função para fazer requisições e exibir resultado
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    print_step "$description"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        print_success "Status: $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        return 0
    else
        print_error "Status: $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        return 1
    fi
}

# ====================================
# INÍCIO DOS TESTES
# ====================================

echo ""
echo "======================================"
echo "  TESTES - PORTAL DA TRANSPARÊNCIA"
echo "======================================"
echo ""

# Verificar se jq está instalado
if ! command -v jq &> /dev/null; then
    print_warning "jq não está instalado. Instale para melhor formatação do JSON."
    print_warning "macOS: brew install jq"
    print_warning "Ubuntu: sudo apt-get install jq"
    echo ""
fi

# ====================================
# 1. Health Checks
# ====================================

echo "======================================"
echo "1. HEALTH CHECKS"
echo "======================================"
echo ""

make_request "GET" "/health" "" "Verificando saúde geral da API"

make_request "GET" "/portal/health" "" "Verificando conexão com Portal da Transparência"

make_request "GET" "/portal/cache/health" "" "Verificando conexão com Redis (Cache)"

# ====================================
# 2. Listagem de Packages
# ====================================

echo "======================================"
echo "2. LISTAGEM DE PACKAGES"
echo "======================================"
echo ""

make_request "GET" "/portal/packages" "" "Listando todos os packages disponíveis"

# Salvar alguns packages para testes posteriores
print_step "Salvando lista de packages para testes..."
packages_response=$(curl -s "$BASE_URL/portal/packages")
package_ids=($(echo "$packages_response" | jq -r '.packages[:5][]' 2>/dev/null || echo ""))

if [ ${#package_ids[@]} -gt 0 ]; then
    print_success "Encontrados ${#package_ids[@]} packages para teste"
    echo "Packages: ${package_ids[@]}"
    echo ""
else
    print_warning "Nenhum package encontrado. Alguns testes podem falhar."
    echo ""
fi

# ====================================
# 3. Busca de Packages
# ====================================

echo "======================================"
echo "3. BUSCA DE PACKAGES"
echo "======================================"
echo ""

# Busca por "despesas"
search_data='{
  "query": "despesas",
  "rows": 5,
  "start": 0
}'

make_request "POST" "/portal/packages/search" "$search_data" "Buscando packages com termo 'despesas'"

# Busca por "receitas"
search_data='{
  "query": "receitas",
  "rows": 3,
  "start": 0
}'

make_request "POST" "/portal/packages/search" "$search_data" "Buscando packages com termo 'receitas'"

# ====================================
# 4. Detalhes de Package Específico
# ====================================

echo "======================================"
echo "4. DETALHES DE PACKAGE"
echo "======================================"
echo ""

if [ ${#package_ids[@]} -gt 0 ]; then
    test_package_id="${package_ids[0]}"
    
    make_request "GET" "/portal/packages/$test_package_id" "" "Obtendo detalhes completos do package: $test_package_id"
    
    make_request "GET" "/portal/packages/$test_package_id/metadata" "" "Obtendo apenas metadados do package: $test_package_id"
    
    make_request "GET" "/portal/packages/$test_package_id/resources" "" "Obtendo recursos do package: $test_package_id"
else
    print_warning "Pulando testes de detalhes (nenhum package disponível)"
    echo ""
fi

# ====================================
# 5. Packages Recentes
# ====================================

echo "======================================"
echo "5. PACKAGES RECENTES"
echo "======================================"
echo ""

make_request "GET" "/portal/packages/recent?rows=5" "" "Obtendo 5 packages mais recentes"

# ====================================
# 6. Busca por Tag
# ====================================

echo "======================================"
echo "6. BUSCA POR TAG"
echo "======================================"
echo ""

tag_search_data='{
  "tag": "despesas",
  "rows": 3
}'

make_request "POST" "/portal/packages/by-tag" "$tag_search_data" "Buscando packages com tag 'despesas'"

# ====================================
# 7. Testes de Cache
# ====================================

echo "======================================"
echo "7. TESTES DE CACHE"
echo "======================================"
echo ""

# Primeira requisição (sem cache)
print_step "Fazendo primeira requisição (sem cache)..."
time1_start=$(date +%s%N)
make_request "GET" "/portal/packages?use_cache=true" "" "Primeira requisição - deve consultar API"
time1_end=$(date +%s%N)
time1=$((($time1_end - $time1_start) / 1000000))
echo "Tempo: ${time1}ms"
echo ""

# Segunda requisição (com cache)
print_step "Fazendo segunda requisição (com cache)..."
time2_start=$(date +%s%N)
make_request "GET" "/portal/packages?use_cache=true" "" "Segunda requisição - deve usar cache"
time2_end=$(date +%s%N)
time2=$((($time2_end - $time2_start) / 1000000))
echo "Tempo: ${time2}ms"
echo ""

if [ $time2 -lt $time1 ]; then
    print_success "Cache funcionando! Segunda requisição foi ${time1}ms vs ${time2}ms"
else
    print_warning "Cache pode não estar funcionando corretamente"
fi
echo ""

# Limpar cache
clear_cache_data='{
  "pattern": "portal:*"
}'

make_request "POST" "/portal/cache/clear" "$clear_cache_data" "Limpando todo o cache do portal"

# ====================================
# 8. Teste de Busca com Cache
# ====================================

echo "======================================"
echo "8. BUSCA COM CACHE"
echo "======================================"
echo ""

search_with_cache='{
  "query": "despesas",
  "rows": 10
}'

print_step "Primeira busca (sem cache)..."
time3_start=$(date +%s%N)
make_request "POST" "/portal/packages/search?use_cache=true" "$search_with_cache" "Buscando 'despesas' - primeira vez"
time3_end=$(date +%s%N)
time3=$((($time3_end - $time3_start) / 1000000))
echo "Tempo: ${time3}ms"
echo ""

print_step "Segunda busca (com cache)..."
time4_start=$(date +%s%N)
make_request "POST" "/portal/packages/search?use_cache=true" "$search_with_cache" "Buscando 'despesas' - segunda vez"
time4_end=$(date +%s%N)
time4=$((($time4_end - $time4_start) / 1000000))
echo "Tempo: ${time4}ms"
echo ""

if [ $time4 -lt $time3 ]; then
    print_success "Cache de busca funcionando! ${time3}ms vs ${time4}ms"
else
    print_warning "Cache de busca pode não estar funcionando corretamente"
fi
echo ""

# ====================================
# RESUMO DOS TESTES
# ====================================

echo ""
echo "======================================"
echo "  RESUMO DOS TESTES"
echo "======================================"
echo ""
print_success "Todos os testes de integração com Portal da Transparência foram executados!"
echo ""
print_step "Próximos passos:"
echo "  1. Verificar logs do backend: make logs-backend"
echo "  2. Verificar logs do Redis: make logs-redis"
echo "  3. Monitorar cache: make redis-shell"
echo "  4. Documentação da API: http://localhost:4001/docs"
echo ""
print_success "Fase 3 - Integração com Portal da Transparência - COMPLETA! ✓"
echo ""

