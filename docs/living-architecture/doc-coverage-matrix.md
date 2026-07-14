# Matriz de Cobertura Documental — REQSYS#007

**Owner:** IA_DOCUMENTACAO_VIVA  
**Atualizado em:** 2026-06-25  
**Status:** baseline inicial  
**Escopo:** documentação viva, arquitetura viva e aderência runtime↔docs.

## 1. Matriz executiva

| Domínio | Componente crítico | Documento obrigatório | Evidência atual | Status | Risco |
|---|---|---|---|---|---|
| Runtime Público | Health checks, rollout, rollback | README + runtime-docs-map | Documento inicial | Parcial | Médio |
| CI/CD Governado | Branch policies, gates, artifacts | governance.md | Documento inicial | Parcial | Médio |
| Observabilidade | Logs, métricas, traces, dashboards | analytics.md | Documento inicial | Parcial | Médio |
| UX/UI Operacional | Navegação, responsividade, drill-down | README + index.html | Documento inicial | Parcial | Médio |
| Decisões Arquiteturais | ADRs e decisões operacionais | ADRs futuros | Pendente | Aberto | Alto |
| Changelog | Registro por incremento | CHANGELOG futuro ou seção dedicada | Pendente | Aberto | Médio |
| Grafo Arquitetural | Relacionamentos docs/runtime/CI/analytics | architecture-graph.mmd | Criado | Inicial | Baixo |

## 2. Critérios de cobertura

A cobertura documental será considerada válida somente quando cada componente crítico tiver:

1. Documento fonte versionado.
2. Owner explícito.
3. Data de atualização.
4. Status evidenciado.
5. Relação com componente runtime, CI, analytics, UX ou governança.
6. Evidência manual ou automática.
7. Próxima ação quando o status não estiver consolidado.

## 3. Cálculo inicial

| Métrica | Numerador | Denominador | Percentual inicial estimado |
|---|---:|---:|---:|
| Componentes com documento inicial | 4 | 7 | 57,14% |
| Componentes com evidência automática | 0 | 7 | 0,00% |
| Componentes com risco alto aberto | 1 | 7 | 14,29% |
| Componentes com grafo inicial | 1 | 1 | 100,00% |

## 4. Interpretação

O percentual de 84% informado para a frente deve ser tratado como **maturidade alvo operacional**, não como evidência plena. O estado evidenciado deste incremento é uma base inicial auditável, mas ainda sem validação automática contra runtime e CI.

## 5. Próxima ação objetiva

Adicionar um workflow ou script de validação que percorra `runtime-docs-map.json`, verifique a existência dos documentos, extraia metadados mínimos e publique um relatório de cobertura como artifact de CI.
