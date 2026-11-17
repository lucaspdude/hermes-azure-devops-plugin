# Design

## Context

Ver [proposal.md](./proposal.md). O plugin já tem a base agent-side
(`azure-devops-plugin-core`) e as tools (`azure-devops-read-tools`,
`azure-devops-write-tools`). Esta change acrescenta a metade do app.

Fatos do SDK (lidos no checkout do Hermes v0.23.1, doc 04 da pesquisa):

- O backend Python do plugin é `dashboard/plugin_api.py`, montado em
  `/api/plugins/<id>/`; a UI fala com ele por `ctx.rest` (profile-aware,
  recusa `..`) e opcionalmente `ctx.socket`.
- `plugin_api.py` **só é importado** se o plugin estiver em
  `plugins.enabled` no `config.yaml` — caso contrário `ctx.rest` dá 404
  silencioso.
- `broadcast_plugin_event` é fire-and-forget; `ctx.socket` é no-op em remoto
  OAuth → o evento é invalidação, o polling é o ground truth.
- A linha da sidebar **não aceita `render`** (só `{codicon,label,path,tier}`);
  o indicador ao vivo vai para status bar / badge de sessão / própria página.
- A UI é JS de disco, sem build e **sem JSX** (`jsx()` de
  `react/jsx-runtime`); timers usam `ctx.setInterval`, nunca
  `window.setInterval`.
- A meia desktop é **opt-in e app-level**: o app copia
  `plugins/<id>/desktop/plugin.js` para `~/.hermes/desktop-plugins/<id>/`; o
  `doctor` avisa quando a cópia está stale.

## Goals / Non-Goals

**Goals:**
- Visibilidade da atividade do usuário sem gastar turno de LLM.
- Backend fino: nenhuma credencial, configuração ou estado duplicado.
- Atualização confiável: evento como invalidação, polling como ground truth,
  cache para não martelar a API.
- Degradação acionável em cada gate (backend ausente, escopo faltando).

**Non-Goals:**
- Escrita na UI (decisão: leitura no painel, escrita no agente — o agente tem
  o fluxo de aprovação do Hermes e a lógica de tools já testada).
- Seletor de projeto / visão por projeto no painel: o recorte é por identidade
  (decisão avaliada: "meu" 0.63; a visão por projeto fica nas tools).
- Badge na linha de sessão (depende de spike de correspondência de ids).
- Painel no dashboard web além das rotas que a página do desktop consome.
- Widgets configuráveis, múltiplas visualizações, filtros salvos.

## Decisions

### O painel é o "meu" por identidade, não por projeto
A visão mostra o que pertence ao dono do PAT (autor/reviewer de PRs, work
items atribuídos, builds disparados). Isso funciona sem `default_project`
— condição essencial num plugin genérico — e é determinístico por PAT.

A visão por projeto não é uma opção secundária: continua acessível pelas tools
(`azure_devops_list_pull_requests`, `azure_devops_list_builds`,
`azure_devops_query_wiql`), então nada se perde em capacidade, só o atalho
visual.

### Backend fino sobre o `client.py` do agente
`dashboard/plugin_api.py` é um `APIRouter` que **importa o mesmo módulo de
cliente** das tools e converte `AdoError` no mesmo envelope de erro. Nenhum
segundo cliente, nenhuma segunda leitura de PAT, nenhuma taxonomia paralela.

### Cache em memória de ~15s por escopo
O polling de uma página aberta é a fonte de tráfego; sem cache, cada
reabertura/refresh vira chamada à API e o risco de 429 sobe. 15s é curto o
bastante para não parecer "travado" e longo o bastante para absorver polling
humano. O cache é invalidated quando chega um evento de escrita.

### A UI é read-only por construção
Só existem rotas `GET`. A mutação fica no agente, que tem aprovação,
mensagem de erro padronizada e idempotência controlada. Duplicar escrita na
UI criaria dois lugares para a mesma regra.

### O evento é invalidação, não estado
O backend não "publica" o estado: ele emite `ado.changed` e a UI re-busca
por REST. Como a entrega é fire-and-forget, o polling de 15s é o ground truth
e a UI nunca confia no evento como fonte.

### Entradas: sidebar estática + chip no status bar
A sidebar só aceita rótulo e rota → entrada estática "Azure DevOps". O chip do
status bar carrega a contagem (é a superfície sancionada para indicador ao
vivo) e navega para a página ao clicar.

### Badge de sessão fica de fora do v1 (spike)
A linha de sessão entrega o **durable stored id**, enquanto o contexto de tool
entrega `session_id` (muda na compressão) e `conversation_id` (estável). Não
há correspondência verificada. Sem ela, o badge mostraria o dado errado — o
mesmo risco R9 que o plano do database-connector registra. Fica como spike com
decisão explícita: se o mapeamento não se confirmar, o sinal vai para a
página ("última atividade tocada pelo agente") e não para a linha.

