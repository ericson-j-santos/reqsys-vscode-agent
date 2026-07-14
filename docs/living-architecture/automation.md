# Automação — Living Architecture Doc Drift Check

**Owner:** IA_DOCUMENTACAO_VIVA  
**Status:** warning-first  
**Atualizado em:** 2026-06-25  
**Escopo:** REQSYS#007 • DOCS_VIVAS • LIVING_ARCHITECTURE

## Objetivo

Automatizar a primeira camada de validação da documentação viva do ReqSys, garantindo que os documentos referenciados no mapa runtime↔docs existam e possuam metadados mínimos de governança.

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
4. Verificação de metadados mínimos:
   - owner/responsável;
   - status/estado;
   - data de atualização.
5. Geração de relatório JSON consolidado.

## Modo operacional

O modo inicial é **warning-first**:

- documentos ausentes geram falha;
- JSON inválido gera falha;
- ausência de metadados gera warning;
- warnings não bloqueiam merge nesta primeira fase.

## Evolução planejada

| Fase | Comportamento | Critério de avanço |
|---|---|---|
| 1 | Warning-first | Workflow verde com relatório publicado |
| 2 | Strict parcial | Metadados mínimos obrigatórios em docs canônicos |
| 3 | Gate bloqueante | Drift documental bloqueia merge |
| 4 | Runtime-linked | Evidência runtime↔docs cruzada com telemetria |

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
  --report artifacts/living-architecture-report.json
```

Para endurecimento futuro:

```bash
python tools/living_architecture_doc_drift_check.py --strict
```
