# REQSYS#002 — Runtime Público / Deploy

## Objetivo

Manter uma base executável, auditável e segura para build, deploy, smoke e rollback do runtime público do `reqsys-vscode-agent` no Fly.io, com DuckDNS como hostname externo opcional.

## Estado consolidado

| Item | Estado | Evidência |
|---|---:|---|
| Contrato de deploy | Implementado | comando `runtime-deploy` |
| Contrato de artefato/container | Implementado | comando `runtime-artifact` |
| Contrato Fly.io + DuckDNS | Implementado | comando `runtime-public` |
| Contrato de monitor | Implementado | comando `runtime-monitor` |
| Runtime HTTP | Implementado | `agent/reqsys_agent/http_runtime.py` |
| Versão CLI/runtime | Sincronizada | `0.7.0` |
| Readiness workflow | Implementado | `.github/workflows/runtime-deploy.yml` |
| Container workflow | Implementado | `.github/workflows/runtime-artifact.yml` |
| Fly.io deploy workflow | Implementado | `.github/workflows/flyio-deploy.yml` |
| Smoke monitor | Implementado | `.github/workflows/flyio-smoke-monitor.yml` |
| Rollback runbook | Implementado | `docs/FLYIO_ROLLBACK_RUNBOOK.md` |
| Teste do runbook | Implementado | `.github/workflows/flyio-rollback-readiness.yml` |
| Deploy real `dev` | Pendente | requer `workflow_dispatch` e `FLY_API_TOKEN` |
| URL `.fly.dev` validada | Pendente | requer artifact de deploy real |
| DuckDNS validado | Pendente | requer hostname real e smoke |
| Produção | Bloqueada | requer promoção, smoke e aprovação |

## Ambientes

```text
dev → staging → production
```

Produção só pode ser operada por execução manual explícita e com hostname DuckDNS informado.

## Runtime HTTP

Comando local:

```bash
PYTHONPATH=agent python -m reqsys_agent.cli serve --host 0.0.0.0 --port 8080
```

Endpoints:

- `/health`;
- `/ready`;
- `/runtime-deploy`;
- `/runtime-artifact`;
- `/runtime-public`.

## Variáveis de ambiente

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_FLY_APP_NAME
REQSYS_DUCKDNS_HOSTNAME
```

O serviço mantém fallback para `FLY_APP_NAME` e `DUCKDNS_HOSTNAME`, mas novos deploys usam apenas os nomes `REQSYS_*`.

Secret:

```text
FLY_API_TOKEN
```

## Controles de custo

`fly.toml`:

```toml
auto_stop_machines = "stop"
auto_start_machines = true
min_machines_running = 0
```

Deploy:

```text
--ha=false
```

Não há banco pago ou volume persistente obrigatório neste runtime.

## Supply chain

O Fly CLI está fixado em:

```text
flyctl 0.4.49
superfly/flyctl-actions/setup-flyctl@ed8efb33836e8b2096c7fd3ba1c8afe303ebbff1
```

## Fluxos

### Readiness

`.github/workflows/runtime-deploy.yml`

- testes;
- health;
- contrato por ambiente;
- artifact `runtime-deploy-evidence-*`.

### Container

`.github/workflows/runtime-artifact.yml`

- build Docker;
- usuário não-root;
- health e readiness dentro do container;
- inspeção de imagem;
- artifact `runtime-container-artifact-evidence-*`.

### Deploy Fly.io

`.github/workflows/flyio-deploy.yml`

Em PR:

- testes;
- build local;
- container local;
- smoke HTTP;
- validação de versão e metadados;
- artifact de validação.

Em `workflow_dispatch`:

- valida token e inputs;
- captura releases anteriores;
- implanta com image label igual ao SHA;
- injeta ambiente/app/DuckDNS;
- executa smoke `.fly.dev` e DuckDNS;
- valida payload do runtime;
- captura status e histórico de releases;
- publica artifact mesmo em falha.

### Smoke público

`.github/workflows/flyio-smoke-monitor.yml`

Executa smoke independente após deploy e gera `flyio-smoke-monitor-evidence-*`.

### Rollback readiness

`.github/workflows/flyio-rollback-readiness.yml`

Valida automaticamente se o runbook contém pré-condições, comandos, variáveis, evidências e restrições obrigatórias.

## Gates que bloqueiam produção

- CI ou build falhando;
- `FLY_API_TOKEN` ausente;
- health/readiness sem HTTP 2xx;
- versão diferente de `0.7.0`;
- app ou DuckDNS divergente do payload;
- ausência de artifact;
- rollback não validado;
- Auth, CORS, JWT, secrets, PII ou auditoria fora da política;
- execução fora de `workflow_dispatch`;
- aprovação humana ausente.

## Rollback

O procedimento oficial está em:

```text
docs/FLYIO_ROLLBACK_RUNBOOK.md
```

Resumo:

1. capturar incidente e `correlation_id`;
2. listar releases com `flyctl releases --image`;
3. selecionar imagem anterior com evidência verde;
4. redeployar com `flyctl deploy --image`;
5. executar smoke `.fly.dev` e DuckDNS;
6. publicar evidência e encerrar ou escalar.

Rollback de imagem não reverte banco de dados.

## KPIs

| KPI | Meta |
|---|---:|
| Startup health | 100% antes da promoção |
| Evidence coverage | 100% dos workflows de runtime |
| Container build success | ≥ 95% após estabilização |
| Deploy success rate | ≥ 95% após execuções reais |
| Uptime | ≥ 99,5% após runtime público estável |
| MTTR | ≤ 30 minutos após rollback testado |

## Maturidade evidenciada

| Dimensão | Percentual | Observação |
|---|---:|---|
| Técnico | 92% | Código, container, workflows, metadados e rollback automatizados. |
| Operacional | 68% | Falta execução real do deploy e do smoke externo. |
| Usuário final | 40% | Ainda sem URL pública validada por artifact real. |
| Governança | 92% | Gates, supply chain pinning, artifacts e runbook testado. |
| Produção | 30% | Produção continua bloqueada até promoção real e aprovação. |

## Próximas ações operacionais

1. confirmar `FLY_API_TOKEN` no repositório;
2. executar `Fly.io Public Deploy` com `environment=dev`;
3. validar `flyio-public-deploy-evidence-dev`;
4. confirmar URL `.fly.dev`;
5. informar e validar hostname DuckDNS real;
6. executar `Fly.io Smoke Monitor`;
7. registrar primeira release saudável como rollback candidate.
