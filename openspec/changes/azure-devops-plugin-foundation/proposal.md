# Proposal

## Why

O repositório `hermes-azure-devops-plugin` está vazio: não existe plugin Hermes
que permita ao agente operar Azure DevOps (projetos, repositórios, builds, pull
requests, work items). Sem uma fundação comum — manifesto, configuração,
credencial, cliente HTTP e contrato de erro — qualquer tool seria uma
implementação isolada repetindo autenticação, paginação e tratamento de erro.

## What Changes

- Cria o pacote do plugin nativo (Python) no formato aceito pelo Hermes:
  `plugin.yaml` + `__init__.py` com `register(ctx)`.
- Declara o manifesto com `manifest_version: 2`, `requires_hermes`,
  `requires_env` (PAT do Azure DevOps, formato rico) e `config_schema` com as
  settings visíveis ao usuário (organização, base URL, api-version, projeto
  padrão, timeout).
- Centraliza a lista de tools em **um registro único** (`registry.py`), que é a
  fonte de verdade do manifesto e do `register(ctx)` — elimina divergência
  entre `provides_tools` e as tools registradas (regra 6 do catálogo).
- Implementa o cliente HTTP sobre `httpx`: auth Basic com PAT lido por
  `agent.secret_scope.get_secret`, timeout explícito, **sem retry**, seleção de
  host (`dev.azure.com` / `vsrm.dev.azure.com` para Release Management) e
  paginação normalizada em um único campo `continuationToken`.
- Define o contrato de resposta das tools: sempre JSON string, sucesso
  (`{"ok": true, "data": ...}`) ou erro (`{"ok": false, "error": {...}}`) com
  taxonomia de códigos acionável.
- Entrega o harness de testes offline (transporte HTTP falso) para que as tools
  seguintes nasçam testáveis sem rede e sem PAT.

## Capabilities

### New Capabilities
- `azure-devops-plugin-core`: manifesto, configuração, resolução de credencial,
  cliente HTTP, contrato de erro, paginação e disciplina de registro de tools do
  plugin Azure DevOps.

### Modified Capabilities

(nenhuma — ainda não há specs neste repositório)

## Impact

- **Novo código**: pacote do plugin (raiz do repositório), `plugin.yaml`,
  `__init__.py`, módulos `registry.py`, `config.py`, `auth.py`, `client.py`,
  `errors.py`, `pagination.py`, `testing.py` (fake transport) e suíte de
  testes.
- **Dependências**: `httpx` (já é dependência do core do Hermes — não entra em
  `python_dependencies`).
- **Sistemas externos**: nenhum nesta change. As chamadas de rede só existem a
  partir da change das tools de leitura; a foundation sozinha não fala com a
  rede.
- **Fora de escopo**: as tools em si (mudam nas changes seguintes), a
  meia desktop, a publicação no catálogo oficial e qualquer UX no app.
