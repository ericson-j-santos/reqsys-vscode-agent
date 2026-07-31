# REQSYS#002.P5 — Runbook de rollback Fly.io

## Objetivo

Restaurar o último runtime conhecido como saudável quando um deploy do `reqsys-vscode-agent` falhar, quando o smoke público retornar erro ou quando os metadados expostos por `/runtime-public` divergirem do ambiente esperado.

O rollback do Fly.io é feito redeployando uma imagem anterior. Ele não desfaz automaticamente migrações ou alterações de dados.

## Escopo

Este runbook cobre:

- app Fly.io do runtime público;
- ambientes lógicos `dev`, `staging` e `production`;
- URL `<app>.fly.dev`;
- hostname DuckDNS quando configurado;
- endpoints `/health`, `/ready`, `/runtime-deploy`, `/runtime-artifact` e `/runtime-public`.

## Pré-condições

1. Secret `FLY_API_TOKEN` disponível no ambiente de execução.
2. Nome exato do app Fly.io.
3. Artifact do deploy com `releases-before.json`, `releases-after.json`, `fly-status.txt` e respostas de smoke.
4. Imagem anterior identificada como conhecida e saudável.
5. Confirmação de que não houve migração destrutiva incompatível com a imagem anterior.

## Critérios que acionam rollback

Execute rollback quando pelo menos uma condição ocorrer após o deploy:

- `/health` ou `/ready` não retornar HTTP 2xx;
- `status` não for `ok`;
- versão exposta não for `0.7.0`;
- `fly_app_name` não corresponder ao app implantado;
- `duckdns_hostname` divergir do hostname informado;
- container não atingir estado saudável dentro do timeout;
- smoke DuckDNS falhar depois de a propagação DNS já estar confirmada;
- regressão funcional ou operacional relevante confirmada.

## Procedimento

### 1. Registrar o incidente

Registre:

- `correlation_id` das respostas disponíveis;
- ambiente;
- app Fly.io;
- commit e run ID;
- horário UTC;
- sintoma observado;
- decisão de rollback.

### 2. Listar releases e imagens

```bash
flyctl releases --app "$FLY_APP_NAME" --image
```

Para evidência estruturada:

```bash
flyctl releases --app "$FLY_APP_NAME" --image --json > releases-rollback.json
```

### 3. Selecionar a imagem anterior saudável

Escolha a imagem imediatamente anterior ao deploy defeituoso, preferencialmente a registrada em `releases-before.json` ou associada ao último commit com smoke verde.

Não selecione uma imagem apenas pela idade. Confirme commit, ambiente e evidência de saúde.

### 4. Redeploy da imagem anterior

```bash
flyctl deploy \
  --app "$FLY_APP_NAME" \
  --image "$PREVIOUS_IMAGE" \
  --strategy rolling \
  --wait-timeout 10m \
  --ha=false \
  --env "REQSYS_RUNTIME_ENVIRONMENT=$SELECTED_ENVIRONMENT" \
  --env "REQSYS_FLY_APP_NAME=$FLY_APP_NAME" \
  --env "REQSYS_DUCKDNS_HOSTNAME=$DUCKDNS_HOSTNAME"
```

Não use estratégia `immediate` por padrão. Ela só deve ser usada quando a indisponibilidade atual for mais grave que o risco de interrupção durante o rollback.

### 5. Validar a URL Fly.io

```bash
curl --fail --show-error --silent "https://${FLY_APP_NAME}.fly.dev/health"
curl --fail --show-error --silent "https://${FLY_APP_NAME}.fly.dev/ready?environment=${SELECTED_ENVIRONMENT}"
curl --fail --show-error --silent "https://${FLY_APP_NAME}.fly.dev/runtime-public?environment=${SELECTED_ENVIRONMENT}"
```

Valide no JSON:

- `status = ok`;
- `version = 0.7.0`;
- `environment` correto;
- `fly_app_name` correto;
- `duckdns_hostname` correto quando configurado.

### 6. Validar DuckDNS

Quando houver hostname configurado:

```bash
curl --fail --show-error --silent "https://${DUCKDNS_HOSTNAME}/health"
```

O rollback do container não altera registros DNS. Se a URL Fly.io estiver saudável e DuckDNS falhar, trate como incidente de DNS/certificado antes de repetir deploys.

### 7. Encerrar ou escalar

Considere o rollback concluído somente quando:

- Fly.io retornar HTTP 2xx nos endpoints obrigatórios;
- payloads apresentarem os metadados esperados;
- DuckDNS estiver saudável quando aplicável;
- artifact de rollback tiver sido publicado;
- incidente registrar causa, ação, resultado e próximo passo.

Escale quando:

- não existir imagem anterior disponível;
- a imagem anterior também falhar;
- houver migração destrutiva ou incompatibilidade de dados;
- o token não possuir escopo para o app;
- o problema for de DNS, certificado ou conta/billing do provedor.

## Evidências obrigatórias

O registro de rollback deve conter:

- `releases-rollback.json`;
- imagem selecionada;
- comando executado sem token;
- `flyctl status` após rollback;
- respostas dos endpoints;
- horário inicial e final;
- actor;
- commit/run que originou o incidente;
- `correlation_id`;
- resultado final: `restored`, `failed` ou `escalated`.

## Restrições

- Nunca registrar `FLY_API_TOKEN` em log ou artifact.
- Nunca declarar recuperação apenas porque o comando de deploy terminou.
- Nunca usar rollback de imagem como substituto de rollback de banco.
- Nunca alterar DuckDNS automaticamente sem credencial e política específicas.
- Produção exige aprovação humana e evidência posterior de smoke.

## Teste do runbook

O script abaixo valida automaticamente a presença das seções, comandos e variáveis obrigatórias:

```bash
python tools/validate_flyio_rollback_runbook.py
```

O workflow `.github/workflows/flyio-rollback-readiness.yml` executa essa validação e publica o artifact `flyio-rollback-readiness-evidence`.
