# Design

## Context

Ver proposal.md. Os dados enriquecidos (datas ISO, `url` por item, `days`, `ignored_projects`)
vêm da change irmã `azure-devops-panel-filters` — esta change é **só interface** sobre
esses payloads, mais a rota `/releases` que falta no backend.

Referências de padrão no código: `autorag/desktop/plugin.js` (hooks + panes +
statusbar chip), `crew/desktop/plugin.js` (dashboard com abas internas no renderer).
Restrições do SDK confirmadas: ESM sem build, `jsx()` de `react/jsx-runtime`,
`var(--ui-*)`, `ctx.setInterval`, `ctx.os.notify`/`openExternal`,
`ctx.registerSettingsPage` com `children` para sub-páginas.

## Goals / Non-Goals

**Goals:**
- Quatro abas com contadores, presets 7/30/90, seletor de projetos ignorados.
- Toda linha clicável para o Azure DevOps; datas relativas; badges de estado.
- Busca local, refresh manual com idade, notificação nativa de build falho (dedupe).
- Estados vazios acionáveis.

**Non-Goals:**
- Alterar contratos do backend além da rota `/releases` (a change irmã cobre).
- Notificar PRs/work items (só build falho — o ruído de PR é alto e o usuário já vê o badge).
- Edição inline de work items no painel (escrita segue pelo agente).
- Preview HTML de conteúdo (a página é lista + link, não viewer).

## Decisions

### Abas como estado interno do componente, não sub-rotas
A navegação por abas fica em `useState('prs')` dentro do `Panel` — não são rotas
novas do `ROUTES_AREA`. A rota única `/azure-devops` continua sendo o destino do
chip/sidebar; abas internas evitam fragmentar o deep-link e o histórico.

*Alternativa*: quatro rotas (`/azure-devops/prs` etc.) — rejeitada: o chip aponta para
a página e a aba ativa é preferência de sessão, não endereço.

### Persistência de preferências: `localStorage` do renderer
A aba ativa e o preset de período ficam em `localStorage` sob chaves
`azure-devops.tab`/`azure-devops.days` — sobrevivem a reload do app e não exigem
backend. **Projetos ignorados NÃO ficam aqui**: é estado de configuração compartilhado
com o agente, gravado na setting do perfil via `hermes config set` pelo backend (rota
`POST /settings/ignored-projects` que o backend executa com `hermes_cli.config`).

*Alternativa*: guardar tudo no backend — rejeitada para aba/preset (preferência de
dispositivo) e aceita para projetos ignorados (preferência da organização/pessoa,
compartilhada com as tools).

### Seletor de projetos ignorados grava via backend
A UI lista os projetos (do `/overview`) com checkbox; ao aplicar, chama
`POST /settings/ignored-projects` com a lista; o backend executa
`hermes config set plugins.entries.<id>.settings.ignored_projects <json>` no perfil
ativo e responde o estado gravado. O backend é quem pode escrever config com segurança
(o renderer não tem acesso ao `hermes_cli.config`).

### Presets de período fixos: 7/30/90, sem custom
Três presets, default 7. Custom de data inicial/final fica de fora: o custo de UI
(calendário, validação) e o ganho marginal não compensam para o uso diário; a rota
aceita `days` arbitrário se o modelo precisar.

### Builds: filtro de data client-side no backend (fato da API)
`minFinishTime` é ignorado pela API (verificado). O backend busca os N mais recentes e
corta por data. A UI só repassa `days`.

### Badges com `var(--ui-*)` e texto do estado
Cores semânticas mapeadas: succeeded/open → `var(--ui-success)` (com fallback
`--ui-text` se não existir), failed/rejected → `var(--ui-danger)`, inProgress →
`var(--ui-warning)`, draft/abandoned → `var(--ui-text-secondary)`. O texto do badge é
sempre o estado cru da API (sem tradução) para bater com o que o usuário vê no ADO.

### Notificação de build falho: dedupe em `ctx.state`
O conjunto de build ids já notificados fica em memória do plugin (`Set`) + `ctx.state`
para sobreviver a reload; `ctx.os.notify` dispara só quando o usuário está away
(o SDK bloqueia em uso) e aceita `activate` para abrir o build no navegador.

### Busca por texto: filtro local, sem chamada
O campo de busca filtra as linhas já carregadas da aba ativa (match por título/número,
case-insensitive). Sem chamada de backend: o volume por aba (≤ 20 itens) não justifica.

### Estados vazios acionáveis
Cada aba tem texto de vazio próprio ("nenhum PR aberto") + botão que abre a URL raiz da
seção no navegador (`ctx.os.openExternal`) — o usuário sai do vazio com um caminho.

### Rota `/releases` no backend
O `/overview` não cobre releases; esta change adiciona
`GET /releases?days=N` (releases do usuário, por `requestedFor`/`createdBy` quando
existir, filtradas por data client-side igual a builds) servida pelo mesmo `router`.

## Risks / Trade-offs

- [Hooks em `desktop/plugin.js` sem build: erro de runtime derruba a página inteira]
  → harness de teste node com stubs (o mesmo da validação anterior) + smoke no app.
- [`localStorage` pode não existir em builds antigos do Electron] → guard
  `typeof localStorage !== 'undefined'` com fallback em memória.
- [Setting `ignored_projects` escrita por fora conflita com a UI] → a UI recarrega a
  setting no load e no evento de invalidação; último escritor vence (aceito).
- [Notificação nativa exige usuário away] → aceito: é o comportamento do SDK; o badge
  in-app cobre o caso em uso.
- [`TestClient` cobre backend, mas a UI é validada por smoke no app] → harness node com
  stubs de `@hermes/plugin-sdk`/`react` valida o registro e o render; visual final é
  smoke do usuário.

## Migration Plan

Sem migração: `plugin.js` e rota `/releases` novos, deploy = rsync + Reload desktop
plugins + restart do dashboard service (para o backend remontar).

## Open Questions

Nenhum.
