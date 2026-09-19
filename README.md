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
- expor contrato HTTP local/provider-neutral;
- validar smoke HTTP contra o runtime selecionado;
- manter evidência de roteamento e rollback/restart antes de promoção.

## Estado de runtime

Fly.io não é mais a rota ativa deste projeto.

A rota atual segue a regra operacional `runtime-routing`: avaliar e reaproveitar PC24x7/local primeiro. Provedor externo só deve ser usado quando houver decisão explícita por requisito objetivo de SLA, segurança, continuidade ou regulação.

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
  -> Runtime Routing Contract
  -> Runtime Smoke Monitor
```

## O que este projeto não faz

- Não faz merge ou push automático.
- Não altera produção fora de workflow governado.
- Não aplica patch sem aprovação.
- Não lê arquivos sensíveis.
- Não depende do build do projeto consumidor.
- Não usa LLM ou banco vetorial por padrão.
- Não publica URL pública sem CI verde e smoke test.
- Não cria ou altera registros DNS automaticamente.
- Não registra segredos em código, logs ou artifacts.
- Não usa Fly.io como rota ativa.

## Estrutura

```text
extension/
agent/
runtime/
tools/
examples/reqsys.config.json
docs/
.github/workflows/
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

### Contrato de roteamento do runtime

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-public \
  --environment dev \
  --provider pc24x7 \
  --base-url http://localhost:8080
```

Os parâmetros antigos `--app-name` e `--duckdns-hostname` continuam aceitos apenas para compatibilidade e retornam `status=attention`, pois Fly.io/DuckDNS não são rota ativa.

### Contrato do smoke monitor

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-monitor \
  --environment dev \
  --base-url http://localhost:8080
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

## Variáveis do runtime ativo

Variáveis não sensíveis:

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_RUNTIME_PROVIDER
REQSYS_PUBLIC_BASE_URL
```

Não há secret Fly.io obrigatório para a rota ativa.

## Workflows de runtime

| Workflow | Arquivo | Função |
|---|---|---|
| CI | `.github/workflows/ci.yml` | testes Python, health e compilação TypeScript |
| Runtime Deploy Readiness | `.github/workflows/runtime-deploy.yml` | readiness por ambiente e artifact |
| Runtime Container Artifact | `.github/workflows/runtime-artifact.yml` | build/inspeção do container e artifact |
| Runtime Smoke Monitor | `.github/workflows/flyio-smoke-monitor.yml` | smoke HTTP provider-neutral contra runtime selecionado |
| Legacy Fly.io Public Deploy | `.github/workflows/flyio-deploy.yml` | rota legada arquivada; não executa deploy |
| Fly.io Rollback Readiness | `.github/workflows/flyio-rollback-readiness.yml` | legado; valida runbook histórico |

## Runtime Smoke Monitor

Em pull request, o workflow executa testes e valida o contrato local do monitor.

Em `workflow_dispatch`, ele:

1. valida ambiente e URL base;
2. emite contrato de monitoramento;
3. executa smoke HTTP contra `/health`, `/ready`, `/runtime-deploy`, `/runtime-artifact` e `/runtime-public`;
4. publica artifact de evidência.

O workflow não faz deploy, rollback, alteração de DNS ou alteração de segredos.

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

- `docs/RUNTIME_ROUTING_CURRENT.md` — rota atual e decisão de não usar Fly.io;
- `docs/RUNTIME_PUBLIC_DEPLOY.md` — histórico consolidado da frente;
- `docs/FLYIO_PUBLIC_DEPLOY.md` — legado Fly.io + DuckDNS;
- `docs/FLYIO_SMOKE_MONITOR.md` — legado smoke público Fly.io;
- `docs/FLYIO_ROLLBACK_RUNBOOK.md` — legado rollback operacional;
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
| 0.7 | Deploy público controlado + smoke HTTP | Recalibrado para runtime não Fly.io |
| 0.7.1 | Roteamento ativo PC24x7/non-Fly | Implementado neste incremento |
| 0.8 | LlamaIndex/Ollama opcional | Futuro |
| 0.9 | Sugestão de patch assistida | Futuro |
