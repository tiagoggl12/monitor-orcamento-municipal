#!/usr/bin/env sh
set -e

DB_PATH="/app/data/app.db"
BACKUP_DB="/app/backup/app.db"

if [ ! -s "$DB_PATH" ]; then
  if [ -f "$BACKUP_DB" ]; then
    echo "✅ Restaurando banco de dados a partir do backup..."
    cp "$BACKUP_DB" "$DB_PATH"
  else
    echo "⚠️ Backup não encontrado em $BACKUP_DB. Iniciando com banco vazio."
  fi
fi

exec "$@"

