# Desktop SDK — notas da verificacao (spike)

Data: 2026-11-17. Fontes: plugin de referencia `autorag`
(`~/.hermes/plugins/autorag/desktop/plugin.js`), SDK do app
(`hermes-agent/apps/desktop/src/sdk/`, `src/api/plugins.ts`) e o mount do
backend (`hermes_cli/web_server_dashboard.py`).

## O que as superficies aceitam (confirmado)

| Area | Campos/uso | Fonte |
|---|---|---|
| `ROUTES_AREA` | `{ path }` + `render: () => Element` | doc SDK |
| `SIDEBAR_NAV_AREA` | `{ path, label, codicon, tier? }` — **sem render** | doc SDK |
| `STATUSBAR_AREAS.right` | `render` ou `data`, com `order` | autorag usa `render` |
| `ctx.rest(path, opts)` | profile-aware, escopo `/api/plugins/<id>/`, recusa `..` | `src/api/plugins.ts` (`pluginRest`) |
| `ctx.onEvent(name, fn)` | nome do wire: `plugin.<id>.<event>` | doc SDK |
| `ctx.setInterval` / `ctx.clearInterval` | sobrevivem ao hot reload; limpar no `onDispose` | doc SDK |
| `ctx.registerMany([...])` | registro em lote | autorag |
| `ctx.onDispose(fn)` | limpeza (timers, listeners) | autorag |

## Backend: como o `plugin_api.py` e carregado (importante)

`_mount_one_plugin_api` importa o arquivo com `import_user_code(api_path,
"hermes_dashboard_plugin_<nome>")` — **fora do pacote do plugin**, isolado.
Consequencias aplicadas nesta implementacao:

- **Sem imports relativos** em `dashboard/plugin_api.py`: o modulo resolve os
  modulos do plugin pelo namespace que o loader do agente registrou, via o shim
  `hermes_plugin_modules.py` (raiz do plugin).
- O router e montado em `/api/plugins/<name>/` com dependencia de
  `_plugin_route_secret_scope` (escopo de segredos do perfil).
- O mount exige o plugin em `plugins.enabled` (gate GHSA-mcfc-hp25-cjv7) e so
  importa de fontes `bundled`/`user` — projeto (`./.hermes/plugins/`) nunca
  auto-importa Python.

## Spike do badge de sessao: decisao

A correspondencia entre o id da linha de sessao (durable stored id) e a conversa
do agente (`conversation_id`/`session_id`) nao foi confirmada nesta verificacao:
a area `SESSION_ROW_AREAS` entrega o id duravel ao render, mas o contexto da tool
carrega `session_id` (muda na compressao) e `conversation_id` (estavel), e nao ha
um mapeamento publicado entre eles no SDK. **Decisao: o badge de linha de sessao
fica fora do v1**; o sinal de "o agente mexeu no Azure DevOps" fica na pagina
(e o painel e invalidado pelo evento de escrita). Revisar quando o SDK publicar
o mapeamento.

## Stale copy

A metade desktop e materializada no host do gateway
(`materialize_desktop_half`): `<hermes_root>/plugins/<nome>` →
`<hermes_root>/desktop-plugins/<nome>/plugin.js`. O `doctor` avisa quando a
copia fica stale; no desenvolvimento, symlink + Rescan.
