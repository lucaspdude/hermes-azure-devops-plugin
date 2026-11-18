# Design

## Context

Ver proposal.md. O painel atual varre todos os projetos a cada ciclo (~14 × 3 endpoints),
não filtra por data, não devolve links nem datas. As tools de listagem também não expõem
filtro de data.

Fatos verificados contra a API real (2026-11-17):

- PRs: `searchCriteria.minTime` **funciona** (filtro server-side real).
- Builds: `minFinishTime`/`maxFinishTime` são **ignorados em silêncio** nos query
  params (devolvem os mesmos resultados com e sem). `POST /_apis/build/queries` não
  existe (resposta não-JSON). O único corte de data de builds possível é **client-side**.
- `list_projects` já é chamada pelo painel — o campo `ignored` sai dela de graça.

## Goals / Non-Goals

**Goals:**
- Cortar o ruído: default 7 dias e projetos ignorados pulados **antes** da API.
- Datas e links nos payloads do painel (a UI da change `azure-devops-panel-ui` consome).
- Mesmo parâmetro `days` nas tools do agente (consistência painel ↔ agente).

**Non-Goals:**
- UI/UX (abas, badges, busca, notificações) — change `azure-devops-panel-ui`.
- Esconder projetos ignorados do agente (decisão do usuário: apenas visual).
- Filtro de data para work items via WIQL (o WIQL do painel já ordena por
  `ChangedDate DESC` e o corte é pós-busca).

## Decisions

### `ignored_projects` como setting do perfil, lida antes da varredura
A setting vive em `plugins.entries.<id>.settings.ignored_projects` (lista de nomes ou
ids — os dois aceitos, comparados case-insensitive por nome e igualdade por id). O
backend do painel filtra a lista de projetos **antes** de iterar PRs/WIQL/builds: projeto
ignorado não gera chamada. As tools do agente **não** recusam conteúdo de projeto
ignorado (decisão do usuário: efeito apenas visual); `list_projects` marca `ignored`.

*Alternativa*: esconder do agente também — rejeitada pelo usuário (quebra automações
que consultam projeto ignorado explicitamente).

### `days` com default 7 e clamp 1–90
Painel e tools aceitam `days` (default 7, mínimo 1, máximo 90). O clamp evita
`$top` gigante e varredura infinita. Presets de UI (7/30/90) mapeiam direto.

### Corte de data de builds no backend (não na API)
`_overview_payload` busca `$top = min(50, days * 3)` builds por projeto e filtra
`finishTime`/`queueTime` >= data de corte no Python. A API ignora `minFinishTime`
nos query params (verificado) — não existe filtro server-side de builds por data.

### Corte de data de PRs server-side
PRs usam `searchCriteria.minTime` (funciona, verificado). O corte é
`now - days` em ISO 8601 UTC.

### Work items: corte pós-WIQL
O WIQL já ordena por `ChangedDate DESC` e aceita `$top`; o corte de data
(`System.ChangedDate >= corte`) entra na própria cláusula WHERE da query — server-side
e sem chamada extra (o WIQL aceita datas literais na cláusula).

### Links: campo `url` por item
- PR: `_links.web.href` do payload (já vem da API).
- Build: `_links.web.href` (página de resultados).
- Work item: `_links.html.href` (página HTML).
- Fallback: construir `https://dev.azure.com/{org}/{project}/…` quando o payload não
  traz `_links`.

### Datas ISO 8601 UTC
Todos os campos de data são devolvidos em ISO 8601 UTC (`2026-11-17T12:00:00Z`). A UI
converte para local e mostra relativo ("há 2 dias").

## Risks / Trade-offs

- [Varredura de 14 projetos por projeto continua O(n) chamadas] → mitigado por
  `ignored_projects` (o usuário corta os que não usa) e pelo cache de 15s existente.
- [`days=90` com organização grande pode estourar `$top`] → `$top` do painel
  escala com `days` (`min(50, days * 3)`) e o corte pós-busca descarta o resto.
- [Nome de projeto ignorado renomeado na org vira "não ignorado"] → a setting aceita
  **id** (estável) ou nome (legível); docs recomendam id.
- [WIQL com data literal pode confundir timezone] → a data de corte é gerada em UTC e
  comparada com `System.ChangedDate` (que a API trata em UTC).

## Migration Plan

Sem migração: setting nova com default vazio, parâmetros novos opcionais com default
que preserva o comportamento atual (exceto o ganho de filtro).

## Open Questions

Nenhum.
