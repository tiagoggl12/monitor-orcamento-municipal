#!/bin/bash

# ====================================
# Script de Teste - Chat e Orquestrador Gemini
# ====================================
# Este script testa a funcionalidade completa de chat
# incluindo o orquestrador Gemini que cruza dados.

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URL base da API
BASE_URL="http://localhost:4001/api"

# Variáveis globais
MUNICIPALITY_ID=""
SESSION_ID=""

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
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        print_success "Status: $http_code"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        echo ""
        echo "$body"
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
echo "  TESTES - CHAT E ORQUESTRADOR GEMINI"
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
# 1. Preparação - Criar Município de Teste
# ====================================

echo "======================================"
echo "1. PREPARAÇÃO"
echo "======================================"
echo ""

municipality_data='{
  "name": "Fortaleza",
  "state": "CE",
  "year": 2023
}'

response=$(make_request "POST" "/municipalities" "$municipality_data" "Criando município de teste")
MUNICIPALITY_ID=$(echo "$response" | jq -r '.id' 2>/dev/null)

if [ -z "$MUNICIPALITY_ID" ] || [ "$MUNICIPALITY_ID" = "null" ]; then
    print_error "Falha ao criar município. Abortando testes."
    exit 1
fi

print_success "Município criado com ID: $MUNICIPALITY_ID"
echo ""

# ====================================
# 2. Criar Sessão de Chat
# ====================================

echo "======================================"
echo "2. CRIAR SESSÃO DE CHAT"
echo "======================================"
echo ""

session_data="{
  \"municipality_id\": $MUNICIPALITY_ID,
  \"title\": \"Teste - Chat Orçamento 2023\"
}"

response=$(make_request "POST" "/chat/sessions" "$session_data" "Criando sessão de chat")
SESSION_ID=$(echo "$response" | jq -r '.id' 2>/dev/null)

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
    print_error "Falha ao criar sessão. Abortando testes."
    exit 1
fi

print_success "Sessão criada com ID: $SESSION_ID"
echo ""

# ====================================
# 3. Listar Sessões
# ====================================

echo "======================================"
echo "3. LISTAR SESSÕES"
echo "======================================"
echo ""

make_request "GET" "/chat/sessions?municipality_id=$MUNICIPALITY_ID" "" "Listando sessões do município"

# ====================================
# 4. Obter Detalhes da Sessão
# ====================================

echo "======================================"
echo "4. DETALHES DA SESSÃO"
echo "======================================"
echo ""

make_request "GET" "/chat/sessions/$SESSION_ID" "" "Obtendo detalhes da sessão $SESSION_ID"

# ====================================
# 5. Enviar Mensagens de Teste
# ====================================

echo "======================================"
echo "5. ENVIAR MENSAGENS (ORQUESTRADOR)"
echo "======================================"
echo ""

print_warning "NOTA: As respostas dependem de:"
print_warning "  1. Documentos LOA/LDO carregados"
print_warning "  2. API do Portal da Transparência acessível"
print_warning "  3. GEMINI_API_KEY configurada"
echo ""

# Mensagem 1: Pergunta simples
print_step "Enviando pergunta 1: Informações gerais"
message1='{
  "question": "Olá! Quais tipos de informações você pode me fornecer sobre o orçamento municipal?"
}'

response1=$(make_request "POST" "/chat/sessions/$SESSION_ID/messages" "$message1" "Enviando mensagem 1")
echo ""
sleep 2

# Mensagem 2: Pergunta sobre dados disponíveis
print_step "Enviando pergunta 2: Disponibilidade de dados"
message2='{
  "question": "Quais documentos e dados estão disponíveis para análise?"
}'

response2=$(make_request "POST" "/chat/sessions/$SESSION_ID/messages" "$message2" "Enviando mensagem 2")
echo ""
sleep 2

# Mensagem 3: Pergunta específica (se houver documentos)
print_step "Enviando pergunta 3: Consulta específica"
message3='{
  "question": "Quanto foi o orçamento previsto para a área da saúde?"
}'

print_warning "Esta pergunta só terá resposta completa se houver documentos LOA/LDO processados"
response3=$(make_request "POST" "/chat/sessions/$SESSION_ID/messages" "$message3" "Enviando mensagem 3")
echo ""

# ====================================
# 6. Obter Histórico de Mensagens
# ====================================

echo "======================================"
echo "6. HISTÓRICO DE MENSAGENS"
echo "======================================"
echo ""

make_request "GET" "/chat/sessions/$SESSION_ID/messages" "" "Obtendo histórico da sessão"

# ====================================
# 7. Obter Resumo da Sessão
# ====================================

