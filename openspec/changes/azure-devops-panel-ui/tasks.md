# Tasks

## 1. Backend: rota de releases e settings

- [ ] 1.1 Criar `GET /releases?days=N` no `dashboard/plugin_api.py` (releases do usuário nas varreduras de projeto, corte por data igual a builds, mesmos `_links.web`/datas) — verificar com `TestClient` + `MockTransport` o payload e o corte
- [ ] 1.2 Criar `POST /settings/ignored-projects` que grava `plugins.entries.<id>.settings.ignored_projects` no config do perfil via `hermes_cli.config` e devolve o estado gravado — verificar com `TestClient` que a setting é gravada e lida de volta
- [ ] 1.3 Teste de regressão das rotas existentes (`/overview`, `/pull-requests/{id}`, `/builds/{id}`) garantindo que nada quebrou — verificar suite verde

## 2. UI: estrutura de abas e filtros

- [ ] 2.1 Reescrever `Panel` em `desktop/plugin.js` com estado de abas (`prs`/`wi`/`builds`/`releases`), contadores no título e persistência da aba ativa em `localStorage` (com guard para build antigo) — verificar no harness de stubs node que o registro e o render passam
- [ ] 2.2 Barra de presets de período (7/30/90, default 7, persistido em `localStorage`) que refaz a busca com `days` — verificar no harness que o clique troca o valor enviado ao `rest`
- [ ] 2.3 Campo de busca por texto filtrando localmente as linhas da aba ativa — verificar no harness com dois itens e um filtro

## 3. UI: conteúdo das linhas

- [ ] 3.1 Linhas clicáveis com `ctx.os.openExternal(url)` (PR, WI, build, release) e linhas sem url exibidas sem clique — verificar no harness que linhas sem url não registram handler
- [ ] 3.2 Datas relativas ("há 2 dias", "há 3 horas") calculadas dos ISO 8601 — verificar com teste unitário da função de formatação (agora, minutos, horas, dias)
- [ ] 3.3 Badges de estado com `var(--ui-success)`/`--ui-danger`/`--ui-warning`/`--ui-text-secondary` e o texto cru da API — verificar por inspeção no app e teste do mapeamento estado→cor

## 4. UI: filtros, refresh e notificações

- [ ] 4.1 Seletor de projetos ignorados (checkbox por projeto do `/overview`) que grava via `POST /settings/ignored-projects` e reflete o estado no load — verificar no harness o fluxo marcar→gravar→recarregar
- [ ] 4.2 Botão de refresh manual (força `rest('/overview')` imediato) + indicador "atualizado há Xs" (tick de 1s) — verificar no harness que o indicador atualiza e o polling de 15s continua
- [ ] 4.3 Notificação nativa de build falho com dedupe por build id (`ctx.os.notify` com `activate` para abrir o build) e guarda para só notificar builds do usuário — verificar por teste com `ctx.os.notify` stubado
- [ ] 4.4 Estados vazios acionáveis por aba (mensagem + botão "abrir no Azure DevOps") — verificar no harness com listas vazias

## 5. Deploy e validação

- [ ] 5.1 Suite completa verde local (python do sistema + venv) e rsync para o hostgator — verificar suite + `hermes plugins doctor /root/.hermes/plugins/azure-devops --ci` limpo
- [ ] 5.2 Reconciliar a meia desktop (`reconcile_desktop_halves_report`) e conferir md5 do `plugin.js` materializado contra o do repo — verificar md5 iguais
- [ ] 5.3 Smoke no app Desktop: clicar no chip, alternar as 4 abas, trocar preset, buscar, ignorar um projeto, clicar numa linha (abre no navegador), refresh manual — verificar visualmente cada interação
- [ ] 5.4 Smoke de notificação: simular build falho do usuário e confirmar notificação única — verificar no app
