# Spec Delta

## Purpose

Filtrar a atividade do painel desktop e as listagens do agente por data (presets
7/30/90 dias, default 7) e por projetos ignorados (persistentes no config do perfil),
com links clicáveis e datas nos payloads — para que o usuário veja só o que importa
e consiga abrir o item no Azure DevOps.

## ADDED Requirements

### Requirement: Filtro de data com presets
O painel SHALL aceitar um período de busca com presets **7, 30 e 90 dias** e default
**7 dias**, aplicado às listagens de pull requests, work items e builds. O backend
SHALL expor o período como parâmetro `days` na rota `/overview`.

#### Scenario: Default de 7 dias
- **WHEN** o painel abre sem escolher período
- **THEN** o `/overview` é chamado com `days=7` e os itens têm menos de 7 dias

#### Scenario: Preset 90 dias
- **WHEN** o usuário escolhe o preset de 90 dias
- **THEN** o `/overview` é refeito com `days=90` e itens de até 90 dias aparecem

### Requirement: Filtro de data de PRs é server-side
Para pull requests, o backend SHALL aplicar o filtro de data como
`searchCriteria.minTime` na chamada à API do Azure DevOps (filtro verificado
funcionando contra a API real).

#### Scenario: PRs antigos não são buscados
- **WHEN** `days=7`
- **THEN** a chamada à API inclui `searchCriteria.minTime` com a data de corte e a
  resposta não contém PRs anteriores ao corte

### Requirement: Filtro de data de builds é client-side no backend
A API de builds **ignora** filtros de data nos query params (comportamento
verificado: `minFinishTime` devolve os mesmos resultados com e sem o filtro). O
backend SHALL buscar os builds mais recentes (`$top`) e aplicar o corte de data
**após a busca**, filtrando por `finishTime` ou `queueTime`.

#### Scenario: Builds antigos são descartados após a busca
- **WHEN** `days=7` e a busca traz builds de julho e outubro
- **THEN** o painel recebe somente builds cuja data é dentro do período

#### Scenario: O filtro não vira parâmetro quebrado
- **WHEN** o backend monta a chamada de builds
- **THEN** nenhum parâmetro de data viaja na query (o comportamento silencioso da API
  é documentado em `docs/ado-endpoints.md`)

### Requirement: Ferramentas do agente aceitam filtro de dias
As tools `azure_devops_list_pull_requests` e `azure_devops_list_builds` SHALL aceitar
o parâmetro opcional `days` (default 7), com a mesma semântica: server-side para PRs,
pós-filtro para builds.

#### Scenario: Agente pede builds dos últimos 30 dias
- **WHEN** o modelo chama `azure_devops_list_builds` com `days=30`
- **THEN** a resposta contém somente builds dentro do período

### Requirement: Projetos ignorados persistentes
O plugin SHALL expor a setting `ignored_projects` (lista de nomes ou ids de projeto)
em `config_schema`, persistida no `config.yaml` do perfil. O backend do painel SHALL
**pular projetos ignorados antes de chamar a API** (nem PRs, nem WIQL, nem builds desses
projetos são buscados).

#### Scenario: Projeto ignorado não gera chamadas
- **WHEN** `ignored_projects` contém "Projeto X" e o painel carrega
- **THEN** nenhuma chamada de PR, WIQL ou build é feita para "Projeto X"

#### Scenario: Lista vazia é o default
- **WHEN** `ignored_projects` não está configurada
- **THEN** todos os projetos são varridos (comportamento atual preservado)

### Requirement: Projetos ignorados são apenas visuais
Os itens de projetos ignorados SHALL **não** ser escondidos das tools do agente:
`list_projects` SHALL devolver todos os projetos com um campo informativo
`ignored: true|false`, e as tools de conteúdo (PRs, work items, builds de um projeto
ignorado) SHALL continuar funcionando quando consultadas explicitamente.

#### Scenario: Agente lista projetos com o campo informativo
- **WHEN** o agente chama `list_projects` com projetos ignorados configurados
- **THEN** todos os projetos aparecem, com `ignored: true` nos ignorados

#### Scenario: Conteúdo de projeto ignorado continua acessível
- **WHEN** o agente pede PRs ou work items de um projeto ignorado explicitamente
- **THEN** a tool responde normalmente (o filtro é visual, não de acesso)

### Requirement: Links clicáveis nos payloads do painel
O backend SHALL devolver a **URL web** de cada item do painel (`pullRequests`,
`workItems`, `builds`), no formato que abre o Azure DevOps no navegador
(`https://dev.azure.com/{org}/{project}/…`).

#### Scenario: PR tem URL web
- **WHEN** o painel lista um pull request
- **THEN** o item carrega `url` apontando para a página do PR no Azure DevOps

#### Scenario: Build tem URL web
- **WHEN** o painel lista um build
- **THEN** o item carrega `url` apontando para a página de resultados do build

### Requirement: Datas nos payloads do painel
O backend SHALL devolver a data relevante de cada item (`createdAt` para PRs,
`changed` para work items, `finishedAt`/`queuedAt` para builds) em formato ISO 8601.

#### Scenario: Idade do item é visível
- **WHEN** o painel lista itens
- **THEN** cada item carrega a data em ISO 8601, para a UI mostrar "há 2 dias"
