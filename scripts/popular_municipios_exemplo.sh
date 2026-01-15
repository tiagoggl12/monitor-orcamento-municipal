#!/bin/bash

# ====================================
# Script para popular municípios de exemplo
# ====================================

echo "🏙️  Populando municípios de exemplo do Ceará..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Array de municípios do Ceará
declare -a MUNICIPIOS=(
  '{"name": "Fortaleza", "state": "CE", "year": 2025, "population": 2700000, "ibge_code": "2304400"}'
  '{"name": "Caucaia", "state": "CE", "year": 2025, "population": 368918, "ibge_code": "2303709"}'
  '{"name": "Juazeiro do Norte", "state": "CE", "year": 2025, "population": 276264, "ibge_code": "2307304"}'
  '{"name": "Maracanaú", "state": "CE", "year": 2025, "population": 228712, "ibge_code": "2307650"}'
  '{"name": "Sobral", "state": "CE", "year": 2025, "population": 210711, "ibge_code": "2312908"}'
  '{"name": "Crato", "state": "CE", "year": 2025, "population": 133031, "ibge_code": "2304103"}'
  '{"name": "Itapipoca", "state": "CE", "year": 2025, "population": 132179, "ibge_code": "2306405"}'
  '{"name": "Maranguape", "state": "CE", "year": 2025, "population": 131123, "ibge_code": "2307635"}'
  '{"name": "Iguatu", "state": "CE", "year": 2025, "population": 103259, "ibge_code": "2305407"}'
  '{"name": "Quixadá", "state": "CE", "year": 2025, "population": 88402, "ibge_code": "2311603"}'
)

# Contador
SUCCESS=0
FAILED=0

for MUNICIPIO in "${MUNICIPIOS[@]}"; do
    NAME=$(echo "$MUNICIPIO" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
    echo -n "Criando $NAME... "
    
    RESPONSE=$(curl -s -X POST http://localhost:4001/api/municipalities/ \
      -H "Content-Type: application/json" \
      -d "$MUNICIPIO")
    
    if echo "$RESPONSE" | grep -q '"id"'; then
        echo "✅"
        ((SUCCESS++))
    else
        echo "❌ (já existe ou erro)"
        ((FAILED++))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Resultado:"
echo "   ✅ Criados com sucesso: $SUCCESS"
echo "   ❌ Falhas ou duplicados: $FAILED"
echo ""
echo "🔍 Para ver todos os municípios:"
echo "   ./scripts/listar_municipios.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

