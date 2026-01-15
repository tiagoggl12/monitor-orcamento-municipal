# Backend - Monitor de Orçamento Público Municipal

API FastAPI para o sistema de monitoramento de orçamentos públicos.

## 🚀 Executando Localmente (sem Docker)

### Pré-requisitos

- Python 3.11+
- pip

### Setup

```bash
# 1. Criar ambiente virtual
python -m venv venv

# 2. Ativar ambiente virtual
# No Linux/Mac:
source venv/bin/activate
# No Windows:
venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
# Copie o env.example da raiz do projeto e configure

# 5. Executar servidor
python -m app.main
# ou
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Acessar Documentação

- Swagger UI: http://localhost:4001/docs
- ReDoc: http://localhost:4001/redoc
- Health Check: http://localhost:4001/health

## 🏗️ Estrutura do Projeto

```
backend/
├── app/
│   ├── api/                    # Endpoints da API
│   │   ├── routes/
│   │   │   └── municipalities.py  # ✅ Rotas de municípios
│   │   └── dependencies.py     # Dependencies para injeção
│   ├── core/                   # Configurações centrais
│   │   ├── config.py          # ✅ Configurações (lê .env)
│   │   └── database.py        # ✅ Setup SQLAlchemy
│   ├── models/                 # Models do banco (SQLAlchemy)
│   │   ├── municipality.py    # ✅ Model de Município
│   │   ├── document.py        # ✅ Model de Documento
│   │   ├── chat_session.py    # ✅ Model de Sessão de Chat
│   │   └── message.py         # ✅ Model de Mensagem
│   ├── schemas/                # Schemas Pydantic (validação)
│   │   ├── component_schemas.py  # ✅ Schemas de componentes de resposta
│   │   └── request_schemas.py    # ✅ Schemas de request/response
│   ├── services/               # Lógica de negócio
│   │   ├── pdf_ingestion.py   # TODO: Processamento de PDFs
│   │   ├── gemini_orchestrator.py  # TODO: Orquestrador Gemini
│   │   ├── transparency_portal.py  # TODO: Cliente CKAN API
│   │   ├── vector_db.py       # TODO: Cliente ChromaDB
│   │   └── response_builder.py # TODO: Helper para construir respostas
│   ├── tasks/                  # Tarefas Celery (async)
│   │   └── process_document.py # TODO: Processamento assíncrono
│   ├── prompts/                # Templates de prompts para Gemini
│   │   └── gemini_system_prompt.py  # TODO: Prompt engineering
│   └── main.py                 # ✅ Entry point da aplicação
├── data/                       # Dados locais (gitignored)
│   └── uploads/               # PDFs enviados
├── Dockerfile                  # ✅ Container Docker
├── requirements.txt            # ✅ Dependências Python
└── README.md                   # Este arquivo
```

## 📡 API Endpoints Disponíveis

### Health Check

- `GET /health` - Status da aplicação e serviços

### Root

- `GET /` - Informações básicas da API

### Municipalities

- `POST /api/municipalities` - Criar município
- `GET /api/municipalities` - Listar municípios
- `GET /api/municipalities/{id}` - Obter município
- `GET /api/municipalities/{id}/status` - Status dos documentos
- `GET /api/municipalities/search/{name}/{state}/{year}` - Buscar município
- `DELETE /api/municipalities/{id}` - Deletar município

### TODO: Próximos Endpoints

- `POST /api/documents/upload` - Upload de LOA/LDO
- `GET /api/documents/{id}/status` - Status do processamento
- `POST /api/chat` - Enviar mensagem no chat
- `GET /api/chat/sessions/{id}` - Histórico da sessão
- `GET /api/portal/packages` - Listar packages do portal
- `GET /api/portal/package/{id}` - Detalhes do package

## ⚙️ Configuração

Todas as configurações são carregadas do arquivo `.env` na raiz do projeto.

### Variáveis Obrigatórias

```bash
GEMINI_API_KEY=your_api_key_here
```

### Variáveis Importantes

```bash
# Portas
BACKEND_PORT=4001

# Banco de Dados
DATABASE_URL=sqlite:///data/app.db

# ChromaDB
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000

# Portal
PORTAL_BASE_URL=https://dados.fortaleza.ce.gov.br
```

## 🗄️ Banco de Dados

### Modelos Criados

- **Municipality** - Municípios configurados
- **Document** - Documentos (LOA/LDO) com versionamento
- **ChatSession** - Sessões de chat dos usuários
- **Message** - Mensagens do histórico

### Migrations (Alembic)

```bash
# TODO: Configurar Alembic
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 🧪 Testes

```bash
# Executar testes
pytest

# Com coverage
pytest --cov=app --cov-report=html
```

## 📝 Schemas de Response

O sistema utiliza respostas estruturadas em JSON com componentes tipados:

- **text** - Texto em Markdown
- **chart** - Gráficos (bar, line, pie, area)
- **table** - Tabelas estruturadas
- **alert** - Alertas (info, warning, error, success)
- **metric** - Métricas individuais
- **comparison** - Comparações lado a lado
- **timeline** - Linha do tempo

Exemplo:

```json
{
  "session_id": "uuid",
  "timestamp": "2026-01-05T10:30:00Z",
  "response": {
    "components": [
      {
        "type": "text",
        "content": "## Análise",
        "format": "markdown"
      },
      {
        "type": "metric",
        "label": "Total",
        "value": "R$ 450M"
      }
    ],
    "metadata": {
      "sources": ["LOA 2023"],
      "confidence": "high"
    }
  }
}
```

## 🔧 Desenvolvimento

### Adicionar Nova Rota

1. Criar arquivo em `app/api/routes/`
2. Importar em `app/api/routes/__init__.py`
3. Incluir router em `app/main.py`

### Adicionar Novo Model

1. Criar arquivo em `app/models/`
2. Importar em `app/models/__init__.py`
3. Importar em `app/core/database.py` (função `init_db`)

### Adicionar Novo Schema

1. Criar em `app/schemas/`
2. Importar em `app/schemas/__init__.py`

## 📊 Status do Desenvolvimento

- [x] Estrutura básica do projeto
- [x] Configuração com .env
- [x] Models do banco de dados
- [x] Schemas Pydantic
- [x] API de Municipalities
- [x] Health Check
- [ ] API de Documents (upload)
- [ ] Processamento de PDFs
- [ ] Integração com ChromaDB
- [ ] Integração com Gemini
- [ ] API de Chat
- [ ] Integração com Portal da Transparência
- [ ] Celery para tarefas assíncronas
- [ ] Testes automatizados

## 🐛 Debug

### Logs

Os logs são configurados via `LOG_LEVEL` no `.env`:

- DEBUG - Todos os logs
- INFO - Informações gerais (padrão)
- WARNING - Avisos
- ERROR - Apenas erros

### Problemas Comuns

**Erro: GEMINI_API_KEY não configurada**
- Adicione a chave no arquivo `.env` na raiz do projeto

**Erro: Banco de dados não encontrado**
- Certifique-se que o diretório `data/` existe
- O banco será criado automaticamente no startup

**Erro: Módulo não encontrado**
- Verifique se está no ambiente virtual ativado
- Execute `pip install -r requirements.txt`

## 📚 Próximos Passos

1. Implementar upload de documentos
2. Integrar com ChromaDB para vetorização
3. Implementar Gemini Orchestrator
4. Criar cliente do Portal da Transparência
5. Implementar API de Chat
6. Adicionar testes

