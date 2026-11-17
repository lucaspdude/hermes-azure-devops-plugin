# Proposal

## Why

O plugin dá acesso ao Azure DevOps **pelo chat**, mas o usuário só descobre que
tem PR esperando, build quebrado ou work item atribuído a ele **se perguntar**.
A surface do Desktop (página, linha na sidebar, chip no status bar) dá essa
visibilidade sem custo de contexto e sem gastar um turno de LLM — e é a
mesma peça que o Hermes já sanciona para plugins (Desktop Plugin SDK + backend
`plugin_api.py`).

O plugin é genérico: a visão não pode depender de projeto, time ou nome de
empresa configurado. O recorte que funciona sem configuração é **"minha
atividade"**: o que o dono do PAT é autor/reviewer, o que está atribuído a ele,
o que ele disparar por último.

## What Changes

- Acrescenta a **meia desktop** do plugin: `desktop/plugin.js` (página
  `/azure-devops`, linha na sidebar, chip no status bar) e
  `dashboard/plugin_api.py` + `dashboard/manifest.json` (rotas REST do painel),
  formando o pacote unificado (agente + dashboard + desktop).
- O backend do painel é um **adaptador fino** sobre o mesmo `client.py` usado
  pelas tools: mesmo PAT, mesma configuração, nenhuma credencial duplicada e
  nenhum estado duplicado (o estado canônico continua sendo a API do ADO).
- O painel mostra a **atividade do usuário autenticado** (PRs onde ele é
  autor/reviewer, work items atribuídos a ele, últimas builds disparadas por
  ele), sem exigir `default_project` — a visão por projeto continua
  acessível pelas tools do agente.
- O painel é **estritamente de leitura**: escrita continua no agente, que
  aproveita o fluxo de aprovação do Hermes e a lógica já implementada nas
  tools.
- O polling da página é limitado por **cache em memória de ~15s** no backend, e
  as tools de escrita do agente emitem um evento que **invalida** o painel.
- Documenta os **gates** que tornam a tela silenciosamente vazia: o
  `plugin_api.py` só é importado com o plugin em `plugins.enabled`, e a meia
  desktop é opt-in em Capabilities → Plugins.

## Capabilities

### New Capabilities
- `azure-devops-desktop-surface`: a surface do plugin dentro do app Hermes
  Desktop — painel da atividade do usuário autenticado, entradas de navegação,
  invalidação por evento com fallback de polling, e degradação explícita
  quando o backend não está montado.

### Modified Capabilities

(nenhuma)

## Impact

- **Novo código**: `dashboard/manifest.json`, `dashboard/plugin_api.py`,
  `desktop/plugin.js`; `client.py` ganha o ponto de extensão para o backend
  (cliente compartilhado) e as tools de escrita passam a emitir evento.
- **Manifesto**: `plugin.yaml` passa a descrever a surface desktop (o
  `desktop/plugin.js` passa a existir no pacote).
- **Sistemas externos**: a API do Azure DevOps — apenas leitura a partir do
  painel; o mesmo PAT e a mesma organização do agente.
- **Comportamento do agente**: as tools de escrita passam a emitir um evento
  (fire-and-forget) — nenhum contrato de tool muda.
- **Fora de escopo**: escrita na UI, seletor de projeto no painel, badge na
  linha de sessão (depende de um spike de correspondência de ids), meia
  dashboard web além do que a página do desktop usa.
