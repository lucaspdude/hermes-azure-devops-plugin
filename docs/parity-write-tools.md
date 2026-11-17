# Paridade das tools de escrita com o MCP azure-devops-connector

Fonte do MCP: `src/tools.ts` (21 tools no total; 11 de escrita). Fonte do
plugin: `registry.TOOLS` (13 tools de escrita nas changes `write-tools`).

## Cobertura das 11 tools de escrita do MCP

| Tool do MCP | No plugin | Diferenca deliberada |
|---|---|---|
| `ado_create_pull_request` | `azure_devops_create_pull_request` | mesmo contrato (source/target/title/description/isDraft/reviewerIds) |
| `ado_add_pull_request_comment` | `azure_devops_add_pull_request_comment` | `commentType: 1` fixo (texto); nova thread ou resposta por `threadId` |
| `ado_add_pull_request_label` | `azure_devops_add_pull_request_label` | aceita label por nome (o plugin resolve) ou por `labelId` |
| `ado_remove_pull_request_label` | `azure_devops_remove_pull_request_label` | aceita nome: o plugin resolve o id antes do DELETE |
| `ado_approve_pull_request` | `azure_devops_approve_pull_request` | `reviewerId` resolvido pelo plugin (identidade do PAT), nunca aceito do modelo |
| `ado_reject_pull_request` | `azure_devops_reject_pull_request` | idem |
| `ado_reset_pull_request_vote` | `azure_devops_reset_pull_request_vote` | idem |
| `ado_abandon_pull_request` | `azure_devops_abandon_pull_request` | mesmo contrato |
| `ado_complete_pull_request` | `azure_devops_complete_pull_request` | `squashMerge`/`deleteSourceBranch` em `completionOptions` |

## Extensoes de escrita do plugin que o MCP nao tem

- `azure_devops_update_work_item` — JSON Patch (op/path/value) no
  `PATCH /_apis/wit/workitems/{id}` com `Content-Type: application/json-patch+json`.
- `azure_devops_create_wiki_page` / `azure_devops_update_wiki_page` — PUT com
  `If-Match` da versao atual (a wiki sempre no projeto dono, resolvido pelo
  `remoteUrl` na listagem).
- `azure_devops_queue_build` — POST `/{project}/_apis/build/builds` com a
  definition resolvida por nome e variaveis opcionais.

## Diferencas deliberadas de comportamento

- **Identidade do voto**: o plugin resolve o `reviewerId` por chamada
  (`/_apis/connectionData`, api-version preview); o MCP faz o mesmo, mas o
  plugin **nao** aceita `reviewerId` do modelo.
- **Sem retry**: nenhuma escrita e repetida (um create repetido abriria um
  segundo PR).
- **Conflito de versao**: 412/precondition cai no envelope de erro com a
  mensagem da API, sem nova tentativa.
