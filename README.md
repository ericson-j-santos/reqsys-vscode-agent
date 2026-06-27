# ReqSys VSCode Agent

Plugin local e enxuto para VS Code, preparado para ser plugado em projetos como `reqsys-v2-enterprise-real` sem acoplar código de ferramenta ao produto principal.

## Objetivo

Fornecer comandos locais no VS Code para:

- validar o workspace;
- gerar checklist governado;
- construir índice local de contexto;
- consultar informações do projeto com base em evidência local;
- executar busca semântica leve local sem LLM externo;
- expor contrato inicial de runtime público/deploy com healthcheck, ambientes, rollback e artifact de evidência;
- validar artefato/container sem publicar produção;
- evoluir futuramente para RAG local com LlamaIndex/Ollama.

## Arquitetura mínima

```text
VS Code Extension
  -> Python Agent CLI
  -> Workspace Reader Governado
  -> Local Context Index
  -> Keyword Search
  -> Lightweight Semantic Search
  -> Runtime Deploy Readiness Contract
  -> Runtime Deploy Readiness Workflow
  -> Runtime Container Artifact Workflow
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
- Não usa banco vetorial nesta fase.
- Não publica URL pública sem CI verde e smoke test.
- Não faz push de imagem para registry sem alvo e credenciais explícitos.

## Estrutura

```text
extension/
agent/
runtime/
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

### Runtime público / deploy

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy
```

Contrato filtrado por ambiente:

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-deploy --environment staging
```

Esse comando registra o contrato inicial da frente `REQSYS#002 • Runtime Público / Deploy`, incluindo:

- ambientes `dev`, `staging` e `production`;
- healthcheck obrigatório;
- ordem de promoção;
- evidências exigidas;
- KPIs de runtime;
- restrições de segurança;
- diretriz de rollback.

### Artefato/container de runtime

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact
```

Contrato filtrado por ambiente:

```bash
PYTHONPATH=agent python -m reqsys_agent.cli runtime-artifact --environment staging
```

Dockerfile do runtime:

```text
runtime/Dockerfile.agent
```

Documentação detalhada:

```text
docs/RUNTIME_PUBLIC_DEPLOY.md
```

### Workflow de readiness de deploy

```text
.github/workflows/runtime-deploy.yml
```

O workflow executa testes, healthcheck, contrato de deploy por ambiente e publica artifact de evidência `runtime-deploy-evidence-*`.

Ele não publica produção e não cria URL pública.

### Workflow de artefato/container

```text
.github/workflows/runtime-artifact.yml
```

O workflow executa testes, build Docker, healthcheck dentro do container, contrato de deploy dentro do container, inspeção de metadados da imagem e publica artifact de evidência `runtime-container-artifact-evidence-*`.

Ele não faz push para registry, não publica produção e não cria URL pública.

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

### Perguntar ao contexto local por palavra-chave

```bash
PYTHONPATH=agent python -m reqsys_agent.cli ask \
  --workspace /caminho/do/projeto \
  --question "Quais workflows existem?"
```

### Perguntar ao contexto local com busca semântica leve

```bash
PYTHONPATH=agent python -m reqsys_agent.cli semantic-ask \
  --workspace /caminho/do/projeto \
  --question "controle de qualidade de pipelines"
```

A busca semântica desta fase usa TF-IDF + similaridade de cosseno localmente, sem embeddings externos, sem LLM e sem banco vetorial.

## Comandos VS Code

| Comando | Função |
|---|---|
| `ReqSys Agent: Health` | valida o agente local |
| `ReqSys Agent: Inspect Workspace` | mostra configuração e escopo |
| `ReqSys Agent: Governance Checklist` | mostra checklist governado |
| `ReqSys Agent: Build Local Context` | cria `.reqsys/index.json` |
| `ReqSys Agent: Ask Local Context` | pergunta ao índice local por palavra-chave |
| `ReqSys Agent: Semantic Ask Local Context` | pergunta ao índice local com ranking TF-IDF/cosseno |

## Segurança operacional

O leitor de workspace:

- usa somente caminhos permitidos por configuração;
- ignora binários;
- ignora arquivos grandes;
- bloqueia diretórios técnicos pesados;
- bloqueia nomes sensíveis conhecidos;
- opera em modo `safe-readonly`;
- não usa LLM nesta fase;
- não usa serviço externo nesta fase.

A frente de runtime/deploy:

- não publica produção sem evidência de CI;
- não informa URL pública sem smoke test validado;
- exige healthcheck antes de promoção;
- exige rollback documentado;
- gera artifact de evidência no workflow de readiness;
- gera artifact de evidência no workflow de container;
- mantém produção bloqueada em caso de violação de Auth, CORS, JWT, secrets, PII ou auditoria.

## Roadmap enxuto

| Fase | Entrega |
|---|---|
| 0.1 | CLI + extensão + config plugável |
| 0.2 | Workspace Reader + Local Context Index |
| 0.3 | Busca semântica local leve |
| 0.4 | Contrato de runtime público/deploy |
| 0.5 | Workflow de readiness de deploy com artifact |
| 0.6 | Artefato/container de runtime com evidência |
| 0.7 | Deploy público controlado + smoke HTTP |
| 0.8 | LlamaIndex/Ollama opcional |
| 0.9 | Sugestão de patch assistida |
