# 🗄️ Como Acessar o Banco de Dados SQLite

## 📊 Informações do Banco

- **Tipo:** SQLite
- **Localização:** Volume Docker `monitor_sqlite_data`
- **Arquivo:** `/app/data/app.db` (dentro do container)
- **Localização no host:** Docker gerencia internamente

---

## 🔧 Opção 1: Acessar via Container (Mais Simples)

### 1. Entrar no container do backend:
```bash
docker exec -it monitor_backend /bin/bash
```

### 2. Instalar sqlite3 (se necessário):
```bash
apt-get update && apt-get install -y sqlite3
```

### 3. Abrir o banco:
```bash
sqlite3 /app/data/app.db
```

### 4. Comandos SQLite úteis:
```sql
-- Listar todas as tabelas
.tables

-- Ver estrutura de uma tabela
.schema municipalities

-- Consultar dados
SELECT * FROM municipalities;
SELECT * FROM documents;
SELECT * FROM chat_sessions;

-- Sair
.quit
```

---

## 🖥️ Opção 2: Usar DBeaver (Interface Gráfica)

### 1. Copiar banco do container para o host:
```bash
docker cp monitor_backend:/app/data/app.db /Users/mnq763/Desktop/LOA/app.db
```

### 2. Instalar DBeaver:
- Download: https://dbeaver.io/download/
- É gratuito e suporta SQLite

### 3. Conectar ao banco:
- Abrir DBeaver
- Database → New Database Connection
- Escolher "SQLite"
- Selecionar o arquivo: `/Users/mnq763/Desktop/LOA/app.db`
- Conectar

### 4. Fazer queries visualmente!
- Interface gráfica completa
- Execute queries SQL
- Visualize dados em tabelas
- Exporte para CSV/Excel

---

## 🔍 Opção 3: DB Browser for SQLite (Alternativa ao DBeaver)

### 1. Instalar:
```bash
brew install --cask db-browser-for-sqlite  # macOS
```

Ou baixe em: https://sqlitebrowser.org/

### 2. Copiar banco (se ainda não copiou):
```bash
docker cp monitor_backend:/app/data/app.db /Users/mnq763/Desktop/LOA/app.db
```

### 3. Abrir o arquivo:
- Abrir DB Browser
- File → Open Database
- Selecionar `/Users/mnq763/Desktop/LOA/app.db`

---

## 📋 Opção 4: Via Python (Programático)

Crie um script `query_db.py`:

```python
import sqlite3
import pandas as pd

# Conectar ao banco
conn = sqlite3.connect('/Users/mnq763/Desktop/LOA/app.db')

# Query como DataFrame
df = pd.read_sql_query("SELECT * FROM municipalities", conn)
print(df)

# Query normal
cursor = conn.cursor()
cursor.execute("SELECT * FROM documents")
for row in cursor.fetchall():
    print(row)

conn.close()
```

Execute:
```bash
python3 query_db.py
```

---

## 🔄 Opção 5: API do Backend (Já funcionando!)

Você pode consultar via API sem precisar acessar o banco diretamente:

```bash
# Listar municípios
curl http://localhost:4001/api/municipalities/

# Listar documentos
curl http://localhost:4001/api/documents/

# Ver detalhes de um município
curl http://localhost:4001/api/municipalities/{id}

# Swagger (interface visual)
# Abra no navegador: http://localhost:4001/docs
```

---

## 📊 Estrutura do Banco

### Tabelas criadas:

1. **municipalities** - Municípios cadastrados
   - id (UUID)
   - name (texto)
   - state (texto)
   - year (inteiro)
   - population (inteiro, opcional)
   - ibge_code (texto, opcional)
   - created_at (datetime)

2. **documents** - Documentos LOA/LDO
   - id (UUID)
   - municipality_id (FK)
   - document_type (LOA/LDO)
   - year (inteiro)
   - file_name (texto)
   - file_path (texto)
   - status (pending/processing/processed/failed)
   - uploaded_at (datetime)
   - processed_at (datetime, opcional)

3. **chat_sessions** - Sessões de chat
   - id (UUID)
   - municipality_id (FK, opcional)
   - created_at (datetime)

4. **messages** - Mensagens do chat
   - id (UUID)
   - session_id (FK)
   - role (user/assistant)
   - content (JSON)
   - created_at (datetime)

---

## 🛠️ Comandos Úteis

### Fazer backup do banco:
```bash
docker cp monitor_backend:/app/data/app.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### Restaurar backup:
```bash
docker cp backup_20260105_152000.db monitor_backend:/app/data/app.db
docker-compose restart backend
```

### Ver tamanho do banco:
```bash
docker exec monitor_backend ls -lh /app/data/app.db
```

### Limpar banco (⚠️ CUIDADO):
```bash
docker exec monitor_backend rm /app/data/app.db
docker-compose restart backend
# Banco será recriado vazio
```

---

## 💡 Dicas

### Por que SQLite?
- ✅ Zero configuração
- ✅ Arquivo único e portátil
- ✅ Perfeito para desenvolvimento
- ✅ Sem servidor separado
- ✅ Rápido para milhares de registros

### Quando migrar para PostgreSQL?
- Produção com múltiplos usuários simultâneos
- Necessidade de replicação
- Mais de 100GB de dados
- Queries complexas com JOIN pesados

### Como migrar para PostgreSQL?
1. Alterar `DATABASE_URL` no `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

2. Instalar PostgreSQL no docker-compose

3. Rodar migrations:
   ```bash
   make db-upgrade
   ```

4. Pronto! SQLAlchemy cuida do resto.

---

## 🎯 Recomendação

**Para começar:** Use a **Opção 5 (API + Swagger)** - http://localhost:4001/docs

É visual, não precisa instalar nada e você vê todos os endpoints disponíveis!

**Para análises:** Use **DBeaver** ou **DB Browser** - interfaces gráficas profissionais.

**Para scripts:** Use **Opção 4 (Python)** - automação e análises customizadas.

