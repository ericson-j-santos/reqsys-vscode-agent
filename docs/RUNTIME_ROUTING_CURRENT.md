# Runtime routing atual

## Decisão

Fly.io não é mais a rota ativa para esta frente.

A rota ativa deve seguir a regra operacional `runtime-routing`: avaliar e reaproveitar o PC24x7/local primeiro. Provedor externo só deve ser usado quando houver decisão explícita por requisito objetivo de SLA, segurança, continuidade, regulação ou incompatibilidade técnica do host local.

## Estado evidenciado

| Item | Estado |
|---|---|
| Código HTTP runtime | Implementado |
| Contrato `runtime-public` | Provider-neutral / não Fly.io |
| Smoke monitor | Provider-neutral |
| Deploy Fly.io | Legado arquivado |
| Secret `FLY_API_TOKEN` | Não requerido para rota ativa |
| Produção | Bloqueada sem autorização e smoke real |

## Variáveis ativas

```text
REQSYS_RUNTIME_ENVIRONMENT
REQSYS_RUNTIME_PROVIDER
REQSYS_PUBLIC_BASE_URL
```

## Comandos de contrato

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-public \
  --environment dev \
  --provider pc24x7 \
  --base-url http://localhost:8080
```

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-monitor \
  --environment dev \
  --base-url http://localhost:8080
```

## Critério de conclusão da frente

A frente só pode ser considerada operacionalmente concluída quando houver:

1. runtime selecionado e registrado;
2. healthcheck HTTP real verde;
3. smoke real de `/health`, `/ready`, `/runtime-deploy`, `/runtime-artifact` e `/runtime-public`;
4. artifact de evidência do workflow ou host executor;
5. procedimento de rollback/restart documentado para o runtime selecionado;
6. bloqueio explícito de produção sem autorização.

## Legado Fly.io

Os arquivos históricos de Fly.io permanecem no repositório para rastreabilidade, mas não representam a rota ativa. O workflow `Legacy Fly.io Public Deploy` não deve executar deploy.
