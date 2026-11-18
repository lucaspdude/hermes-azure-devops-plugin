# Proposal

## Why

O painel desktop `/azure-devops` hoje carrega **sem nenhum filtro**: varre os 14+ projetos
da organização a cada ciclo, lista tudo sem ordem de data e sem links para o Azure DevOps.
Com a organização real (14 projetos), cada atualização de 15 segundos gera dezenas de
chamadas à API — e a maior parte do resultado é ruído para o usuário (projetos que ele não
usa, itens com meses de idade, nada clicável).

O agente sofre do mesmo: `list_pull_requests`, `list_builds` e `query_wiql` não
expõem filtro de data, então o modelo lista tudo e interpreta "recente" por conta própria.

## What Changes

- **Projetos ignorados** (novo): setting `plugins.entries.azure-devops.settings.ignored_projects`
  (lista de ids/nomes). O backend do painel e as tools de listagem **pulam esses projetos
  antes de chamar a API** (economia real de chamadas). Os itens não são escondidos do
  agente por outra via — `list_projects` continua devolvendo todos, agora com um campo
  `ignored` informativo; o agente decide. (Decisão do usuário: efeito **apenas visual**
  no painel; as tools continuam acessando os projetos ignorados normalmente.)
- **Filtro de data** (novo): preset de **7 dias por padrão** nas listagens de PRs, builds e
  work items do painel e nas tools `list_pull_requests` e `list_builds` (novo parâmetro
  `days`, presets 7/30/90 no painel).
  - **PRs**: filtro server-side `searchCriteria.minTime` (verificado contra a API real).
  - **Builds**: a API **ignora** `minFinishTime` nos query params (verificado: devolve os
    mesmos resultados com e sem o filtro) — o filtro de data de builds é aplicado **no
    backend** (busca os N mais recentes e filtra por `finishTime`/`queueTime`).
- **Links clicáveis** (novo): toda resposta do painel passa a carregar a URL web do objeto
  (`url`), para o app abrir o Azure DevOps no navegador via `ctx.os.openExternal`.
- **Dates nos payloads** (novo): `createdAt`/`finishedAt`/`updated` nos itens do painel,
  para o usuário ver idade dos itens e o filtro fazer sentido visualmente.

## Capabilities

### New Capabilities
- `azure-devops-panel-filters`: filtros de data (7/30/90, default 7), projetos ignorados
  persistentes no config do perfil, links clicáveis e datas nos payloads do painel; filtro
  de data e de projetos ignorados respeitado pelas tools de listagem do agente.

### Modified Capabilities
- `azure-devops-plugin-core`: `config_schema` ganha a setting `ignored_projects`
  (lista); `list_projects` passa a devolver o campo `ignored` informativo por projeto.

## Impact

- **Backend do painel** (`dashboard/plugin_api.py`): `/overview` ganha `?days=7`,
  pula projetos ignorados, devolve `url` e datas nos itens.
- **Tools** (`tools_pull_requests.py`, `tools_builds.py`): novo parâmetro `days`
  (server-side para PRs, client-side para builds — a API ignora `minFinishTime`).
- **`config.py`**: `ignored_projects` (lista, default vazio) e `default_days` (int, 7).
- **`plugin.yaml`**: `config_schema` com as duas novas settings.
- **Manifesto**: `list_projects` devolve campo novo (`ignored`) — sem breaking change.
- **Fora de escopo**: UI/UX (abas, badges, busca, notificações) — change
  `azure-devops-panel-ui`, que consome os dados enriquecidos desta change.
