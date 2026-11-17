# Proposal

## Why

A change anterior entregou a leitura. Falta a **escrita** — que é onde o
plugin deixa de ser um browser e passa a ser um braço do agente no dia a dia:
abrir PR, comentar, rotular, votar, concluir/abandonar PR, atualizar work item,
editar wiki e enfileirar build. Sem isso o usuário precisa sair do chat para
fazer qualquer ação.

## What Changes

- Entrega as tools de escrita da API do Azure DevOps, prefixadas
  `azure_devops_*`, no mesmo envelope `{"ok": true, "data": ...}`.
- Porta a paridade de escrita do MCP `azure-devops-connector`: criação de PR,
  comentário em thread, labels (adicionar/remover), votos (aprovar/rejeitar/
  resetar), abandono e conclusão de PR.
- Acrescenta escrita fora do MCP: `azure_devops_update_work_item`,
  `azure_devops_create_wiki_page`, `azure_devops_update_wiki_page` e
  `azure_devops_queue_build`.
- Resolve a identidade do usuário autenticado em tempo de chamada (endpoint
  `_apis/connectionData`), requisito do voto em PR (o PAT é de uma pessoa
  específica; votar como outra dá 403).
- Devolve, em toda escrita, o identificador e a URL do objeto afetado, para o
  modelo conseguir conferir o resultado sem uma chamada extra.

## Capabilities

### New Capabilities
- `azure-devops-write-tools`: surface de escrita do Azure DevOps — pull
  requests (criação, comentários, labels, votos, abandono/conclusão), work
  items, wiki e enfileiramento de build.

### Modified Capabilities

(nenhuma)

## Impact

- **Depende de**: `azure-devops-plugin-foundation` (base) e da leitura (`azure-devops-read-tools`, para identidade e definitions).
- **Novo código**: `tools_pull_request_writes.py`, `tools_work_item_writes.py`,
  `tools_wiki_writes.py`, `tools_build_writes.py`, agregados em
  `registry.py`; `plugin.yaml` atualizado.
- **Sistemas externos**: API REST do Azure DevOps, agora com escrita
  (pull requests, work items, wiki, builds).
- **Credenciais**: o PAT precisa dos escopos de escrita correspondentes; a
  surface de ajuda (change seguinte) documenta escopo por operação.
- **Fora de escopo**: políticas de branch customizadas, aprovação automática,
  idempotência de escrita, `/ado-help` e publicação.
