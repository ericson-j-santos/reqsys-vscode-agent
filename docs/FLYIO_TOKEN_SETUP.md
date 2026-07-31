# Fly.io Token Setup

## Causa do bloqueio

O workflow `Fly.io Public Deploy` exige o secret de repositório:

```text
FLY_API_TOKEN
```

Sem esse secret, o deploy é bloqueado antes da instalação de dependências e antes de qualquer chamada ao Fly.io.

## Onde configurar

Acesse:

```text
https://github.com/ericson-j-santos/reqsys-vscode-agent/settings/secrets/actions
```

Depois:

1. selecione **New repository secret**;
2. use o nome exato `FLY_API_TOKEN`;
3. cole um token válido do Fly.io;
4. salve o secret;
5. execute novamente o workflow `Fly.io Public Deploy`.

## Segurança

- não registre o token em arquivo;
- não use GitHub Variables para esse valor;
- não inclua o token em logs, issues ou comentários;
- não altere o nome do secret;
- faça rotação do token se houver exposição.

## Comportamento do workflow

Quando o token estiver ausente, o workflow:

- falha no preflight;
- apresenta annotation objetiva no job;
- registra o link de configuração no step summary;
- publica artifact de evidência;
- não instala flyctl;
- não instala dependências Python;
- não tenta consultar status ou releases no Fly.io.
