# Proposal

## Why

O painel `/azure-devops` funciona, mas é uma única tela com três seções empilhadas,
texto puro e sem navegação: não dá para saber a que projeto/época cada item pertence,
nada é clicável e o único jeito de ver algo no Azure DevOps é sair do Hermes. A change
`azure-devops-panel-filters` entrega os dados (datas, URLs, filtros); esta change
transforma isso em **interface**.

## What Changes

- **Abas** na página `/azure-devops`: Pull Requests, Work Items, Builds e Releases —
  uma seção por aba, com contadores no título da aba.
- **Presets de período** (7/30/90 dias, default 7) alimentando o `days` do backend.
- **Seletor de projetos** com checkbox, alimentando a setting `ignored_projects`
  (persistida no `config.yaml` do perfil via `hermes config set` — ou leitura direta
  quando o painel roda no mesmo processo).
- **Links clicáveis** em todas as linhas: abre o item no Azure DevOps no navegador via
  `ctx.os.openExternal`.
- **Datas relativas** ("há 2 dias") calculadas dos ISO 8601 do backend.
- **Badges de cor** por estado (PR draft/open/merged, build succeeded/failed/in progress,
  work item state) usando `var(--ui-*)`.
- **Busca por texto** dentro da aba ativa (filtra por título).
- **Refresh manual** + "atualizado há Xs" (o polling de 15s continua; o refresh força).
- **Notificações nativas** (`ctx.os.notify`) quando um build do usuário falha, só
  quando o usuário está away (o SDK já bloqueia em uso) e com dedupe por build id.
- **Estados vazios acionáveis** ("nenhum PR aberto" + botão "abrir no Azure DevOps").

## Capabilities

### New Capabilities
- `azure-devops-panel-ui`: a experiência da página `/azure-devops` — abas com
  contadores, presets de período, seletor de projetos ignorados, busca, links externos,
  datas relativas, badges de estado, refresh manual, notificação de build falho e
  estados vazios acionáveis.

### Modified Capabilities
- `azure-devops-panel-filters` (spec irmã desta mesma entrega): a UI é o consumidor
  dos filtros e payloads definidos lá; nenhuma mudança de contrato.

## Impact

- **`desktop/plugin.js`**: reescrita da página (hooks, abas, filtros, busca) — mesmo
  formato ESM sem build, `jsx()` de `react/jsx-runtime`, `var(--ui-*)`,
  `ctx.setInterval`.
- **`dashboard/plugin_api.py`**: rota `/releases` nova (lista as releases do
  usuário — a única seção que o `/overview` ainda não cobre).
- **Sem mudança** nas tools do agente nem nos contratos da change irmã.
