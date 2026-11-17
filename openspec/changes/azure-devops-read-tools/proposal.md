# Proposal

## Why

Com a fundação pronta (config, PAT, cliente HTTP, envelope de erro), falta a
superfície de **leitura** — que é o que o agente usa 90% do tempo: localizar
projetos, repositórios, builds, pull requests, work items, wiki, branches,
commits, tags, artefatos, identidades, políticas e releases. Sem ela o plugin
não existe para o usuário: instalar o pacote só habilita um cliente HTTP.

## What Changes

- Entrega as tools de leitura da API do Azure DevOps, com prefixo
  `azure_devops_*`, todas registradas no registro único e refletidas em
  `provides_tools`.
- Cobre as 23 tools de leitura do MCP `azure-devops-connector` existente
  (projetos, repositórios, builds e pull requests) **e** as extensões decididas
  na pesquisa: work items, wiki, branches/commits/tags, artefatos, identidades,
  políticas e releases.
- Preserva os comportamentos que o MCP já resolvia e que são armadilhas
  conhecidas: paginação de builds pelo header `x-ms-continuationtoken`,
  resolução de build definition por nome, normalização da resposta de
  `changes` (array puro ou envelope `{value: [...]}`) e o host
  `vsrm.dev.azure.com` do Release Management.
- Cada tool devolve o envelope `{"ok": true, "data": ...}` definido na
  capability `azure-devops-plugin-core`.

## Capabilities

### New Capabilities
- `azure-devops-read-tools`: surface de leitura do Azure DevOps exposta ao
  agente — projetos, repositórios, builds, pull requests, work items, wiki,
  refs git, artefatos, identidades, políticas e releases.

### Modified Capabilities

(nenhuma)

## Impact

- **Depende de**: `azure-devops-plugin-foundation` (config, PAT, cliente
  HTTP, envelope de erro) — esta change pressupõe essa base implementada.
- **Novo código**: módulos de tools por domínio (`tools_projects.py`,
  `tools_builds.py`, `tools_pull_requests.py`, `tools_work_items.py`,
  `tools_wiki.py`, `tools_git.py`, `tools_artifacts.py`,
  `tools_identity.py`, `tools_policies.py`, `tools_releases.py`) agregados
  em `registry.py`, com `plugin.yaml` atualizado.
- **Sistemas externos**: API REST do Azure DevOps (`dev.azure.com` e
  `vsrm.dev.azure.com`) — leitura apenas, nenhuma escrita.
- **Dependências**: nenhuma nova (mesma base da change de fundação).
- **Fora de escopo**: tools de escrita (change seguinte), `/ado-help`,
  documentação e publicação (change de help/distribuição).
