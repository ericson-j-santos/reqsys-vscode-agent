# ReqSys VSCode Agent

Plugin local e enxuto para VS Code, preparado para ser plugado em projetos como `reqsys-v2-enterprise-real` sem acoplar código de ferramenta ao produto principal.

## Objetivo

Fornecer comandos e contratos governados para:

- validar o workspace;
- gerar checklist governado;
- construir índice local de contexto com cache incremental;
- consultar informações do projeto com base em evidência local;
- executar busca semântica leve local sem LLM externo;
- validar readiness e artefato/container do runtime;
- preparar deploy público controlado no Fly.io;
- validar Fly.io e DuckDNS por smoke HTTP;
- manter runbook de rollback testado em CI.

## Arquitetura mínima

```text
VS Code Extension
  -> Python Agent CLI
  -> Workspace Reader Governado
  -> Local Context Index + Incremental Cache
  -> Keyword Search
  -> Lightweight Semantic Search
  -> Runtime Deploy Readiness Contract
  -> Runtime Container Artifact
  -> HTTP Runtime
  -> Fly.io Public Deploy Workflow
  -> Fly.io Smoke Monitor
  -> Fly.io Rollback Readiness
```

## O que este projeto não faz

- Não faz merge ou push automático.
- Não altera produção fora de workflow governado.
- Não aplica patch sem aprovação.
- Não lê arquivos sensíveis.
- Não depende do build do projeto consumidor.
- Não usa LLM ou banco vetorial por padrão.
- Não publica URL pública sem CI verde e smoke test.
- Não cria ou altera registros DuckDNS automaticamente.
- Não registra `FLY_API_TOKEN` em código, logs ou artifacts.
- Não trata rollback de imagem como rollback de banco de dados.

## Estrutura

```text
extension/
agent/
runtime/
tools/
examples/reqsys.config.json
docs/
.github/workflows/
fly.toml
README.md
```

## Instalação local

### Agente

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m reqsys_agent.cli health
```

### Extensão

```bash
cd extension
npm install
npm run compile
```

## Uso local do agente

### Health

```bash
PYTHONPATH=agent python -m reqsys_agent.cli health
```

A versão de runtime HTTP e CLI está sincronizada em `0.7.0`.

### Runtime público / deploy

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy --environment staging
```

### Artefato/container

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact --environment staging
```

### Contrato Fly.io + DuckDNS

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-public \
  --environment dev \
  --app-name reqsys-vscode-agent \
  --duckdns-hostname <hostname>.duckdns.org
```

### Contrato do smoke monitor

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-monitor \
  --environment dev \
  --base-url https://reqsys-vscode-agent.fly.dev \
  --duckdns-url https://<hostname>.duckdns.org
```

### Servidor HTTP local

```bash
PYTHONPATH=agent python -m reqsys_agent.cli serve --host 0.0.0.0 --port 8080
```

Endpoints:

- `/health`;
- `/ready`;
- `/runtime-deploy`;
- `/runtime-artifact`;
- `/runtime-public`.

## Variáveis do runtime Fly.io

Variáveis não sensíveis:

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_FLY_APP_NAME
REQSYS_DUCKDNS_HOSTNAME
```

Os nomes antigos `FLY_APP_NAME` e `DUCKDNS_HOSTNAME` permanecem apenas como fallback de compatibilidade no serviço HTTP. Novos deploys usam os nomes `REQSYS_*`, evitando colisão com variáveis reservadas do Fly.io.

Secret obrigatório para deploy real:

```text
FLY_API_TOKEN
```

## Workflows de runtime

| Workflow | Arquivo | Função |
|---|---|---|
| CI | `.github/workflows/ci.yml` | testes Python, health e compilação TypeScript |
| Runtime Deploy Readiness | `.github/workflows/runtime-deploy.yml` | readiness por ambiente e artifact |
| Runtime Container Artifact | `.github/workflows/runtime-artifact.yml` | build/inspeção do container e artifact |
| Fly.io Public Deploy | `.github/workflows/flyio-deploy.yml` | validação em PR e deploy manual real |
| Fly.io Smoke Monitor | `.github/workflows/flyio-smoke-monitor.yml` | smoke real em `.fly.dev` e DuckDNS |
| Fly.io Rollback Readiness | `.github/workflows/flyio-rollback-readiness.yml` | validação automática do runbook |

