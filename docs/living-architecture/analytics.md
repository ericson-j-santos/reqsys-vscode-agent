# Analytics da Documentação Viva — REQSYS#007

**Owner:** IA_DOCUMENTACAO_VIVA  
**Atualizado em:** 2026-06-25  
**Status:** baseline inicial.

## 1. Objetivo

Definir métricas para acompanhar a saúde da documentação viva, a aderência entre runtime e documentação e a evolução rumo ao padrão ouro consolidado.

## 2. Indicadores principais

| Indicador | Tipo | Fórmula | Meta alvo |
|---|---|---|---:|
| Cobertura documental | Efetividade | `componentes_documentados / componentes_criticos * 100` | >= 95% |
| Aderência runtime↔docs | Confiabilidade | `links_validos / links_esperados * 100` | >= 95% |
| Atualização automática | Automação | `docs_validados_por_ci / docs_vivos * 100` | >= 90% |
| Rastreabilidade por ADR | Governança | `decisoes_com_adr / decisoes_relevantes * 100` | >= 90% |
| Drift documental | Risco | `itens_desatualizados / itens_mapeados * 100` | <= 5% |
| Documentos com metadados mínimos | Auditabilidade | `docs_com_owner_status_data / docs_obrigatorios * 100` | 100% |

## 3. Eventos recomendados

| Evento | Quando gerar | Campos mínimos |
|---|---|---|
| `living_docs.validation_started` | Início da validação documental | `correlation_id`, `branch`, `commit_sha` |
| `living_docs.validation_completed` | Fim da validação | `correlation_id`, `status`, `coverage_percent` |
| `living_docs.drift_detected` | Documento ausente, sem owner ou sem vínculo | `correlation_id`, `path`, `rule_id`, `severity` |
| `living_docs.runtime_link_checked` | Validação de vínculo runtime↔docs | `correlation_id`, `component_id`, `validation_status` |
| `living_docs.maturity_changed` | Mudança de maturidade documental | `correlation_id`, `from`, `to`, `evidence` |

## 4. Dashboard executivo recomendado

Cards mínimos:

1. Cobertura documental total.
2. Aderência runtime↔docs.
3. Quantidade de drifts abertos.
4. Documentos sem owner/status/data.
5. ADRs pendentes.
6. Última validação automática.
7. Tendência de maturidade.

## 5. Drill-down obrigatório

Cada card deve permitir abrir o analítico filtrado por:

- domínio;
- componente;
- severidade;
- documento;
- branch;
- PR;
- data da última validação;
- owner.

## 6. Estado inicial calculado

| Dimensão | Percentual evidenciado | Observação |
|---|---:|---|
| Cobertura documental inicial | 57,14% | Base documental criada para 4 de 7 domínios críticos. |
| Automação documental | 0,00% | Ainda não há validador automatizado nesta branch. |
| Aderência runtime↔docs automatizada | 0,00% | Mapa criado, validação pendente. |
| Maturidade alvo informada | 84,00% | Tratada como alvo, não como evidência final. |

## 7. Próximo incremento analítico

Gerar `living-architecture-report.json` durante o CI com os percentuais calculados e publicar como artifact navegável.
