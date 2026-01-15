#!/bin/bash

# ====================================
# Script para listar municípios
# ====================================

echo "🏙️  Municípios Cadastrados"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

curl -s http://localhost:4001/api/municipalities/ | python3 -m json.tool

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

