# Governança — Documentação Viva / Arquitetura Viva

**Frente:** REQSYS#007  
**Owner:** IA_DOCUMENTACAO_VIVA  
**Atualizado em:** 2026-06-25  
**Status:** baseline inicial governado.

## 1. Princípios

A documentação viva do ReqSys deve ser:

- versionada no Git;
- rastreável por PR, commit e changelog;
- vinculada a componentes reais de runtime, CI/CD, observabilidade, UX ou automação;
- auditável por metadados mínimos;
- validável por automação progressiva;
- distinta entre estado evidenciado e estado alvo.

## 2. Regras obrigatórias

| Regra | Descrição | Severidade inicial |
|---|---|---|
| DOC-GOV-001 | Todo documento vivo deve possuir owner, status e data de atualização. | Warning |
| DOC-GOV-002 | Todo componente crítico deve aparecer no `runtime-docs-map.json`. | Warning |
| DOC-GOV-003 | Toda decisão arquitetural relevante deve gerar ADR ou referência equivalente. | Warning |
| DOC-GOV-004 | PRs de documentação viva devem alterar escopo limitado e rastreável. | Warning |
| DOC-GOV-005 | Não declarar maturidade consolidada sem evidência automatizada ou manual verificável. | Blocking |
| DOC-GOV-006 | Não expor secrets, tokens, PII, CPF, connection strings ou chaves em documentos. | Blocking |
| DOC-GOV-007 | Links de runtime público só devem ser publicados como estáveis após CI/health check verde. | Blocking |

## 3. Gates recomendados

### 3.1 Gate documental mínimo

- Arquivo existe.
- Arquivo é UTF-8 legível.
- Possui título claro.
- Possui owner/status/data quando for documento vivo.
- Não contém padrões óbvios de segredo ou PII.

### 3.2 Gate runtime↔docs

- Todo componente runtime mapeado possui documento vinculado.
- Todo documento vinculado existe no repositório.
- Documentos críticos apontam o ambiente correto quando citarem URLs ou endpoints.

### 3.3 Gate de maturidade

- `Experimental`: documento inicial sem validação.
- `Controlado`: documento revisado manualmente.
- `Avançado`: documento validado por CI.
- `Padrão Ouro Consolidado`: documento validado por CI, runtime, analytics e changelog.

## 4. O que não deve ser feito

- Não criar documentação duplicada para o mesmo componente sem índice canônico.
- Não registrar URL pública como pronta se o CI ou health check estiver falho.
- Não alterar workflow produtivo nesta frente sem alinhamento com IA Governança/CI.
- Não usar Mermaid, HTML ou markdown com dependências externas obrigatórias.
- Não misturar implementação funcional com documentação viva no mesmo PR, salvo correção mínima necessária.

## 5. Próximo incremento governado

Criar `scripts/validate-living-architecture-docs.*` e integrar em CI inicialmente como warning, evoluindo para gate bloqueante depois de estabilizado.
