# ReqSys VSCode Agent

Plugin local e enxuto para VS Code, preparado para ser plugado em projetos como `reqsys-v2-enterprise-real` sem acoplar código de ferramenta ao produto principal.

## Objetivo

Fornecer comandos locais no VS Code para:

- validar o workspace;
- gerar checklist governado;
- construir índice local de contexto;
- consultar informações do projeto com base em evidência local;
- evoluir futuramente para RAG local com LlamaIndex/Ollama.

## Arquitetura mínima

```text
VS Code Extension
  -> Python Agent CLI
  -> Workspace Reader Governado
  -> Local Context Index
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
- Não usa LLM por padrão nesta fase.

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

## Uso local do agente

### Health

```bash
PYTHONPATH=agent python -m reqsys_agent.cli health
```

### Inspecionar workspace

```bash
PYTHONPATH=agent python -m reqsys_agent.cli inspect --workspace /caminho/do/projeto
```

### Gerar índice local

```bash
PYTHONPATH=agent python -m reqsys_agent.cli build-index --workspace /caminho/do/projeto
```

O índice é gerado em:

```text
.reqsys/index.json
```

### Perguntar ao contexto local

```bash
PYTHONPATH=agent python -m reqsys_agent.cli ask \
  --workspace /caminho/do/projeto \
  --question "Quais workflows existem?"
```

## Comandos VS Code

| Comando | Função |
|---|---|
| `ReqSys Agent: Health` | valida o agente local |
| `ReqSys Agent: Inspect Workspace` | mostra configuração e escopo |
| `ReqSys Agent: Governance Checklist` | mostra checklist governado |
| `ReqSys Agent: Build Local Context` | cria `.reqsys/index.json` |
| `ReqSys Agent: Ask Local Context` | pergunta ao índice local |

## Segurança operacional

O leitor de workspace:

- usa somente caminhos permitidos por configuração;
- ignora binários;
- ignora arquivos grandes;
- bloqueia diretórios técnicos pesados;
- bloqueia nomes sensíveis conhecidos;
- opera em modo `safe-readonly`;
- não usa LLM nesta fase.

## Roadmap enxuto

| Fase | Entrega |
|---|---|
| 0.1 | CLI + extensão + config plugável |
| 0.2 | Workspace Reader + Local Context Index |
| 0.3 | Busca semântica opcional |
| 0.4 | LlamaIndex/Ollama opcional |
| 0.5 | Sugestão de patch assistida |