### Fly.io Public Deploy

Em pull request, o workflow executa testes, build Docker, container local, smoke HTTP e validação da injeção de metadados.

Em `workflow_dispatch`, ele:

1. exige `FLY_API_TOKEN`;
2. valida ambiente, nome do app e hostname DuckDNS;
3. usa `flyctl 0.4.49` instalado por action fixada em commit SHA;
4. registra as releases anteriores;
5. executa deploy com uma Machine (`--ha=false`) e image label igual ao commit;
6. injeta `REQSYS_RUNTIME_ENVIRONMENT`, `REQSYS_FLY_APP_NAME` e `REQSYS_DUCKDNS_HOSTNAME`;
7. executa smoke HTTP;
8. valida os metadados retornados por `/runtime-public`;
9. publica `flyio-public-deploy-evidence-*`, inclusive em falha.

O deploy real permanece manual e não é executado em pull request.

### Fly.io Smoke Monitor

O workflow manual valida:

- `/health`;
- `/ready`;
- `/runtime-deploy`;
- `/runtime-artifact`;
- `/runtime-public`;
- `/health` via DuckDNS quando informado.

### Rollback

Runbook:

```text
docs/FLYIO_ROLLBACK_RUNBOOK.md
```

Validação local:

```bash
python tools/validate_flyio_rollback_runbook.py
```

O rollback seleciona uma imagem anterior com `flyctl releases --image` e a redeploya com `flyctl deploy --image`. O procedimento exige smoke posterior e artifact de evidência.

## Contexto local

### Inspecionar workspace

```bash
PYTHONPATH=agent python -m reqsys_agent.cli inspect --workspace /caminho/do/projeto
```

### Gerar índice local

```bash
PYTHONPATH=agent python -m reqsys_agent.cli build-index --workspace /caminho/do/projeto
```

Arquivos locais gerados:

```text
.reqsys/index.json
.reqsys/index-state.json
```

### Perguntar por palavra-chave

```bash
PYTHONPATH=agent python -m reqsys_agent.cli ask \
  --workspace /caminho/do/projeto \
  --question "Quais workflows existem?"
```

### Busca semântica leve

```bash
PYTHONPATH=agent python -m reqsys_agent.cli semantic-ask \
  --workspace /caminho/do/projeto \
  --question "controle de qualidade de pipelines"
```

A busca usa TF-IDF + similaridade de cosseno localmente, sem embeddings externos, LLM ou banco vetorial.

## Comandos VS Code

| Comando | Função |
|---|---|
| `ReqSys Agent: Health` | valida o agente local |
| `ReqSys Agent: Inspect Workspace` | mostra configuração e escopo |
| `ReqSys Agent: Governance Checklist` | mostra checklist governado |
| `ReqSys Agent: Build Local Context` | cria índice local incremental |
| `ReqSys Agent: Ask Local Context` | consulta por palavra-chave |
| `ReqSys Agent: Semantic Ask Local Context` | consulta com ranking TF-IDF/cosseno |

## Documentação

- `docs/RUNTIME_PUBLIC_DEPLOY.md` — estado consolidado da frente;
- `docs/FLYIO_PUBLIC_DEPLOY.md` — execução Fly.io + DuckDNS;
- `docs/FLYIO_SMOKE_MONITOR.md` — smoke público;
- `docs/FLYIO_ROLLBACK_RUNBOOK.md` — rollback operacional;
- `docs/INCREMENTAL_INDEX_CACHE.md` — cache incremental.

## Roadmap enxuto

| Fase | Entrega | Estado |
|---|---|---:|
| 0.1 | CLI + extensão + config plugável | Implementado |
| 0.2 | Workspace Reader + Local Context Index | Implementado |
| 0.3 | Busca semântica local leve | Implementado |
| 0.4 | Contrato de runtime público/deploy | Implementado |
| 0.5 | Readiness com artifact | Implementado |
| 0.6 | Artefato/container com evidência | Implementado |
| 0.7 | Deploy público controlado + smoke HTTP | Pipeline implementado; execução real pendente de workflow manual |
| 0.7.1 | Hardening de metadados e rollback | Implementado neste incremento |
| 0.8 | LlamaIndex/Ollama opcional | Futuro |
| 0.9 | Sugestão de patch assistida | Futuro |