### A UI é JS puro, sem build, sem JSX
`desktop/plugin.js` em ESM, importando só `@hermes/plugin-sdk`, `react` e
`react/jsx-runtime`; JSX escrito como `jsx()`; cores por
`var(--ui-*)`; timers por `ctx.setInterval`.

### O gate é documentado como parte do produto
Como a tela depende de dois gates (plugin em `plugins.enabled` + toggle da
meia desktop em Capabilities → Plugins), ambos entram no README e a página
trata o 404 do backend com mensagem acionável.

## Ambiente de execucao e referencia viva

O alvo e o host `hostgator` (VPS), com **Hermes Agent v0.23.2** em
`/root/.hermes/hermes-agent` e o gateway escutando em `127.0.0.1:34007`. O app
Desktop do Mac ja tem esse host cadastrado como conexao SSH
(`hubcredito-agent`, porta 22022, chave `id_hostgator`), e o host ja serve
**dois perfis** (`default` e `hub-documentador`) — o backend do painel e
profile-aware, entao a rota precisa respeitar o perfil ativo.

Transport validado (leitura, pelo mesmo forward SSH que o app usa):

```
ssh -L <local>:127.0.0.1:34007 hostgator
  GET /api/health               -> 200  {"ok":true,"version":"0.23.2"}
  GET /api/plugins/             -> 401  {"reason":"no_cookie"}   (existe, exige sessao)
  GET /api/desktop-plugins/list -> 401  {"reason":"no_cookie"}   (existe, exige sessao)
```

O `401 no_cookie` e o estado esperado fora do app: no remoto a autenticacao e
por **cookie de sessao** emitido pelo login do proprio app, nao por header. O
`ctx.rest` do plugin herda esse mesmo cookie, entao a chamada do painel chega ao
gateway remoto normalmente.

**Referencia viva**: o plugin `autorag` (`~/.hermes/plugins/autorag`) ja
implementa o pacote unificado que esta change desenha, com a metade desktop
materializada em `~/.hermes/desktop-plugins/autorag/plugin.js`. Ele confirma os
contratos a seguir:

```
autorag/
├── plugin.json              (metadados do pacote)
├── dashboard/manifest.json  { name, label, description, icon, version, api: "plugin_api.py" }
├── dashboard/plugin_api.py  router = APIRouter(); @router.get("/status") ...
├── desktop/plugin.js        export default { id, name, description, defaultEnabled, register(ctx) }
└── skills/<nome>/SKILL.md   (4 skills embarcadas)
```

E os contratos do SDK que ele usa: `ctx.registerMany([...])` com `PANES_AREA` /
`PALETTE_AREA` / `KEYBINDS_AREA` / `STATUSBAR_AREAS.right`, `ctx.rest(path,
opts)`, `ctx.onDispose(...)` e `ctx.i18n.register(LOCALES)`. A pagina
(`ROUTES_AREA`) e a linha da sidebar (`SIDEBAR_NAV_AREA`) nao tem exemplo vivo
local, mas sao as areas documentadas da mesma SDK.

**Onde a metade desktop e materializada**: `materialize_desktop_half` copia de
`<hermes_root>/plugins/<nome>` para `<hermes_root>/desktop-plugins/<nome>` — no
**host onde o gateway roda**, nao no cliente. No `hostgator` ainda nao existe
`~/.hermes/desktop-plugins/`; ele nasce na instalacao do plugin. O `doctor`
avisa quando a copia esta stale.


## Risks / Trade-offs

- [Backend não montado → tela vazia] → a página trata 404 com mensagem
  acionável; README documenta o gate.
- [Cópia stale de `desktop/plugin.js`] → `doctor` avisa; o README explica o
  Rescan e o symlink para desenvolvimento.
- [Evento perdido] → polling de 15s reconcilia; a UI nunca usa o evento como
  estado.
- [429 do ADO com várias janelas abertas] → cache por escopo; o chip usa o
  mesmo payload cacheado.
- [Escopo `Identity: Read` ausente] → degradação explícita, não tela quebrada.
- [Painel desatualizado por up to 15s] → aceito: o evento invalida na hora e o
  cache só existe para absorver polling repetido.
- [Badge de sessão] → não entra no v1 (spike); sem isso, perde-se o indicador
  "este chat mexeu neste PR".
- [Meia desktop é app-level e opt-in] → o usuário precisa ligar o toggle; sem
  isso, a página simplesmente não existe no app (sem erro).

## Migration Plan

Nenhuma (plugin novo). Rollback: remover o pacote e o toggle em Capabilities.

## Open Questions

(nenhuma que afete specs ou tasks; o spike do badge de sessão tem decisão
própria documentada acima)
