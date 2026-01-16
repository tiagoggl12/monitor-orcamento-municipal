# ====================================
# Monitor de Orçamento Público Municipal
# Makefile - Comandos úteis
# ====================================

.PHONY: help up down restart logs build clean dev dev-build dev-logs prod

# Mostrar ajuda
help:
	@echo "Comandos disponíveis:"
	@echo "  make dev          - Iniciar ambiente de DESENVOLVIMENTO (com hot reload)"
	@echo "  make dev-build    - Rebuild ambiente de desenvolvimento"
	@echo "  make dev-logs     - Ver logs do ambiente de desenvolvimento"
	@echo "  make prod         - Iniciar ambiente de PRODUÇÃO (build otimizado)"
	@echo "  make up           - Alias para 'make prod'"
	@echo "  make down         - Parar todos os containers"
	@echo "  make restart      - Reiniciar todos os containers"
	@echo "  make logs         - Ver logs de todos os containers"
	@echo "  make build        - Rebuild de todos os containers (produção)"
	@echo "  make clean        - Remover containers, volumes e imagens"
	@echo "  make backup-db    - Fazer backup do banco SQLite"
	@echo "  make restore-db   - Restaurar banco SQLite do backup"

# ====================================
# DESENVOLVIMENTO (Hot Reload)
# ====================================
dev:
	@echo "🚀 Iniciando ambiente de DESENVOLVIMENTO (Hot Reload)..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-build:
	@echo "🔨 Rebuilding frontend dev..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-logs:
	@echo "📋 Logs do ambiente de desenvolvimento:"
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

dev-down:
	@echo "🛑 Parando ambiente de desenvolvimento..."
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# ====================================
# PRODUÇÃO (Build Otimizado)
# ====================================
prod:
	@echo "🚀 Iniciando ambiente de PRODUÇÃO..."
	docker compose up -d

up: prod

build:
	@echo "🔨 Rebuilding ambiente de produção..."
	docker compose build --no-cache
	docker compose up -d

# ====================================
# GERAL
# ====================================
down:
	@echo "🛑 Parando todos os containers..."
	docker compose down

restart:
	@echo "🔄 Reiniciando containers..."
	docker compose restart

logs:
	@echo "📋 Logs dos containers:"
	docker compose logs -f

clean:
	@echo "🧹 Limpando containers, volumes e imagens..."
	docker compose down -v --rmi all
	@echo "✅ Limpeza concluída!"

# ====================================
# BACKUP / RESTORE DO BANCO
# ====================================
backup-db:
	@echo "💾 Criando backup do banco..."
	mkdir -p backup
	docker compose exec -T backend sh -lc 'cp /app/data/app.db /tmp/app.db'
	docker compose cp backend:/tmp/app.db ./backup/app.db
	@echo "✅ Backup salvo em ./backup/app.db"

restore-db:
	@echo "♻️  Restaurando banco do backup..."
	docker compose exec -T backend sh -lc 'cp /app/backup/app.db /app/data/app.db'
	@echo "✅ Banco restaurado"

# ====================================
# TESTES
# ====================================
test-api:
	@echo "🧪 Testando API..."
	./test-api.sh

test-upload:
	@echo "📤 Testando upload..."
	./test-upload.sh

test-chat:
	@echo "💬 Testando chat..."
	./test-chat.sh

test-portal:
	@echo "🌐 Testando portal..."
	./test-portal.sh
