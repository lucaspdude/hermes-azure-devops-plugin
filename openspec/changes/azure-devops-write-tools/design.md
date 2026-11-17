# Design

## Context

Ver [proposal.md](./proposal.md). A base (config, PAT, cliente HTTP, envelope,
paginação) vem da change `azure-devops-plugin-core`; a leitura vem de
`azure-devops-read-tools`.

O MCP `azure-devops-connector` já implementa as escritas de PR em TypeScript e
serve de referência de paridade (o MCP **não é tocado**).

## Goals / Non-Goals

**Goals:**
- Escrever com segurança: identidade correta, sem contornar políticas da
  organização e sem repetir a operação em caso de erro.
- Preservar a paridade de escrita do MCP e estender para work item, wiki e
  enfileiramento de build.

**Non-Goals:**
- Idempotência de escrita (retry seguro) — ver riscos.
- Aprovações automáticas, bypass de policies, merge automático.
- Criação de branch, tags, release, pipelines (não há equivalente no MCP nem
 需求 na pesquisa).

## Decisions

### Vote sempre no usuário autenticado, resolvido em tempo de chamada
`azure_devops_approve/reject/reset_pull_request_vote` resolve
`authenticatedUser.id` via `GET /_apis/connectionData` antes do `PUT`
(vote 10/5/0). Resolver em tempo de chamada (e não cachear) evita que um PAT
trocado no perfil continue votando como o usuário anterior.

*Alternativa*: aceitar `reviewerId` do modelo — rejeitada (o modelo erraria a
identidade e o voto sairia 403 ou, pior, em nome de outra pessoa).

### Sem retry em escrita
Erro de escrita é devolvido ao modelo, que decide o que fazer. Repetir um
`POST` de criação de PR pode duplicar o PR.

*Alternativa*: retry idempotente por chave — a API do Azure DevOps não oferece
chave de idempotência para criação de PR; custo alto, benefício baixo.

### Operations JSON Patch para work items
Atualização de work item usa a API de patch (`PATCH /_apis/wit/workitems/{id}`
com `[{op, path, value}]`), que é a forma nativa de editar campos e evita
PUT de objeto completo (que sobrescreveria campos não informados). O patch
aplicado é devolvido no `data` da resposta.

### Wiki: criar vs. atualizar são tools distintas
Criar e atualizar páginas são operações diferentes na API (a atualização exige
a página existir); duas tools explícitas são mais previsíveis para o modelo do
que uma tool com flag `create-or-update` e semântica de "upsert".

### Enfileirar build resolve a definition por nome
`azure_devops_queue_build` aceita `definition` como nome ou id e resolve o
id antes do `POST /builds`, como `azure_devops_list_builds` já faz.

### Módulos de escrita separados dos de leitura
`tools_pull_request_writes.py`, `tools_work_item_writes.py`,
`tools_wiki_writes.py`, `tools_build_writes.py` — para que uma mudança de
comportamento de escrita não toque o diff de leitura. Nomes com sufixo
`_writes` são explicitamente disliked, mas ficam explícitos na raiz e não
colidem com os módulos de leitura.

*Alternativa*: um módulo por domínio misturando leitura e escrita — rejeitada
por misturar Review e Write em diffs pequenos.

### Nenhuma política de aprovação própria
O Hermes já tem o fluxo de aprovação de tools; o plugin **não** implementa
confirmação própria (a regra 12 do catálogo exige respeitar as aprovações
existentes, não inventar outras).

## Risks / Trade-offs

- [Escopo insuficiente do PAT para a escrita pedida] → erro `forbidden` com
  mensagem da API e dica de escopo; a change de help documenta escopo por
  operação.
- [Escrita duplicada em repetição do modelo] → a resposta sempre devolve o id do
  objeto criado, para o modelo deduplicar; sem retry automático.
- [Política de branch bloqueia conclusão] → erro `forbidden` com a mensagem
  original; o plugin não contorna.
- [PATCH de work item parcialmente aplicado] → a API aplica o lote em
  transação; a resposta traz o work item resultante ou o erro.
- [Wiki exige permissão de edição separada] → 403 é reportado como `forbidden`.

## Migration Plan

Nenhuma (plugin novo).

## Open Questions

(nenhuma que afete specs ou tasks)
