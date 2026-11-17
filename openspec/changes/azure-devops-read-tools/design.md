# Design

## Context

Ver [proposal.md](./proposal.md). A change de fundação (`azure-devops-plugin-core`)
já entrega config, PAT, cliente HTTP, envelope `ok/data`, paginação
normalizada e roteamento de host. Esta change só **consome** essa base.

O MCP `azure-devops-connector` (Bun/TS, em `hub/workflow/tools/azure-devops`) é a
referência de paridade: 23 tools de leitura/escrita já testadas contra a API
real. O MCP **não é tocado** — a reimplementação é do zero em Python.

## Goals / Non-Goals

**Goals:**
- Cobrir as 23 tools de leitura do MCP + as extensões decididas na pesquisa.
- Preservar as armadilhas já resolvidas no MCP (paging de builds, definition por
  nome, dois formatos de `changes`).
- Manter o modelo capaz de escolher a tool certa: nomes e descrições precisos.

**Non-Goals:**
- Qualquer escrita (change seguinte).
- `/ado-help`, skills, README, CI (change de help/distribuição).
- Nuances do modelo de PR (draft, reviewers, policies de branch) — são escritas.

## Decisions

### Um módulo por domínio, na raiz do plugin
`tools_projects.py`, `tools_builds.py`, `tools_pull_requests.py`,
`tools_work_items.py`, `tools_wiki.py`, `tools_git.py`,
`tools_artifacts.py`, `tools_identity.py`, `tools_policies.py`,
`tools_releases.py`. Cada módulo exporta `TOOLS` (lista de `ToolSpec`) e
`registry.py` concatena. O loader do Hermes pré-carrega `*.py` irmãos da raiz
como módulos do pacote, então imports relativos funcionam sem subpacotes.

*Alternativa*: um `tools.py` gigante — rejeitada (600+ linhas, diff ilegível
por domínio).

### Handlers como funções `(args: dict, **kwargs) -> str`
Cada handler monta a requisição, chama o cliente e devolve
`json.dumps({"ok": True, "data": ...})`; em caso de `AdoError` devolve o
envelope de erro. Um helper `run(fn)` (em `errors.py` ou `toolkit.py`)
encapsula o try/except para todos os handlers, garantindo que nenhuma exceção
escape.

### Normalização de resposta por tool, não genérica
Cada tool decide o que é útil para o modelo (ex.: listar builds devolve
`definition` como `{id, name}`, sem o payload inteiro da definition). A
normalização genérica do MCP (`formatBuild`, `formatProject`) é reproduzida
1:1 onde já existe — divergir só cria bug.

### Paginação: `continuationToken` de entrada e saída
Toda listagem aceita `continuationToken` e devolve o próximo. Para builds, o
token vem do header `x-ms-continuationtoken`; para as demais APIs, do corpo.

### Parâmetros de projeto e repositório
`project` é obrigatório por padrão (o MCP exige) e aceito por nome ou id;
`repositoryId` é opcional nas tools de PR/wiki quando a organização tem um
único repositório de código — a API resolve. `default_project` (setting) é o
fallback quando o modelo não informa projeto: o plugin preenche antes de
chamar a API, sem mudar o que o modelo pediu.

### Identidade autenticada
`azure_devops_get_my_identity` usa `GET /_apis/connectionData` (o mesmo
endpoint que o MCP usa para descobrir o `reviewerId`). A tool de leitura
expõe o dado; a identidade autenticada será reutilizada pelas tools de escrita.

### Releases no host `vsrm`
O cliente já roteia `/_apis/release/` para `vsrm.dev.azure.com`
(verificado na pesquisa: a rota de release não existe em `dev.azure.com`);
a tool só monta o path com `{org}/{project}`.

### Sem `top` arbitrário e sem teto de saída
A decisão da pesquisa é não impor teto: o modelo controla o volume com `top`
quando quiser. As tools que o MCP já limitava (`top` ≤ 5000 em builds) mantêm
o limite blando documented, sem truncar resposta.

### Testes por tool com `MockTransport`
Cada tool tem ao menos um cenário de sucesso e um de erro (404/403) com o
transporte falso — sem rede, sem PAT.

## Endpoints verificados (2026-11-17, API real)

Verificação feita na fase de planejamento, contra a organização de referência, com
PAT de produção (escopos mínimos) e um PAT temporário de escopo total. As duas
credenciais pertencem ao mesmo usuário — a diferença de resultado entre elas
**é** a diferença de escopo. Resultado por rota:

