# REQSYS#002.P3/P5 — Fly.io + DuckDNS Public Deploy

## Decisão

A frente de runtime público usa **Fly.io** como alvo oficial e mantém **DuckDNS** como hostname externo.

## Estado evidenciado

| Item | Estado |
|---|---:|
| Runtime HTTP | Implementado |
| Container não-root | Implementado |
| `fly.toml` | Implementado |
| Workflow de deploy | Implementado |
| Smoke local em PR | Implementado |
| Injeção de metadados do runtime | Implementada e validada em PR |
| Smoke público pós-deploy | Implementado no workflow manual |
| Runbook de rollback | Implementado e validado em CI |
| Deploy real em `dev` | Pendente de execução `workflow_dispatch` com token válido |
| DuckDNS real | Pendente de hostname e smoke evidenciado |
| Produção | Bloqueada |

## Arquivos

| Arquivo | Função |
|---|---|
| `fly.toml` | Build, região, HTTP service e controles de custo. |
| `.github/workflows/flyio-deploy.yml` | Validação em PR e deploy manual. |
| `.github/workflows/flyio-smoke-monitor.yml` | Smoke público reutilizável. |
| `.github/workflows/flyio-rollback-readiness.yml` | Teste do runbook. |
| `runtime/Dockerfile.agent` | Container HTTP não-root. |
| `agent/reqsys_agent/http_runtime.py` | Endpoints públicos e metadados. |
| `docs/FLYIO_ROLLBACK_RUNBOOK.md` | Procedimento de recuperação. |

## Endpoints

| Endpoint | Uso |
|---|---|
| `/health` | Liveness e versão. |
| `/ready` | Readiness por ambiente. |
| `/runtime-deploy` | Contrato de promoção/gates. |
| `/runtime-artifact` | Contrato do container. |
| `/runtime-public` | Metadados Fly.io + DuckDNS. |

## Versão

CLI e runtime HTTP usam:

```text
0.7.0
```

O workflow bloqueia sucesso se `/health` ou `/runtime-public` retornar versão diferente.

## Variáveis

### Runtime não sensível

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_FLY_APP_NAME
REQSYS_DUCKDNS_HOSTNAME
```

`REQSYS_FLY_APP_NAME` substitui o uso direto de `FLY_APP_NAME`, evitando prefixo reservado pelo provedor. O serviço mantém fallback para os nomes antigos somente por compatibilidade.

### Secret obrigatório

```text
FLY_API_TOKEN
```

O valor não pode ser impresso, persistido ou incluído em artifact.

## Inputs do deploy manual

| Input | Descrição | Default |
|---|---|---|
| `environment` | `dev`, `staging` ou `production` | `dev` |
| `app_name` | Nome do app Fly.io | `reqsys-vscode-agent` |
| `duckdns_hostname` | Hostname `*.duckdns.org`, sem esquema | vazio |

Produção exige hostname DuckDNS explícito.

## Estratégia de custo mínimo

O `fly.toml` mantém:

```toml
auto_stop_machines = "stop"
auto_start_machines = true
min_machines_running = 0
```

O deploy usa:

```text
--ha=false
```

Isso reduz a quantidade inicial de Machines, mas não constitui garantia contratual de custo zero. O incremento não provisiona banco pago nem volume persistente.

## Supply chain do Fly CLI

O setup do Fly CLI está fixado em:

```text
superfly/flyctl-actions/setup-flyctl@ed8efb33836e8b2096c7fd3ba1c8afe303ebbff1
flyctl 0.4.49
```

Isso evita acompanhar automaticamente mudanças da branch `master` da action.

## Validação em pull request

O job `validate-flyio-runtime` executa:

1. testes Python;
2. build Docker;
3. container local na porta 8080;
4. injeção de ambiente, app e DuckDNS de teste;
5. smoke de todos os endpoints;
6. validação JSON da versão e dos metadados;
7. artifact `flyio-runtime-validation-evidence`.

Esse job não acessa Fly.io e não publica runtime.

## Deploy real por workflow_dispatch

O job `deploy-flyio` executa:

1. validação de ambiente, app, DuckDNS e token;
2. testes antes do deploy;
3. captura das releases anteriores;
4. image label igual ao SHA do commit;
5. `flyctl deploy` com estratégia rolling e uma Machine;
6. injeção explícita das variáveis `REQSYS_*`;
7. smoke em `https://<app>.fly.dev`;
8. validação dos metadados retornados;
9. smoke DuckDNS quando informado;
10. captura de status e histórico de releases;
11. artifact `flyio-public-deploy-evidence-*`, inclusive quando ocorrer falha.

## Evidências esperadas

- `runtime-public-contract.json`;
- `releases-before.json`;
- `fly-health.json`;
- `fly-ready.json`;
- `fly-runtime-deploy.json`;
- `fly-runtime-artifact.json`;
- `fly-runtime-public.json`;
- `duckdns-health.json`, quando aplicável;
- `fly-status.txt`;
- `releases-after.json`;
- `summary.md`.

## Gates que bloqueiam produção

- `FLY_API_TOKEN` ausente;
- app ou hostname inválido;
- testes ou build falhando;
- health/readiness sem HTTP 2xx;
- versão diferente de `0.7.0`;
- metadados divergentes;
- DuckDNS falhando quando informado;
- ausência de artifact;
- rollback não validado;
- aprovação humana ausente.

## Smoke independente

Após deploy:

```text
.github/workflows/flyio-smoke-monitor.yml
```

Inputs:

```text
environment=dev
base_url=https://<app>.fly.dev
duckdns_url=https://<hostname>.duckdns.org
```

## Rollback

Consulte:

```text
docs/FLYIO_ROLLBACK_RUNBOOK.md
```

Validação do runbook:

```bash
python tools/validate_flyio_rollback_runbook.py
```

O rollback redeploya uma imagem anterior selecionada em `flyctl releases --image` e exige novo smoke público.

## Próxima ação operacional

1. confirmar o secret `FLY_API_TOKEN`;
2. executar `Fly.io Public Deploy` em `dev`;
3. validar artifact e URL `.fly.dev`;
4. informar e validar o hostname DuckDNS real;
5. executar `Fly.io Smoke Monitor`;
6. registrar release saudável como candidato de rollback.
