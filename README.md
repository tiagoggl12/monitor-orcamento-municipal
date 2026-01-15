# Monitor de Orçamento Público Municipal 🏛️

Sistema inteligente para monitoramento e análise de gastos públicos municipais, utilizando IA (Google Gemini) para cruzar dados da Lei Orçamentária Anual (LOA) e Lei de Diretrizes Orçamentárias (LDO) com informações do Portal da Transparência.

## 🎯 Objetivo

Democratizar o acesso e compreensão dos gastos públicos através de uma interface conversacional que permite consultas em linguagem natural, gerando dashboards, relatórios e análises automáticas.

## ✨ Principais Funcionalidades

- 💬 **Chat Inteligente**: Faça perguntas em linguagem natural sobre o orçamento
- 📊 **Visualizações Automáticas**: Gráficos, tabelas e métricas gerados pela IA
- 🔍 **Cruzamento de Dados**: Compara LOA/LDO com dados executados do Portal
- 📄 **Upload Único**: Envie PDFs uma vez, dados persistem automaticamente
- 🎨 **Respostas Estruturadas**: Componentes visuais dinâmicos (charts, tabelas, alertas)

## 🚀 Quick Start

> **📱 USUÁRIO INICIANTE?** Veja o **[GUIA_RAPIDO.md](GUIA_RAPIDO.md)** ou **[INICIO_RAPIDO.txt](INICIO_RAPIDO.txt)** para instruções passo a passo muito simples!

### Pré-requisitos

