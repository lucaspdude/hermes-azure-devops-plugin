# Tasks

## 1. Configuração

- [x] 1.1 Adicionar `ignored_projects` (lista, default vazio) e `default_days` (int, default 7) em `config_schema` do manifesto e em `config.py` (`PluginConfig`) — verificar com `hermes plugins validate .` e teste unitário dos dois defaults
- [x] 1.2 Helper em `config.py` (`ignored_project_names()`/`ignored_project_ids()`) que normaliza a lista (case-insensitive para nomes, exato para ids) — verificar por teste

## 2. Filtro de data nas tools

- [x] 2.1 `azure_devops_list_pull_requests`: parâmetro opcional `days` (default 7, clamp 1–90) enviado como `searchCriteria.minTime` server-side (ISO 8601 UTC) — verificar com `MockTransport` que o parâmetro viaja e que sem `days` o default é 7
- [x] 2.2 `azure_devops_list_builds`: parâmetro opcional `days` aplicado **após a busca** (`$top = min(50, days * 3)`, filtro por `finishTime`/`queueTime` no Python; a API ignora filtro de data) — verificar com `MockTransport` que builds fora do período são descartados e que nenhum parâmetro de data viaja na query
- [x] 2.3 Documentar o comportamento em `docs/ado-endpoints.md` (builds não filtram data server-side) — verificar que a seção existe

## 3. Projetos ignorados

- [ ] 3.1 `list_projects`: campo `ignored: true|false` por projeto, comparando com a setting `ignored_projects` (nome case-insensitive, id exato) — verificar com `MockTransport` os dois estados
- [ ] 3.2 Tools de conteúdo de projeto ignorado continuam acessíveis quando consultadas explicitamente (sem recusa) — verificar com `MockTransport` que PRs de um projeto ignorado respondem normalmente
- [ ] 3.3 Registrar a decisão ("apenas visual") em `docs/ado-endpoints.md` — verificar o parágrafo

## 4. Backend do painel

- [ ] 4.1 Rota `/overview` aceita `?days=7` (default 7, clamp 1–90) e propaga o corte para PRs (server-side), builds (pós-busca) e WIQL (cláusula `System.ChangedDate >= corte`) — verificar com `TestClient` + `MockTransport` os três cortes
- [ ] 4.2 `/overview` pula projetos ignorados antes de iterar (menos chamadas à API) — verificar com `TestClient` que projeto ignorado gera **zero** chamadas de PR/WIQL/build
- [ ] 4.3 Payloads do painel com `url` (web) e datas ISO 8601 em PRs, work items e builds — verificar com `TestClient` os campos presentes em cada item
- [ ] 4.4 Cache de 15s por (perfil, days) — a chave inclui `days` — verificar que `/overview?days=7` e `?days=30` não compartilham entrada

## 5. Validação final

- [ ] 5.1 Suíte completa passando local (python do sistema + venv) e no hostgator (venv do PM) — verificar `python -m unittest discover -s tests -v` nos dois
- [ ] 5.2 `hermes plugins validate .` e `hermes plugins doctor . --ci` limpos — verificar nos dois
- [ ] 5.3 Smoke real com PAT: `/overview?days=7` no host devolve PRs/builds de até 7 dias (ou vazio legítimo) e respeita `ignored_projects` — verificar contra a organização real
