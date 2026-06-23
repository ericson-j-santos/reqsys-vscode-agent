# ReqSys VSCode Agent

Plugin local e enxuto para VS Code, preparado para ser plugado em projetos como `reqsys-v2-enterprise-real` sem acoplar código de ferramenta ao produto principal.

## Objetivo

Fornecer comandos locais no VS Code para:

- validar o workspace;
- gerar checklist governado;
- consultar informações do projeto com base em contexto local;
- evoluir futuramente para RAG local com LlamaIndex/Ollama.

## Arquitetura mínima

```text
VS Code Extension
  -> Python Agent CLI
  -> Workspace local
  -> Arquivo de configuração do projeto
```

## O que este projeto não faz

- Não faz merge automático.
- Não faz push automático.
- Não altera produção.
- Não aplica patch sem aprovação.
- Não lê arquivos sensíveis.
- Não depende do build do projeto consumidor.
- Não exige arquitetura máxima para começar.

## Estrutura

```text
extension/
agent/
examples/reqsys.config.json
docs/
.github/workflows/
README.md
```

## Projeto consumidor

No projeto consumidor, criar um arquivo similar a:

```text
.reqsys-agent.json
```

Exemplo disponível em:

```text
examples/reqsys.config.json
```

## Instalação local

### Agente

```bash
cd agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m reqsys_agent.cli health
```

### Extensão

```bash
cd extension
npm install
npm run compile
```

## Roadmap enxuto

| Fase | Entrega |
|---|---|
| 0.1 | CLI + extensão + config plugável |
| 0.2 | Leitura de arquivos permitidos |
| 0.3 | Índice local simples |
| 0.4 | LlamaIndex/Ollama opcional |
| 0.5 | Sugestão de patch assistida |
