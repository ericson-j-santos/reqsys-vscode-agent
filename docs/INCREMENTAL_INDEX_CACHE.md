# Incremental Index Cache

## Objetivo

Acelerar a reconstrução do índice local do ReqSys VSCode Agent sem adicionar arquitetura pesada.

## Decisão

Manter o índice local em modo simples e governado, com cache incremental baseado em metadados dos arquivos já processados.

## Arquivos locais gerados em runtime

```text
.reqsys/index.json
.reqsys/manifest.json
```

Esses arquivos continuam locais e não devem ser versionados.

## Estratégia

O build do índice deve comparar, para cada arquivo permitido:

- caminho relativo;
- tamanho;
- data de modificação;
- hash calculado quando necessário.

Se o arquivo não mudou, o item indexado anterior pode ser reaproveitado.

## Métricas esperadas

O retorno de `build-index` deve expor:

```json
{
  "cache": {
    "enabled": true,
    "cache_hits": 10,
    "cache_misses": 2
  }
}
```

## O que não faz

- Não adiciona banco vetorial.
- Não adiciona Qdrant.
- Não adiciona LlamaIndex obrigatório.
- Não adiciona Ollama obrigatório.
- Não faz patch automático.
- Não faz merge/push.
- Não lê arquivos sensíveis.

## Próximo passo técnico

Implementar a leitura e escrita do manifesto incremental dentro de `workspace_reader.py`, preservando compatibilidade com o índice atual.