- Docker & Docker Compose instalados e **rodando**
- API Key do Google Gemini ([obtenha aqui](https://ai.google.dev/))

### Instalação (Resumo)

```bash
# 1. Navegar até a pasta
cd /Users/mnq763/Desktop/LOA

# 2. Configurar variáveis de ambiente
cp env.example .env
nano .env  # Adicione sua GEMINI_API_KEY

# 3. Primeira execução
make setup  # Configuração inicial (só primeira vez)
make up     # Subir aplicação

# 4. Aguarde ~30 segundos e acesse
# 🌐 Frontend: http://localhost:4000  ← ACESSE AQUI!
# 🔧 Backend API: http://localhost:4001
# 📖 Swagger Docs: http://localhost:4001/docs

# 5. Verificar se funcionou
make health  # Deve mostrar tudo "connected"
```

#### ⚡ Próximas Vezes (Mais Rápido!)

```bash
cd /Users/mnq763/Desktop/LOA
make up
# Aguarde 30 segundos → http://localhost:4000
```

#### 🛑 Parar Aplicação

```bash
make down  # Para mas mantém seus dados
```

### Comandos Disponíveis

```bash
# Gerenciamento de Containers
make setup              # Primeira instalação (cria volumes, networks)
make up                 # Subir sistema completo
make down               # Parar sistema (MANTÉM dados persistidos)
make restart            # Reiniciar serviços
make clean              # Limpar containers (NÃO remove volumes)
make clean-all          # ⚠️ Limpar TUDO incluindo volumes (PERDE DADOS!)

# Logs e Monitoramento
make logs               # Ver logs de todos os serviços
make logs-backend       # Ver apenas logs do backend
make logs-redis         # Ver logs do Redis
make health             # Health check de todos os serviços

# Testes
make test               # Executar testes unitários
make test-api           # Testar API de municípios
make test-upload        # Testar upload de documentos
make test-portal        # Testar integração com Portal da Transparência

# Banco de Dados
make db-migrate         # Rodar migrations do banco
make db-upgrade         # Aplicar migrations
make db-downgrade       # Reverter migrations

# Shell/CLI
make shell-backend      # Abrir shell no container do backend
make shell-redis        # Abrir Redis CLI

# Documentos
make check-documents    # Listar documentos processados
```

## 📋 Configuração

### Variáveis de Ambiente Importantes

Edite o arquivo `.env`:

```bash
# Portas dos serviços
FRONTEND_PORT=4000
BACKEND_PORT=4001
CHROMADB_PORT=8001
REDIS_PORT=6379

# API do Gemini (OBRIGATÓRIO)
GEMINI_API_KEY=sua_api_key_aqui

# Portal da Transparência
PORTAL_BASE_URL=https://dados.fortaleza.ce.gov.br

# CORS (se frontend estiver em outra porta)
CORS_ORIGINS=http://localhost:4000
```

**Nota:** Se você já tem serviços rodando nas portas 3000 ou 8000, as portas padrão (4000 e 4001) evitarão conflitos!

### Alterando Portas

Se precisar usar outras portas, basta editar no `.env`:

```bash
FRONTEND_PORT=5000  # Ao invés de 4000
BACKEND_PORT=5001   # Ao invés de 4001
```

Depois reinicie:
```bash
make restart
```

## 🏗️ Arquitetura

```
Usuário
  ↓
Frontend (React + TypeScript) - localhost:4000
  ↓
Backend (FastAPI + Python) - localhost:4001
  ↓
├─→ ChromaDB (Vetores LOA/LDO) - localhost:8001
├─→ Redis (Cache) - localhost:6379
└─→ Portal Transparência (CKAN API)
```

## 📚 Uso

### Primeiro Acesso

1. **Configure o município:**
   - Selecione: Município, Estado, Ano

2. **Upload de documentos** (apenas primeira vez):
   - Faça upload da LOA (PDF)
   - Faça upload da LDO (PDF)
   - Aguarde processamento (pode levar alguns minutos)

3. **Comece a perguntar:**
   - "Qual foi o orçamento total previsto para 2023?"
   - "Compare saúde e educação"
   - "Identifique maiores desvios orçamentários"

### Acessos Seguintes

- ✅ Documentos já estarão processados
- ✅ Não precisa fazer upload novamente
- ✅ Vá direto para o chat!

### Exemplos de Perguntas

**Básicas:**
- "Qual foi o orçamento total?"
- "Quanto foi destinado para saúde?"
- "Mostre as maiores despesas"

**Comparativas:**
- "Compare previsto vs executado na educação"
- "Quais secretarias gastaram mais?"
- "Execução de obras está dentro do previsto?"

**Analíticas:**
- "Identifique inconsistências entre LOA e execução"
- "Análise de transparência dos dados"
- "Quais projetos tiveram maior desvio?"

## 🛠️ Tecnologias

### Frontend
- React 18 + TypeScript
- Tailwind CSS + shadcn/ui
- Recharts (gráficos)
- TanStack Table (tabelas)
- React Query (cache)
- Vite (build)

### Backend
- FastAPI (Python 3.11+)
- ChromaDB (vector database)
- Google Gemini API
- SQLite/PostgreSQL
- Redis (cache + filas)
- Celery (tarefas assíncronas)
- LangChain (processamento)

## 📦 Estrutura do Projeto

```
monitor-orcamento-municipal/
├── frontend/          # Aplicação React
├── backend/           # API FastAPI
├── docs/             # Documentação
├── docker-compose.yml
├── Makefile
├── env.example
└── README.md
```

## 🔒 Segurança

- ✅ API Keys em variáveis de ambiente
- ✅ `.env` nunca comitado no Git
- ✅ CORS configurável
- ✅ Rate limiting
- ✅ Validação de uploads (formato, tamanho)
- ✅ Sanitização de inputs

## 🐛 Troubleshooting

### Porta já em uso

```bash
# Altere no .env
FRONTEND_PORT=5000
BACKEND_PORT=5001

# Reinicie
make restart
```

### ChromaDB não conecta

```bash
# Verifique logs
make logs-chromadb

# Recrie o container
docker-compose restart chromadb
```

### Redis não conecta

```bash
# Verifique logs
make logs-redis

# Teste conexão
make shell-redis
PING  # Deve retornar: PONG

# Reinicie o serviço
docker-compose restart redis
```

### Portal da Transparência não acessível

```bash
# Verifique health check
curl http://localhost:4001/api/portal/health

# Teste diretamente a API externa
curl https://dados.fortaleza.ce.gov.br/api/3/action/package_list

# Se a API externa estiver fora, o sistema continuará funcionando
# mas as consultas ao portal falharão
```

### Gemini API não funciona

- ✅ Verifique se `GEMINI_API_KEY` está correta no `.env`
- ✅ Teste a key em: https://ai.google.dev/
- ✅ Verifique quota da API

### Dados perdidos após restart

- ✅ Use `make down` ao invés de `docker-compose down -v`
- ✅ Volumes Docker estão persistindo? `docker volume ls`
- ✅ Não use `make clean-all` (remove volumes!)

### Upload de PDF falha

- ✅ Arquivo é PDF válido?
- ✅ Tamanho < 50MB?
- ✅ Verifique logs: `make logs-backend`

## 🧪 Desenvolvimento

### Executar testes

```bash
# Backend
make test

# Frontend
cd frontend && npm test
```

### Hot Reload

O Docker Compose está configurado com volumes para hot reload:
- Frontend: Mudanças refletem automaticamente
- Backend: Mudanças refletem automaticamente (uvicorn --reload)

### Acessar shell dos containers

```bash
make shell-backend   # Shell do Python
make shell-frontend  # Shell do Node
```

### Migrations do Banco

```bash
make db-migrate      # Aplicar migrations
make db-reset        # Resetar banco (DEV only!)
```

## 📊 Status do Projeto

- [x] Fase 0: Setup e Infraestrutura
- [ ] Fase 1: Interface Básica e Upload
- [ ] Fase 2: Ingestão de PDFs
- [ ] Fase 3: Integração com Portal
- [ ] Fase 4: Orquestrador Gemini
- [ ] Fase 5: Chat Completo
- [ ] Fase 6: Dashboards
- [ ] Fase 7: Relatórios
- [ ] Fase 8: Testes
- [ ] Fase 9: Escalabilidade

## 🤝 Contribuindo

Contribuições são bem-vindas! 

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Adiciona nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abra um Pull Request

## 📄 Licença

A definir (sugestão: MIT ou GPL para incentivar reuso)

## 📞 Contato

- **Projeto:** Monitor de Orçamento Público Municipal
- **Documentação Completa:** [PROJETO_MONITOR_ORCAMENTO.md](./PROJETO_MONITOR_ORCAMENTO.md)

## 🙏 Agradecimentos

- Google Gemini pela API de IA
- Portal da Transparência de Fortaleza pelos dados abertos
- Comunidade open-source

---

**Desenvolvido com ❤️ para transparência pública**

*Versão: 1.0.0 | Status: Em desenvolvimento*

