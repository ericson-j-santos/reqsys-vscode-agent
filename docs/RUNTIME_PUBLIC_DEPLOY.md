# REQSYS#002 — Runtime Público / Deploy

## Objetivo

Estabelecer o contrato inicial de publicação, healthcheck, promoção entre ambientes e rollback para a frente **REQSYS#002 • IA_RUNTIME_PUBLICO • DEPLOY_RUNTIME**.

Este incremento não publica produção diretamente. Ele cria uma base executável e auditável para impedir que a frente de runtime avance sem evidência mínima.

## Escopo deste incremento

| Item | Estado | Evidência |
|---|---:|---|
| Comando de contrato de deploy | Implementado | `PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy` |
| Healthcheck de startup | Implementado | `PYTHONPATH=agent python -m reqsys_agent.cli health` |
| Ambientes dev/staging/production | Implementado como contrato | Saída JSON do comando `runtime-deploy` |
| Rollback por ambiente | Documentado | Este documento + payload do comando |
| Teste automatizado | Implementado | `agent/tests/test_cli.py` |
| Workflow de readiness de deploy | Implementado | `.github/workflows/runtime-deploy.yml` |
| Artifact de evidência | Implementado | `runtime-deploy-evidence-*` |
| Pipeline de deploy real | Pendente | Próximo incremento após definição do alvo de runtime |
| URL pública validada | Pendente | Só deve ser informada com CI verde e smoke test |

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

Ambientes aceitos:

- `dev`
- `staging`
- `production`

## Workflow governado

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

## Estratégia de promoção

```text
dev → staging → production
```

A promoção entre ambientes exige:

1. CI verde.
2. Healthcheck retornando `status = ok`.
3. Evidência de smoke/readiness test.
4. Plano de rollback documentado.
5. Ausência de violação dos gates de segurança.
6. Aprovação humana antes de produção.

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
- URL pública não validada por smoke test.
- Execução de produção fora de `workflow_dispatch`.

## Rollback

| Ambiente | Estratégia mínima |
|---|---|
| dev | Reverter para o último commit verde da branch de integração. |
| staging | Promover release anterior validada ou desfazer tag candidata. |
| production | Retornar para release estável anterior e registrar incidente com `correlation_id`. |

## KPIs da frente

| KPI | Meta inicial |
|---|---:|
| Uptime | ≥ 99,5% após runtime público existir |
| Deploy success rate | ≥ 95% após estabilização da pipeline |
| MTTR | ≤ 30 minutos para incidentes com rollback suportado |
| Startup health | 100% obrigatório antes de promoção |
| Evidence coverage | 100% para readiness workflow |

## Status executivo

| Dimensão | Percentual estimado | Observação |
|---|---:|---|
| Técnico | 72% | Contrato executável, health, testes e workflow de readiness aplicados. |
| Operacional | 64% | Artifact de evidência disponível; ainda falta deploy real. |
| Usuário final | 44% | Ainda sem URL pública validada. |
| Governança | 80% | Gates documentados, workflow e artifact de evidência. |
| Produção | 38% | Produção continua bloqueada até runtime real, smoke test e aprovação. |

## Próximo incremento recomendado

Adicionar build de artefato/container quando o alvo de runtime estiver definido.

Exemplos de próximos caminhos possíveis:

1. Container Docker do agente/runtime.
2. Deploy em ambiente público escolhido.
3. Smoke test HTTP contra URL pública.
4. Métrica de uptime.
5. Rollback com release/tag anterior.
