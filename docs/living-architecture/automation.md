# Automação — Living Architecture Doc Drift Check

**Owner:** IA_DOCUMENTACAO_VIVA  
**Status:** strict-metadata-gate  
**Atualizado em:** 2026-07-31  
**Escopo:** REQSYS#007 • DOCS_VIVAS • LIVING_ARCHITECTURE

## Objetivo

Validar automaticamente a documentação viva do ReqSys, garantindo que os documentos referenciados no mapa runtime↔docs existam e possuam metadados mínimos de governança.

## Arquivos principais

| Artefato | Papel |
|---|---|
| `docs/living-architecture/runtime-docs-map.json` | Fonte de verdade dos vínculos runtime↔docs |
| `tools/living_architecture_doc_drift_check.py` | Validador local/CI da aderência documental |
| `.github/workflows/living-architecture-docs.yml` | Workflow dedicado para documentação viva |
| `artifacts/living-architecture-report.json` | Relatório gerado em CI para auditoria |

## Validações executadas

1. Validação sintática do JSON `runtime-docs-map.json`.
2. Validação da estrutura `runtime_doc_links`.
3. Verificação de existência dos documentos referenciados.
4. Verificação obrigatória de metadados mínimos:
   - owner/responsável;
   - status/estado;
   - data de atualização.
5. Geração de relatório JSON consolidado.

## Modo operacional atual

O workflow opera em **strict-metadata-gate**:

- documentos ausentes bloqueiam o PR;
- JSON inválido bloqueia o PR;
- ausência de owner, status ou data bloqueia o PR;
- o artifact é publicado mesmo quando a validação falha;
- o gate permanece sem acesso a rede, runtime ou secrets.

A promoção ocorreu após uma execução estável em modo warning-first com:

- `coverage_percent: 100.0`;
- `missing_docs: 0`;
- `metadata_warnings: 0`;
- `findings: 0`.

## Evolução

| Fase | Comportamento | Estado |
|---|---|---|
| 1 | Warning-first | Concluída |
| 2 | Strict para metadados mínimos | Ativa |
| 3 | Gate de drift documental ampliado | Próximo incremento |
| 4 | Runtime-linked com telemetria | Planejada |

## Restrições

- Não acessa rede.
- Não lê secrets.
- Não altera runtime.
- Não executa deploy.
- Não valida conteúdo de negócio; valida estrutura, existência e governança mínima.

## Comando local

```bash
python tools/living_architecture_doc_drift_check.py \
  --map docs/living-architecture/runtime-docs-map.json \
  --report artifacts/living-architecture-report.json \
  --strict
```

## Critério de sucesso

```text
status: passed
coverage_percent: 100.0
missing_docs: 0
metadata_warnings: 0
findings: 0
```
