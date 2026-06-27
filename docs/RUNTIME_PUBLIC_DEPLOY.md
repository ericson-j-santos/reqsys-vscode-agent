# REQSYS#002 — Runtime Público / Deploy

## Objetivo

Estabelecer o contrato inicial de publicação, healthcheck, promoção entre ambientes, rollback, readiness e artefato/container para a frente **REQSYS#002 • IA_RUNTIME_PUBLICO • DEPLOY_RUNTIME**.

Este incremento não publica produção diretamente. Ele cria uma base executável e auditável para impedir que a frente de runtime avance sem evidência mínima.

## Escopo consolidado

| Item | Estado | Evidência |
|---|---:|---|
| Comando de contrato de deploy | Implementado | `PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy` |
| Comando de contrato de artefato/container | Implementado | `PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact` |
| Healthcheck de startup | Implementado | `PYTHONPATH=agent python -m reqsys_agent.cli health` |
| Ambientes dev/staging/production | Implementado como contrato | Saída JSON do comando `runtime-deploy` |
| Rollback por ambiente | Documentado | Este documento + payload do comando |
| Teste automatizado | Implementado | `agent/tests/test_cli.py` |
| Workflow de readiness de deploy | Implementado | `.github/workflows/runtime-deploy.yml` |
| Workflow de artefato/container | Implementado | `.github/workflows/runtime-artifact.yml` |
| Dockerfile do runtime agent | Implementado | `runtime/Dockerfile.agent` |
| Artifact de evidência | Implementado | `runtime-deploy-evidence-*` e `runtime-container-artifact-evidence-*` |
| Push para registry | Pendente | Exige alvo explícito, credentials e governança |
| Pipeline de deploy real | Pendente | Próximo incremento após definição do alvo público |
| URL pública validada | Pendente | Só deve ser informada com CI verde e smoke test HTTP |

## Comandos operacionais

### Healthcheck

```bash
PYTHONPATH=agent python -m reqsys_agent.cli health
```

Resultado esperado:

```json
{
  "status": "ok",
  "service": "reqsys-vscode-agent",
  "mode": "safe-readonly"
}
```

### Contrato de deploy de todos os ambientes

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy
```

### Contrato de deploy por ambiente

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy --environment staging
```

### Contrato de artefato/container

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact
```

### Contrato de artefato/container por ambiente

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact --environment staging
```

Ambientes aceitos:

- `dev`
- `staging`
- `production`

## Workflow governado de readiness

O workflow de readiness fica em:

```text
.github/workflows/runtime-deploy.yml
```

Ele pode ser executado por:

- `pull_request`, usando ambiente lógico `dev`;
- `workflow_dispatch`, com seleção manual de `dev`, `staging` ou `production`.

O workflow executa:

1. Instalação do agente.
2. Validação do ambiente selecionado.
3. Testes automatizados.
4. Healthcheck.
5. Contrato `runtime-deploy` por ambiente.
6. Bloqueio explícito de produção sem execução manual.
7. Geração de evidência Markdown/JSON.
8. Upload de artifact `runtime-deploy-evidence-*`.

## Workflow governado de artefato/container

O workflow de artefato fica em:

```text
.github/workflows/runtime-artifact.yml
```

Ele executa:

1. Validação do ambiente selecionado.
2. Testes automatizados do agente.
3. Emissão do contrato `runtime-artifact`.
4. Build da imagem Docker usando `runtime/Dockerfile.agent`.
5. Healthcheck dentro do container.
6. Execução do contrato `runtime-deploy` dentro do container.
7. Inspeção de metadados da imagem.
8. Upload de artifact `runtime-container-artifact-evidence-*`.

Este workflow **não faz push para registry**, **não executa deploy** e **não cria URL pública**.

## Estratégia de promoção

```text
dev → staging → production
```

A promoção entre ambientes exige:

1. CI verde.
2. Healthcheck retornando `status = ok`.
3. Evidência de smoke/readiness test.
4. Artefato/container validado.
5. Plano de rollback documentado.
6. Ausência de violação dos gates de segurança.
7. Aprovação humana antes de produção.

## Gates que bloqueiam produção

Produção deve permanecer bloqueada se qualquer condição abaixo estiver presente:

- Auth desligada.
- CORS permissivo com `*`.
- JWT sem validação real de issuer/audience.
- Log com token, senha, CPF, PII ou connection string.
- Auditoria sem `correlation_id`.
- Falta de healthcheck de startup.
- Falta de rollback operacional.
- Falta de evidência do CI.
- Falta de evidência do container.
- URL pública não validada por smoke test HTTP.
- Execução de produção fora de `workflow_dispatch`.
- Push de imagem para registry sem alvo, credenciais e política explícita.

## Rollback

| Ambiente | Estratégia mínima |
|---|---|
| dev | Reverter para o último commit verde da branch de integração. |
| staging | Promover release anterior validada ou desfazer tag candidata. |
| production | Retornar para release/container tag estável anterior e registrar incidente com `correlation_id`. |

## KPIs da frente

| KPI | Meta inicial |
|---|---:|
| Uptime | ≥ 99,5% após runtime público existir |
| Deploy success rate | ≥ 95% após estabilização da pipeline |
| MTTR | ≤ 30 minutos para incidentes com rollback suportado |
| Startup health | 100% obrigatório antes de promoção |
| Evidence coverage | 100% para readiness e artifact workflows |
| Container build success | ≥ 95% após estabilização |

## Status executivo

| Dimensão | Percentual estimado | Observação |
|---|---:|---|
| Técnico | 78% | Contrato, health, testes, readiness workflow e container artifact aplicados. |
| Operacional | 70% | Evidências de readiness e container disponíveis; ainda falta deploy real. |
| Usuário final | 46% | Ainda sem URL pública validada. |
| Governança | 84% | Gates, artifacts e bloqueios documentados. |
| Produção | 40% | Produção continua bloqueada até runtime real, smoke test HTTP, registry/deploy alvo e aprovação. |

## Próximo incremento recomendado

Escolher o alvo de runtime público e adicionar job de deployment controlado.

Caminhos possíveis:

1. Build + push para registry controlado.
2. Deploy em ambiente público escolhido.
3. Smoke test HTTP contra URL pública.
4. Métrica de uptime.
5. Rollback com release/tag/container anterior.
