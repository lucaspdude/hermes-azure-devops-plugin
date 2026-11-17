# Tasks

## 1. Registro da verificacao de endpoints (feita no planejamento)

- [x] 1.1 Registrar a tabela de rotas verificadas (data, organizacao de referencia, codigo por rota e nota de contrato) em `docs/ado-endpoints.md` no repo — verificar que o arquivo cobre as 31 tools de leitura, incluindo as rotas que falharam
- [x] 1.2 Aplicar os contratos descobertos na verificacao: paging de builds por `$top` (nunca `top`), `branch` como nome curto nos commits, wiki sempre com o projeto dono no path (extraido do `remoteUrl`), WIQL sempre com corpo JSON — verificar por teste que o parametro `$top` vai codificado (`%24top`) e que a wiki e chamada no projeto dono
- [ ] 1.4 Repetir a verificação de rotas **a partir do hostgator** (o caminho de saída de rede do host pode diferir do da máquina de desenvolvimento) e anexar o resultado ao registro — verificar que o mesmo conjunto de rotas responde igual no host
- [x] 1.3 Trocar a tool de policies para `/_apis/policy/configurations` (policy configurations do projeto) e documentar que policy por repositorio nao e alcancavel com PAT classico — verificar com `MockTransport` a rota e a mensagem de erro

## 2. Tools de projetos e repositorios

- [x] 2.1 Implementar `azure_devops_list_projects` e `azure_devops_get_project` (projeto por nome ou id) — verificar com `MockTransport` que a rota chamada é `/_apis/projects` e que projeto inexistente devolve `not_found`
- [x] 2.2 Implementar `azure_devops_list_repositories` e `azure_devops_get_repository` — verificar com `MockTransport` a rota `/{project}/_apis/git/repositories` e o retorno normalizado (id, nome, url, branch padrão)

## 3. Tools de builds

- [x] 3.1 Implementar `azure_devops_list_build_definitions` (com filtro por nome) e `azure_devops_list_builds` com filtro por status, por definition (id ou nome) e `top` — verificar com `MockTransport` que o nome da definition é resolvido para id antes da listagem
- [x] 3.2 Implementar `azure_devops_get_build`, `azure_devops_get_build_changes` (normalizando array puro e envelope `{value: [...]}`) e `azure_devops_get_build_timeline` — verificar com `MockTransport` os dois formatos de `changes`
- [x] 3.3 Cobrir a paginação de builds (header `x-ms-continuationtoken`) e a propagação do token para a página seguinte — verificar com `MockTransport` que a segunda chamada envia o token recebido

## 4. Tools de pull requests (leitura)

- [x] 4.1 Implementar `azure_devops_list_pull_requests` (filtro `active|abandoned|completed|all`) e `azure_devops_get_pull_request` — verificar com `MockTransport` o parâmetro de status enviado
- [x] 4.2 Implementar `azure_devops_list_pull_request_comments` e `azure_devops_list_pull_request_labels` — verificar com `MockTransport` as rotas de threads e labels

## 5. Tools de work items

- [x] 5.1 Implementar `azure_devops_query_wiql` (POST em `/_apis/wit/wiql`, com `top`) — verificar com `MockTransport` o método e o corpo da consulta
- [x] 5.2 Implementar `azure_devops_get_work_item` (campos default reduzidos + `fields` explícito) e `azure_devops_list_work_items` (filtro por tipo/ids) — verificar com `MockTransport` que o work item inexistente devolve `not_found`

## 6. Tools de wiki, refs git, artefatos, identidades e politicas

- [x] 6.1 Implementar `azure_devops_list_wikis` (lista da organizacao, cada wiki com o projeto dono vindo do `remoteUrl`), `azure_devops_list_wiki_pages` e `azure_devops_get_wiki_page` (sempre no projeto dono da wiki) — verificar com `MockTransport` o retorno do conteudo, da data e que o path usa o projeto dono
- [x] 6.2 Implementar `azure_devops_list_branches`, `azure_devops_get_branch`, `azure_devops_list_commits`, `azure_devops_get_commit` e `azure_devops_list_tags` — verificar com `MockTransport` as rotas de `git/refs` e `git/commits`
- [x] 6.3 Implementar `azure_devops_list_build_artifacts` — verificar com `MockTransport` nome, tamanho e url de cada artefato
- [x] 6.4 Implementar `azure_devops_get_my_identity` e `azure_devops_list_identities` via `/_apis/connectionData` — verificar com `MockTransport` o id e o display name devolvidos
- [x] 6.5 Implementar `azure_devops_list_policies` lendo as **policy configurations do projeto** (`/_apis/policy/configurations`, verificado como 200 com PAT de escopo minimo), com mensagem explicita para quem procurar policy por repositorio — verificar com `MockTransport` a rota e o texto do aviso

## 7. Tools de releases

- [x] 7.1 Implementar `azure_devops_list_release_definitions` e `azure_devops_list_releases` (filtro por definition) — verificar com `MockTransport` que a chamada vai para `vsrm.dev.azure.com/{org}/{project}/_apis/release/...`
- [x] 7.2 Implementar `azure_devops_get_release` e o tratamento de release inexistente — verificar com `MockTransport` o retorno `not_found`

## 8. Registro, manifesto e validacao

- [ ] 8.1 Agregar os modulos em `registry.py` e atualizar `provides_tools` no manifesto — verificar que o teste de consistencia passa
- [ ] 8.2 Revisar as descricoes de todas as tools (o que faz e quando usar) e o `check_fn` de credencial — verificar que toda tool tem `check_fn` e descricao nao vazia, e que a descricao nao carrega conteudo que pertence as skills (o contrato e as receitas ficam nas skills, nao no schema)
- [ ] 8.3 Conferir item a item a paridade com as 23 tools de leitura do MCP (`hub/workflow/tools/azure-devops/src/tools.ts`) e registrar as diferencas deliberadas — verificar com a lista comparada anexada ao PR
- [ ] 8.4 Rodar a suite, `hermes plugins validate . --install-deps` e `hermes plugins doctor . --ci` **no hostgator** — verificar que tudo termina limpo no host alvo
- [ ] 8.5 Fazer o smoke de leitura no hostgator com PAT real (projetos, repos, builds com paginação por `$top`, PRs, WIQL, wiki pages no projeto dono, commits por branch curto) — verificar que os retornos batem com o esperado e que nenhuma chamada falha por versão de API
