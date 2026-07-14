# REQSYS#002.P4 — Fly.io Smoke Monitor

## Objetivo

Adicionar uma validação operacional reutilizável para verificar a URL pública do Fly.io e o hostname DuckDNS após o deploy controlado.

Este incremento não faz deploy, não altera DNS e não lê secrets. Ele apenas executa smoke tests HTTP e publica artifact de evidência.

## Workflow

```text
.github/workflows/flyio-smoke-monitor.yml
```

## Modos de execução

### Pull request

Executa somente validação do contrato:

1. instala dependências;
2. executa testes;
3. emite contrato `runtime-monitor`;
4. publica artifact `flyio-smoke-monitor-validation-evidence`.

Não chama URL pública em PR.

### Workflow dispatch

Executa smoke HTTP real com inputs:

| Input | Descrição | Exemplo |
|---|---|---|
| `environment` | Ambiente lógico | `dev` |
| `base_url` | URL principal | `https://reqsys-vscode-agent.fly.dev` |
| `duckdns_url` | URL DuckDNS opcional | `https://reqsys.duckdns.org` |

## Endpoints validados

| Endpoint | Alvo |
|---|---|
| `/health` | Fly.io + DuckDNS quando informado |
| `/ready` | Fly.io |
| `/runtime-deploy` | Fly.io |
| `/runtime-artifact` | Fly.io |
| `/runtime-public` | Fly.io |

## Critérios de sucesso

O workflow passa quando:

1. a URL principal usa HTTPS;
2. todos os endpoints principais retornam HTTP 2xx;
3. DuckDNS retorna HTTP 2xx em `/health` quando informado;
4. artifact de evidência é publicado.

## Evidências geradas

| Arquivo | Conteúdo |
|---|---|
| `monitor-contract.json` | Contrato do monitor. |
| `primary-health.json` | Resposta `/health` da URL principal. |
| `primary-ready.json` | Resposta `/ready` da URL principal. |
| `primary-runtime-deploy.json` | Resposta `/runtime-deploy`. |
| `primary-runtime-artifact.json` | Resposta `/runtime-artifact`. |
| `primary-runtime-public.json` | Resposta `/runtime-public`. |
| `duckdns-health.json` | Resposta `/health` via DuckDNS, se informado. |
| `summary.md` | Resumo da execução. |

## Limites explícitos

Este workflow não:

- faz deploy;
- faz rollback;
- cria DNS;
- altera secrets;
- declara SLA de uptime com base em uma única execução;
- corrige indisponibilidade automaticamente.

## Próximo incremento recomendado

Após a URL pública ficar estável:

1. adicionar monitoramento agendado leve;
2. guardar histórico de smoke por artifact;
3. gerar métrica de disponibilidade estimada;
4. criar alerta quando `/health` falhar;
5. acoplar rollback runbook ao artifact de falha.
