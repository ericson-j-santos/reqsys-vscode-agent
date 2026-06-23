# Changelog

## 0.2.0 — 2026-06-23

### Adicionado
- Comando CLI `index` para gerar índice local governado.
- Índice em `.reqsys/agent-index/index.json`.
- Leitura limitada a `allowedPaths` do projeto consumidor.
- Bloqueio de arquivos sensíveis e diretórios pesados.
- Hash SHA-256 por arquivo indexado.
- Preview limitado para evidência local.
- Comando VS Code `ReqSys Agent: Index Workspace`.
- Teste automatizado para validar que arquivos sensíveis não entram no índice.

### Mantido fora do escopo
- Sem LLM externo.
- Sem LlamaIndex/Ollama obrigatório.
- Sem banco vetorial.
- Sem patch automático.
- Sem automação de merge/push/produção.

## 0.1.0 — 2026-06-23

### Adicionado
- Base de repositório separado.
- Extensão VS Code mínima.
- Agente Python CLI.
- Exemplo de configuração plugável.
- CI básico.
- Política explícita do que não pode fazer.
