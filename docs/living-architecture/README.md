# REQSYS#007 — Documentação Viva / Arquitetura Viva

**Frente:** `REQSYS#007 • IA_DOCUMENTACAO_VIVA • LIVING_ARCHITECTURE`  
**Branch padrão:** `ai/living-architecture`  
**Estado alvo:** Padrão Ouro ReqSys v2 Enterprise  
**Maturidade declarada:** 84% como alvo operacional inicial, pendente de evidência automatizada completa.

## 1. Objetivo

Consolidar a camada de documentação viva do ReqSys, garantindo que decisões, diagramas, changelog, governança, analytics e vínculos com runtime sejam versionados, auditáveis, navegáveis e rastreáveis.

Esta frente não deve ser tratada como documentação estática. O objetivo é manter uma arquitetura viva, conectada a código, runtime, CI/CD, observabilidade, analytics e evidências de execução.

## 2. Escopo

| Área | Entrega esperada | Estado inicial |
|---|---|---:|
| ADRs | Registro de decisões arquiteturais e operacionais | Em implantação |
| Diagramas vivos | Mermaid/graph versionável e navegável | Em implantação |
| Runtime-linked docs | Mapa entre endpoints, dashboards, workflows e documentação | Em implantação |
| Changelog | Registro rastreável por incremento | Em implantação |
| Governance docs | Regras de alteração documental e gates mínimos | Em implantação |
| Analytics docs | Métricas para cobertura documental e aderência runtime↔docs | Em implantação |
| Architecture graph | Grafo de relacionamento entre runtime, docs, CI e observabilidade | Em implantação |

## 3. KPIs obrigatórios

| KPI | Definição | Fórmula inicial |
|---|---|---|
| Cobertura documental | Percentual de componentes críticos com documentação vinculada | `componentes_documentados / componentes_criticos * 100` |
| Aderência runtime↔docs | Percentual de componentes runtime com link documental válido | `vinculos_runtime_validos / vinculos_runtime_esperados * 100` |
| Atualização automática | Percentual de documentos atualizados por evidência automatizada | `docs_com_evidencia_automatica / docs_vivos * 100` |
| Rastreabilidade decisória | Percentual de decisões relevantes cobertas por ADR | `decisoes_com_adr / decisoes_relevantes * 100` |
| Auditabilidade | Percentual de docs com data, owner, status e fonte de evidência | `docs_auditaveis / docs_obrigatorios * 100` |

## 4. Contrato de entrega da IA

Cada incremento desta frente deve:

1. Alterar preferencialmente entre 1 e 8 arquivos.
2. Preservar o funcionamento do runtime público.
3. Não alterar gates de produção sem evidência e revisão da IA Coordenadora.
4. Incluir impacto em documentação, governança ou rastreabilidade.
5. Declarar claramente estado evidenciado versus estado alvo.
6. Evitar duplicidade com frentes de runtime, observabilidade, UX e automação autônoma.

## 5. Definition of Done

Um incremento de documentação viva só pode ser considerado concluído quando:

- o conteúdo estiver versionado no Git;
- houver relação explícita com runtime, CI, analytics, ADR ou governança;
- o documento informar owner, status e data de atualização quando aplicável;
- o PR estiver com CI verde ou com falhas justificadas como não bloqueantes;
- os links navegáveis forem validados quando existirem;
- houver changelog do incremento.

## 6. Estado evidenciado versus estado alvo

| Dimensão | Estado evidenciado agora | Estado alvo padrão ouro |
|---|---|---|
| Documentação | Base inicial criada nesta branch | Cobertura documental automatizada e validada |
| Diagramas | Grafo Mermaid inicial | Grafo atualizado automaticamente por CI/runtime |
| Runtime-linked docs | Mapa JSON inicial | Validação automática contra endpoints e artifacts reais |
| Governance | Regras documentadas | Gate automático bloqueando drift documental crítico |
| Analytics | Métricas especificadas | Dashboard operacional com série histórica |

## 7. Próximo incremento recomendado

Implementar um verificador automático de drift documental que leia `runtime-docs-map.json`, valide a existência dos documentos referenciados e gere um artifact de cobertura documental no CI.
