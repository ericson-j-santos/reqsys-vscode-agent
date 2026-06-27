# REQSYS#002.P3 — Fly.io + DuckDNS Public Deploy

## Decisão

A frente de runtime público usa **Fly.io** como alvo oficial e mantém **DuckDNS** como hostname externo já utilizado pelo projeto.

## Objetivo

Adicionar deploy público controlado, com custo mínimo, execução manual e evidência obrigatória de smoke HTTP antes de qualquer declaração de produção pronta.

## Arquivos

| Arquivo | Função |
|---|---|
| `fly.toml` | Configuração Fly.io do app, build, região, HTTP service e autostop/autostart. |
| `.github/workflows/flyio-deploy.yml` | Validação em PR e deploy manual via `workflow_dispatch`. |
| `runtime/Dockerfile.agent` | Container HTTP do agente. |
| `agent/reqsys_agent/http_runtime.py` | Serviço HTTP com endpoints de health/readiness. |

## Endpoints públicos

| Endpoint | Uso |
|---|---|
| `/health` | Healthcheck principal. |
| `/ready` | Readiness HTTP. |
| `/runtime-deploy` | Contrato de deploy por ambiente. |
| `/runtime-artifact` | Contrato de artefato/container. |
| `/runtime-public` | Contrato Fly.io + DuckDNS. |

## Estratégia de custo mínimo

O `fly.toml` usa:

```toml
auto_stop_machines = "stop"
auto_start_machines = true
min_machines_running = 0
```

Também evita, neste incremento:

- banco pago;
- volume persistente obrigatório;
- push externo para registry;
- deploy automático em produção;
- criação automática de DNS.

## Secrets e inputs

### Secret obrigatório

```text
FLY_API_TOKEN
```

### Inputs manuais do workflow

| Input | Descrição | Default |
|---|---|---|
| `environment` | Ambiente lógico | `dev` |
| `app_name` | Nome do app Fly.io | `reqsys-vscode-agent` |
| `duckdns_hostname` | Hostname DuckDNS, sem `https://` | vazio |

## Fluxo do workflow

### Pull request

Executa apenas validação local:

1. testes Python;
2. build Docker;
3. container local em `localhost:8080`;
4. smoke HTTP local;
5. artifact `flyio-runtime-validation-evidence`.

### Workflow dispatch

Executa deploy real:

1. valida inputs;
2. valida `FLY_API_TOKEN`;
3. executa testes;
4. emite contrato `runtime-public`;
5. executa `flyctl deploy`;
6. smoke HTTP em `https://<app_name>.fly.dev`;
7. smoke opcional obrigatório no DuckDNS se `duckdns_hostname` for informado;
8. captura `flyctl status`;
9. publica artifact `flyio-public-deploy-evidence-*`.

## Gates que bloqueiam produção

Produção continua bloqueada se houver:

- ausência de `FLY_API_TOKEN`;
- falha nos testes;
- falha no build Docker;
- falha no `flyctl deploy`;
- falha no smoke HTTP da URL `.fly.dev`;
- falha no smoke DuckDNS quando hostname for informado;
- ausência de artifact de evidência;
- tentativa de declarar produção pronta sem aprovação humana.

## Comando local equivalente

```bash
PYTHONPATH=agent python -m reqsys_agent.cli serve --host 0.0.0.0 --port 8080
```

## Próximo incremento

Após merge e execução manual do workflow:

1. validar URL `.fly.dev` real;
2. validar hostname DuckDNS real;
3. registrar tempo de resposta inicial;
4. adicionar monitoramento de uptime;
5. documentar rollback com release anterior do Fly.io.
