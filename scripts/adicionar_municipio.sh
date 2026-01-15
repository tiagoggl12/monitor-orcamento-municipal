#!/bin/bash

# ====================================
# Script para adicionar municípios
# ====================================

echo "🏙️  Adicionar Município"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Solicitar dados
read -p "Nome do Município: " NAME
read -p "Estado (sigla, ex: CE): " STATE
read -p "Ano: " YEAR
read -p "População (opcional, Enter para pular): " POPULATION
read -p "Código IBGE (opcional, Enter para pular): " IBGE_CODE

echo ""
echo "📝 Criando município..."
echo ""

# Construir JSON
JSON_DATA="{\"name\": \"$NAME\", \"state\": \"$STATE\", \"year\": $YEAR"

if [ ! -z "$POPULATION" ]; then
    JSON_DATA="$JSON_DATA, \"population\": $POPULATION"
fi

if [ ! -z "$IBGE_CODE" ]; then
    JSON_DATA="$JSON_DATA, \"ibge_code\": \"$IBGE_CODE\""
fi

JSON_DATA="$JSON_DATA}"

# Fazer request
RESPONSE=$(curl -s -X POST http://localhost:4001/api/municipalities/ \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA")

# Verificar resposta
if echo "$RESPONSE" | grep -q '"id"'; then
    echo "✅ Município criado com sucesso!"
    echo ""
    echo "$RESPONSE" | python3 -m json.tool
else
    echo "❌ Erro ao criar município:"
    echo "$RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

