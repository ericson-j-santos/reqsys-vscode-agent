# Automação — Living Architecture / Runtime Evidence

**Owner:** IA_DOCUMENTACAO_VIVA  
**Status:** runtime-evidence-local-e2e  
**Atualizado em:** 2026-09-20  
**Escopo:** REQSYS#007 • DOCS_VIVAS • LIVING_ARCHITECTURE

## Objetivo

Validar automaticamente a documentação viva do ReqSys em duas camadas complementares:

1. **drift documental estrito** — documentos, owner, status e data;
2. **evidência runtime↔docs** — contratos versionados, runtime HTTP real executado no CI, telemetria estruturada, artifact e controles negativos.

## Arquivos principais

| Artefato | Papel |
|---|---|
| `docs/living-architecture/runtime-docs-map.json` | Fonte de verdade dos vínculos runtime↔docs e contrato de evidência |
| `tools/living_architecture_doc_drift_check.py` | Gate estrito de estrutura/metadados |
| `tools/living_architecture_runtime_evidence_check.py` | Validador de runtime, contratos, telemetria e controles negativos |
| `.github/workflows/living-architecture-docs.yml` | Workflow de drift documental |
| `.github/workflows/living-architecture-runtime-evidence.yml` | Workflow E2E de evidência runtime↔docs |
| `artifacts/living-architecture-report.json` | Relatório do gate documental |
| `artifacts/living-architecture-runtime-evidence.json` | Relatório positivo do runtime |
| `artifacts/living-architecture-runtime-evidence-negative.json` | Evidência do teste do próprio validador |
| `artifacts/living-architecture-runtime.log` | Telemetria HTTP estruturada da execução |

## Gate documental

O workflow `Living Architecture Docs` opera em **strict-metadata-gate**:

- documento referenciado ausente bloqueia o PR;
- JSON inválido bloqueia o PR;
- ausência de owner, status ou data bloqueia o PR;
- artifact é publicado mesmo quando a validação falha.

## Evidência runtime↔docs

O workflow `Living Architecture Runtime Evidence` executa o runtime HTTP real do código da branch/SHA em ambiente CI e verifica:

- `/health`;
- `/ready`;
- `/runtime-deploy`;
- `/runtime-artifact`;
- `/runtime-public`;
- `status=ok` e `correlation_id` em cada endpoint positivo;
- política `pc24x7-first`;
- `flyio_active=false`;
- contratos de workflows e artifacts versionados;
- evento estruturado `http_access` para os caminhos testados;
- controle negativo com endpoint inexistente, que deve retornar HTTP 404 e `status=blocked`.

## Controle contra falso positivo

Além do caso negativo HTTP, o workflow executa um **teste do próprio teste**:

1. cria uma cópia temporária do mapa;
2. injeta deliberadamente um marcador impossível;
3. executa o validador em modo `--repository-only`;
4. exige falha com o código `REPOSITORY_MARKER_MISSING`.

A cópia temporária fica somente no artifact do run e não é versionada.

## Estado de runtime

A rota ativa segue a política **PC24x7-first/provider-neutral**. Fly.io permanece apenas como legado rastreável.

O incremento atual comprova o runtime real iniciado no runner do CI e vinculado ao SHA da execução. Ele **não** declara que o runtime externo selecionado no PC24x7 está validado.

### Bloqueio externo atual

Para concluir a próxima camada é necessário existir uma URL DEV selecionada e registrada para o runtime PC24x7, fornecida por `REQSYS_PUBLIC_BASE_URL`. Até isso ocorrer, o estado externo é:

`blocked-pending-selected-runtime-url`

## Evolução

| Fase | Comportamento | Estado |
|---|---|---|
| 1 | Warning-first | Concluída |
| 2 | Strict para metadados mínimos | Concluída |
| 3 | Runtime local E2E + artifact + telemetria + controles negativos | Ativa |
| 4 | Runtime selecionado PC24x7/DEV com URL real | Próximo incremento |
| 5 | Cruzamento contínuo com telemetria/uptime do runtime selecionado | Planejada |

## Restrições

- não lê secrets;
- não executa deploy;
- não altera DNS;
- não promove produção;
- não trata Fly.io como rota ativa;
- não usa evidência de outro SHA;
- não declara runtime externo como validado sem URL e smoke atuais.

## Comandos

### Gate documental

```bash
python tools/living_architecture_doc_drift_check.py \
  --map docs/living-architecture/runtime-docs-map.json \
  --report artifacts/living-architecture-report.json \
  --strict
```

### Runtime E2E

```bash
python tools/living_architecture_runtime_evidence_check.py \
  --map docs/living-architecture/runtime-docs-map.json \
  --report artifacts/living-architecture-runtime-evidence.json \
  --base-url http://127.0.0.1:8080 \
  --telemetry-log artifacts/living-architecture-runtime.log
```

## Critério de sucesso do incremento atual

```text
status: passed
errors: 0
warnings: 0
todos os endpoints positivos: passed
controle negativo HTTP: passed
telemetria http_access: passed
teste do próprio validador: falha detectada corretamente
artifact vinculado ao SHA atual: publicado
```
