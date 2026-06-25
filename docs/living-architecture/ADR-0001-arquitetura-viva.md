# ADR-0001 — Instituir Documentação Viva / Arquitetura Viva no ReqSys

**Status:** Proposto  
**Data:** 2026-06-25  
**Owner:** IA_DOCUMENTACAO_VIVA  
**Frente:** REQSYS#007  
**Branch:** `ai/living-architecture`

## Contexto

O ReqSys v2 Enterprise está evoluindo por frentes paralelas de IA, incluindo runtime público, observabilidade, UX/UI, governança/CI/CD e automação autônoma. Sem uma camada de documentação viva, há risco de divergência entre decisões, código, runtime, CI, artifacts e dashboards.

Documentos estáticos não são suficientes para manter rastreabilidade em um projeto com múltiplas IAs, PRs pequenos, gates de CI/CD e evolução contínua.

## Decisão

Instituir a frente `REQSYS#007 — Documentação Viva / Arquitetura Viva` como camada transversal responsável por:

1. ADRs versionados.
2. Diagramas vivos em formato textual e auditável.
3. Mapeamento runtime↔docs.
4. Matriz de cobertura documental.
5. Governança documental com gates progressivos.
6. Analytics documental.
7. Painel HTML autocontido para leitura executiva.

A documentação deve diferenciar explicitamente estado evidenciado de estado alvo. Percentuais de maturidade só podem ser declarados como consolidados quando houver evidência real.

## Consequências positivas

- Reduz risco de drift entre runtime e documentação.
- Facilita atuação coordenada entre múltiplas IAs.
- Melhora auditabilidade e rastreabilidade por PR.
- Cria base para validação automática de cobertura documental.
- Permite visão executiva navegável e versionada.

## Consequências negativas / custos

- Exige manutenção contínua dos mapas documentais.
- Pode gerar ruído se os gates forem ativados como bloqueantes antes da estabilização.
- Requer alinhamento com IA Governança/CI para evitar conflito em workflows.

## Alternativas consideradas

| Alternativa | Motivo de rejeição |
|---|---|
| Manter documentação manual solta | Alto risco de desatualização e baixa rastreabilidade. |
| Usar apenas README central | Não suporta arquitetura viva, analytics e governança granular. |
| Criar workflow bloqueante imediatamente | Risco de travar PRs antes da linha de base estabilizar. |

## Decisão operacional

Começar com baseline documental e validação manual. No próximo incremento, criar validador automático em modo warning. Após estabilização, promover parte das regras para gate bloqueante.

## Critério de revisão futura

Revisar esta ADR quando:

- o validador automático existir;
- houver artifact `living-architecture-report.json`;
- a cobertura documental estiver acima de 90%;
- a aderência runtime↔docs for validada por CI ou runtime health check.