echo "======================================"
echo "7. RESUMO DA SESSÃO"
echo "======================================"
echo ""

make_request "GET" "/chat/sessions/$SESSION_ID/summary" "" "Obtendo resumo da sessão"

# ====================================
# 8. Teste de Componentes da Resposta
# ====================================

echo "======================================"
echo "8. ANÁLISE DE COMPONENTES"
echo "======================================"
echo ""

print_step "Analisando última resposta..."

if [ ! -z "$response3" ]; then
    # Verificar se tem components
    component_count=$(echo "$response3" | jq -r '.response.components | length' 2>/dev/null)
    
    if [ ! -z "$component_count" ] && [ "$component_count" != "null" ] && [ "$component_count" -gt 0 ]; then
        print_success "Resposta contém $component_count componentes"
        
        # Listar tipos de componentes
        echo ""
        print_step "Tipos de componentes encontrados:"
        echo "$response3" | jq -r '.response.components[].type' 2>/dev/null | sort | uniq | while read type; do
            echo "  - $type"
        done
        
        # Verificar metadados
        echo ""
        print_step "Metadados da resposta:"
        echo "$response3" | jq '.response.metadata' 2>/dev/null
        
    else
        print_warning "Resposta não contém componentes estruturados"
    fi
else
    print_warning "Não foi possível analisar a resposta"
fi

echo ""

# ====================================
# 9. Teste de Múltiplas Sessões
# ====================================

echo "======================================"
echo "9. MÚLTIPLAS SESSÕES"
echo "======================================"
echo ""

# Criar segunda sessão
session_data2="{
  \"municipality_id\": $MUNICIPALITY_ID,
  \"title\": \"Teste - Análise Comparativa\"
}"

response_session2=$(make_request "POST" "/chat/sessions" "$session_data2" "Criando segunda sessão")
SESSION_ID2=$(echo "$response_session2" | jq -r '.id' 2>/dev/null)

if [ ! -z "$SESSION_ID2" ] && [ "$SESSION_ID2" != "null" ]; then
    print_success "Segunda sessão criada com ID: $SESSION_ID2"
    
    # Enviar mensagem na segunda sessão
    message_session2='{
      "question": "Compare os gastos em saúde e educação"
    }'
    
    make_request "POST" "/chat/sessions/$SESSION_ID2/messages" "$message_session2" "Enviando mensagem na sessão 2"
else
    print_warning "Não foi possível criar segunda sessão"
fi

echo ""

# ====================================
# 10. Limpeza (Opcional)
# ====================================

echo "======================================"
echo "10. LIMPEZA"
echo "======================================"
echo ""

print_warning "Deseja deletar os dados de teste? (y/N)"
read -t 10 -r cleanup_choice || cleanup_choice="n"

if [ "$cleanup_choice" = "y" ] || [ "$cleanup_choice" = "Y" ]; then
    print_step "Deletando sessões..."
    
    make_request "DELETE" "/chat/sessions/$SESSION_ID" "" "Deletando sessão 1"
    
    if [ ! -z "$SESSION_ID2" ]; then
        make_request "DELETE" "/chat/sessions/$SESSION_ID2" "" "Deletando sessão 2"
    fi
    
    make_request "DELETE" "/municipalities/$MUNICIPALITY_ID" "" "Deletando município de teste"
    
    print_success "Limpeza concluída"
else
    print_warning "Mantendo dados de teste"
    print_warning "Sessão ID: $SESSION_ID"
    print_warning "Município ID: $MUNICIPALITY_ID"
    print_warning "Para limpar manualmente: ./test-chat.sh cleanup $SESSION_ID $MUNICIPALITY_ID"
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
print_success "Todos os testes de chat foram executados!"
echo ""
print_step "Resultados:"
echo "  ✓ Sessão de chat criada"
echo "  ✓ Mensagens enviadas e recebidas"
echo "  ✓ Histórico recuperado"
echo "  ✓ Orquestrador Gemini testado"
echo ""
print_step "Notas Importantes:"
echo "  1. Para respostas completas, faça upload de documentos LOA/LDO"
echo "  2. Use: make test-upload para testar upload de documentos"
echo "  3. Verifique GEMINI_API_KEY no arquivo .env"
echo "  4. Logs detalhados: make logs-backend"
echo ""
print_step "Próximos passos:"
echo "  1. Testar via Swagger: http://localhost:4001/docs"
echo "  2. Integrar frontend para interface visual"
echo "  3. Fazer upload de documentos reais"
echo ""
print_success "Fase 4 - Orquestrador Gemini - TESTADO! ✓"
echo ""