| Rota | Código | Nota de contrato |
|---|---|---|
| `GET /{org}/_apis/projects` | 200 | 14 projetos |
| `GET /{org}/{project}/_apis/git/repositories` | 200 | 3 repos |
| `GET .../git/repositories/{repoId}/refs` (+ `filter=heads|tags`) | 200 | |
| `GET .../refs/heads/{branch}` | 200 | |
| `GET .../commits` | 200 | 23 commits; `$top` funciona, `top` **é ignorado** |
| `GET .../commits?branch={nome}` | 200 | o branch é o **nome curto** (`master`); `refs/heads/master` devolve **404** |
| `GET .../commits/{commitId}` | 200 | |
| `GET /{org}/_apis/wit/workitems/{id}` (+ `fields`) | 200 | |
| `POST /{org}/{project}/_apis/wit/wiql` | 200 | 620 itens; **sem corpo** devolve 411; `GET` na mesma rota devolve 405 |
| `GET /{org}/_apis/wiki/wikis` | 200 | lista **por organização** |
| `GET /{org}/{project}/_apis/wiki/wikis` | 200 | lista do projeto (vazia neste projeto) |
| `GET /{org}/{project}/_apis/wiki/wikis/{wikiId}/pages` | 200 | **o projeto do path precisa ser o dono da wiki** (vem do `remoteUrl`); com outro projeto: 404 `WikiNotFoundException` |
| `GET .../pages?path=/Home` | 404 | página inexistente (mensagem explícita da API) |
| `GET /{org}/{project}/_apis/build/definitions` | 200 | |
| `GET /{org}/{project}/_apis/build/builds` | 200 | o paging usa **`$top`**; o token volta no header `x-ms-continuationtoken` |
| `GET .../builds/{id}/changes` | 200 | envelope `{count, value}` |
| `GET .../builds/{id}/timeline` | 200 | envelope `{records}` |
| `GET .../builds/{id}/artifacts` | 200 | lista vazia nesse build (rota ok) |
| `GET /{org}/_apis/connectionData` | 200 | **sem** `api-version`; com `api-version=7.1` devolve **400** (exige `-preview`). O MCP fixa `7.0-preview.1` nesta org |
| `GET /{org}/{project}/_apis/policy/configurations` | 200 | **é a rota de policies viável com PAT** |
| `GET /{org}/{project}/_apis/policies/repositories/{repoId}` | **401** (PAT mínimo) / **404** (PAT full) | **não é alcançável com PAT clássico** — rota resolve, mas a autorização do serviço de policies recusa o PAT |
| `GET .../git/repositories/{repoId}/pullrequests` | 200 | filtro `status`, `$top` |
| `GET .../pullRequests/{id}` | 200 | |
| `GET .../pullRequests/{id}/threads` | 200 | 3 threads |
| `GET .../pullRequests/{id}/labels` | 200 | `{count, value}` |
| `GET .../pullRequests/{id}/reviewers` | 200 | |
| `GET .../git/repositories/{repoId}/labels` | **404** | label é conceito de PR; repositório não tem essa rota |
| `GET vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions` | 200 | `{count, value}` |
| `GET vsrm.dev.azure.com/{org}/{project}/_apis/release/releases` | 200 | `{count, value}` |

Três conclusões que mudam o desenho:

1. **Policies de repositório saem do escopo do v1.** A rota existe, mas um PAT
   clássico não a acessa (401 com escopo mínimo, 404 com escopo total — o
   serviço de policies não autoriza PAT). O que funciona é
   `policy/configurations` (as definições de policy do projeto), que responde
   200 com PAT mínimo. A tool de policies passa a ler **policy configurations**
   do projeto.
2. **A versão de API é por endpoint.** `connectionData` exige versão preview
   (`7.0-preview.1` nesta organização; `7.1` devolve 400). O cliente precisa
   de uma tabela de override por endpoint, com `7.1` como default.
3. **Paging e filtros têm nomes específicos.** Builds paginam por `$top` +
   header `x-ms-continuationtoken` (o param `top` sem cifrão é **ignorado** —
   uma paginação silenciosamente quebrada); commits aceitam o branch como nome
   curto (`refs/heads/x` devolve 404); wiki exige o projeto dono da wiki.

Escopos de escrita (`POST`/`PATCH`/`PUT`/`DELETE`) **não** foram exercitados
contra a API real: a verificação foi apenas leitura, para não sujar a organização
de referência. A paridade de escrita continua coberta pelo MCP em produção.

## Risks / Trade-offs

- [Divergência de paridade com o MCP] → a lista de tools é conferida item a item
  contra `src/tools.ts` do MCP antes do merge (tarefa de verificação).
- [API `wit/wiql` só aceita POST] → o cliente expõe POST explicitamente; teste
  cobre o método.
- [Retorno enorme em `get_build_timeline`] → a tool aceita `top` e devolve o
  timeline bruto; o modelo é instruído a filtrar.
- [Identidade e `reviewerId` divergem entre PATs] → a tool de escrita de voto
  resolve a identidade autenticada no momento da chamada (change seguinte).
- [Campos de work item vary por tipo] → o default é um conjunto mínimo
  (id/tipo/título/estado) e `fields` permite pedir outros.

## Migration Plan

Nenhuma (plugin novo). Rollback: remover o pacote.

## Open Questions

(nenhuma que afete specs ou tasks)
