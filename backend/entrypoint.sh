#!/usr/bin/env sh
set -e

DB_PATH="/app/data/app.db"
BACKUP_DB="/app/backup/app.db"

# Função para verificar se o banco tem dados
has_data() {
  python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('$DB_PATH')
    cursor = conn.cursor()
    # Verificar se há dados em tabelas principais
    tables_to_check = ['municipalities', 'documents', 'exercicio_orcamentario']
    for table in tables_to_check:
        try:
            count = cursor.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            if count > 0:
                conn.close()
                sys.exit(0)  # Tem dados
        except:
            pass
    conn.close()
    sys.exit(1)  # Não tem dados
except:
    sys.exit(1)  # Erro ou banco não existe
" 2>/dev/null
}

# Verificar se precisa restaurar
if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ] || ! has_data; then
  if [ -f "$BACKUP_DB" ] && [ -s "$BACKUP_DB" ]; then
    echo "✅ Restaurando banco de dados a partir do backup..."
    cp "$BACKUP_DB" "$DB_PATH"
    echo "✅ Banco restaurado com sucesso!"
  else
    if [ ! -f "$DB_PATH" ] || [ ! -s "$DB_PATH" ]; then
      echo "⚠️ Backup não encontrado em $BACKUP_DB. Iniciando com banco vazio."
    else
      echo "⚠️ Banco existe mas está vazio. Backup não encontrado em $BACKUP_DB."
    fi
  fi
else
  echo "✅ Banco de dados já possui dados. Pulando restauração."
fi

exec "$@"

