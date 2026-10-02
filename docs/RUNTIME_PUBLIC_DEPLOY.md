# Runtime público provider-neutral

## Decisão

O runtime público do `reqsys-vscode-agent` segue a política `pc24x7-first` e não possui integração de deploy, rollback, segredo ou contingência no Fly.io.

## Componentes ativos

| Componente | Caminho | Responsabilidade |
|---|---|---|
| Readiness | `.github/workflows/runtime-deploy.yml` | valida o contrato por ambiente sem publicar |
| Artefato | `.github/workflows/runtime-artifact.yml` | constrói e inspeciona o container sem push |
| Monitor | `.github/workflows/runtime-smoke-monitor.yml` | executa smoke em URL explícita e recusa Fly.io |
| Roteamento | `docs/RUNTIME_ROUTING_CURRENT.md` | registra a política e os critérios de promoção |

## Variáveis ativas

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_RUNTIME_PROVIDER
REQSYS_PUBLIC_BASE_URL
```

`REQSYS_PUBLIC_BASE_URL` deve ser configurada explicitamente para o runtime autorizado. Hosts `fly.dev` e `fly.io` são inválidos.

## Critérios antes de produção

1. selecionar e registrar o runtime autorizado;
2. validar `/health`, `/ready`, `/runtime-deploy`, `/runtime-artifact` e `/runtime-public`;
3. vincular evidência ao SHA implantado;
4. documentar rollback ou restart para o runtime selecionado;
5. obter a aprovação de produção aplicável.

Os workflows atuais produzem somente evidência de readiness, build e smoke. Eles não publicam um runtime nem alteram DNS ou segredos.
