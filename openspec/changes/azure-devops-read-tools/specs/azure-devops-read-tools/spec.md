# Spec Delta

## Purpose

Especificar a superfície de **leitura** do Azure DevOps exposta ao agente:
quais tools existem, o que cada uma devolve, como filtra e como sinaliza
projeto/repositório inexistente, paginação e erros — sempre dentro do envelope
definido em `azure-devops-plugin-core`.

## ADDED Requirements

### Requirement: O agente localiza projetos e repositórios
O plugin SHALL expor `azure_devops_list_projects` e
`azure_devops_get_project` (organização, id, nome, estado, descrição) e
`azure_devops_list_repositories` e `azure_devops_get_repository` (id, nome,
url, tamanho, branch padrão), aceitando o projeto por nome ou id e devolvendo
`not_found` quando o objeto não existe.

#### Scenario: Lista de projetos da organização
- **WHEN** o modelo chama `azure_devops_list_projects`
- **THEN** recebe a lista de projetos com id, nome e estado, e o
  `continuationToken` quando houver mais páginas

#### Scenario: Projeto inexistente
- **WHEN** o modelo pede `azure_devops_get_project` com um nome que não existe
- **THEN** a resposta é `{"ok": false, "error": {"code": "not_found", ...}}`

#### Scenario: Projeto por id
- **WHEN** o modelo informa o id do projeto em vez do nome
- **THEN** a API é chamada com o id e a resposta é a mesma do caminho por nome

### Requirement: O agente consulta builds e definições de pipeline
O plugin SHALL expor `azure_devops_list_build_definitions`,
`azure_devops_list_builds`, `azure_devops_get_build`,
`azure_devops_get_build_changes` e `azure_devops_get_build_timeline`.
`azure_devops_list_builds` SHALL aceitar filtro por status
(`all|cancelling|completed|inProgress|none|notStarted|postponed`), por
definition (id **ou** nome, com o nome resolvido para id antes da chamada) e
`top`; o resultado SHALL carregar o `continuationToken` da página seguinte.

#### Scenario: Filtro por status
- **WHEN** o modelo pede apenas builds `completed`
- **THEN** a API é chamada com `statusFilter=completed` e a resposta traz
  somente builds concluídos

#### Scenario: Definition por nome
- **WHEN** o modelo passa o nome `ci-main` em `definition`
- **THEN** o plugin resolve o id da definition antes de listar os builds

#### Scenario: Continuação de builds
- **WHEN** a API responde com `x-ms-continuationtoken`
- **THEN** a resposta traz esse token em `continuationToken`, que pode ser
  reenviado para a próxima página

#### Scenario: Changes com dois formatos de resposta
- **WHEN** a API de changes devolve um array puro ou um envelope `{value: [...]}`
- **THEN** o plugin devolve a lista de changes no mesmo formato nos dois casos

### Requirement: O agente consulta pull requests e seus metadados
O plugin SHALL expor `azure_devops_list_pull_requests` (filtro de status
`active|abandoned|completed|all`), `azure_devops_get_pull_request`,
`azure_devops_list_pull_request_comments` e
`azure_devops_list_pull_request_labels`, com o repositório opcional quando a
organização tem um único repositório de código.

#### Scenario: Listagem por status
- **WHEN** o modelo pede PRs `active`
- **THEN** a API é chamada com `searchCriteria.status=active`

#### Scenario: Comentários de um PR
- **WHEN** o modelo pede os comentários de um PR
- **THEN** recebe as threads de comentário com autor, texto, status e data

### Requirement: O agente consulta work items e WIQL
O plugin SHALL expor `azure_devops_query_wiql` (consulta WIQL com projeto
opcional e `top`), `azure_devops_get_work_item` (id, tipo, campos, campos
customizados) e `azure_devops_list_work_items` (filtro por tipo e ids),
sempre devolvendo os campos pedidos ou, por default, um conjunto reduzido
(id, tipo, título, estado).

#### Scenario: Consulta WIQL
- **WHEN** o modelo envia uma consulta WIQL
- **THEN** o plugin envia a consulta e devolve os ids dos work items
  encontrados, respeitando `top`

#### Scenario: Work item inexistente
- **WHEN** o modelo pede um id de work item inexistente
- **THEN** a resposta é `not_found`

### Requirement: O agente consulta wiki, refs git, artefatos, identidades e políticas
O plugin SHALL expor `azure_devops_list_wikis`, `azure_devops_list_wiki_pages`,
`azure_devops_get_wiki_page`, `azure_devops_list_branches`,
`azure_devops_get_branch`, `azure_devops_list_commits`,
`azure_devops_get_commit`, `azure_devops_list_tags`,
`azure_devops_list_build_artifacts`, `azure_devops_get_my_identity`,
`azure_devops_list_identities`, `azure_devops_list_policies`.

#### Scenario: Página de wiki
- **WHEN** o modelo pede a página `/Home` de uma wiki
- **THEN** recebe o conteúdo e a data da última alteração

#### Scenario: Artefatos de um build
- **WHEN** o modelo pede os artefatos de um build
- **THEN** recebe nome, tamanho e url de download de cada artefato

#### Scenario: Policy configurations do projeto
- **WHEN** o modelo pede as policies do projeto
- **THEN** recebe as policy configurations (expiracao de branch, revisao minima) do projeto

#### Scenario: Policy por repositorio nao e exposta
- **WHEN** o usuario procura uma policy por repositorio
- **THEN** a tool informa que essa leitura nao e alcancavel com PAT e devolve as
  policy configurations do projeto como equivalente

#### Scenario: Identidade autenticada
- **WHEN** o modelo chama `azure_devops_get_my_identity`
- **THEN** recebe o id e o display name do usuário dono do PAT

### Requirement: O agente consulta releases no host de Release Management
O plugin SHALL expor `azure_devops_list_release_definitions`,
`azure_devops_list_releases` e `azure_devops_get_release`, sempre no host
`vsrm.dev.azure.com` e sempre com o segmento da organização **e** do projeto
no path.

#### Scenario: Definitions de release
- **WHEN** o modelo pede as definitions de release de um projeto
- **THEN** a requisição vai para `vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions`

#### Scenario: Release inexistente
- **WHEN** o modelo pede uma release inexistente
- **THEN** a resposta é `not_found`

### Requirement: As tools de leitura são discoveríveis pelo modelo
Cada tool de leitura SHALL ter descrição precisa com o que faz e quando usar,
parâmetros documentados e `check_fn` apontando a credencial, e o manifesto
SHALL listar exatamente as tools registradas.

#### Scenario: Manifesto em sincronia
- **WHEN** a suíte roda
- **THEN** `provides_tools` do manifesto é idêntico à lista do registro

#### Scenario: Tool marcada como needing auth
- **WHEN** o PAT não está disponível
- **THEN** o Hermes marca a tool como "needs auth" em vez de falhar na listagem
