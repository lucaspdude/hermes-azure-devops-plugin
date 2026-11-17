# Paridade das tools de leitura com o MCP azure-devops-connector

Fonte do MCP: src/tools.ts (21 tools: 4 de projetos/repos, 4 de builds, 13 de pull requests).
Fonte do plugin: registry.TOOLS (31 tools nesta change).

## Cobertura das 21 tools do MCP

| Tool do MCP | No plugin | Onde |
|---|---|---|
| ado_abandon_pull_request | change seguinte (escrita) | azure_devops_abandon_pull_request (change write-tools) |
| ado_add_pull_request_comment | change seguinte (escrita) | azure_devops_add_pull_request_comment (change write-tools) |
| ado_add_pull_request_label | change seguinte (escrita) | azure_devops_add_pull_request_label (change write-tools) |
| ado_approve_pull_request | change seguinte (escrita) | azure_devops_approve_pull_request (change write-tools) |
| ado_complete_pull_request | change seguinte (escrita) | azure_devops_complete_pull_request (change write-tools) |
| ado_create_pull_request | change seguinte (escrita) | azure_devops_create_pull_request (change write-tools) |
| ado_get_build | sim (leitura) | azure_devops_get_build |
| ado_get_build_changes | sim (leitura) | azure_devops_get_build_changes |
| ado_get_build_timeline | sim (leitura) | azure_devops_get_build_timeline |
| ado_get_project | sim (leitura) | azure_devops_get_project |
| ado_get_pull_request | sim (leitura) | azure_devops_get_pull_request |
| ado_get_repository | sim (leitura) | azure_devops_get_repository |
| ado_list_builds | sim (leitura) | azure_devops_list_builds |
| ado_list_projects | sim (leitura) | azure_devops_list_projects |
| ado_list_pull_request_comments | sim (leitura) | azure_devops_list_pull_request_comments |
| ado_list_pull_request_labels | sim (leitura) | azure_devops_list_pull_request_labels |
| ado_list_pull_requests | sim (leitura) | azure_devops_list_pull_requests |
| ado_list_repositories | sim (leitura) | azure_devops_list_repositories |
| ado_reject_pull_request | change seguinte (escrita) | azure_devops_reject_pull_request (change write-tools) |
| ado_remove_pull_request_label | change seguinte (escrita) | azure_devops_remove_pull_request_label (change write-tools) |
| ado_reset_pull_request_vote | change seguinte (escrita) | azure_devops_reset_pull_request_vote (change write-tools) |

## Extensoes do plugin que o MCP nao tem

- azure_devops_get_branch
- azure_devops_get_commit
- azure_devops_get_my_identity
- azure_devops_get_release
- azure_devops_get_wiki_page
- azure_devops_get_work_item
- azure_devops_list_branches
- azure_devops_list_build_artifacts
- azure_devops_list_build_definitions
- azure_devops_list_commits
- azure_devops_list_identities
- azure_devops_list_policies
- azure_devops_list_release_definitions
- azure_devops_list_releases
- azure_devops_list_tags
- azure_devops_list_wiki_pages
- azure_devops_list_wikis
- azure_devops_list_work_items
- azure_devops_query_wiql

## Diferencas deliberadas

- Nomes renomeados de ado_* para azure_devops_* (decisao da pesquisa, sectao 8).
- list_policies le /_apis/policy/configurations (policy por repositorio nao e alcancavel com PAT classico - verificado contra a API real).
- list_identities e get_my_identity via /_apis/connectionData (api-version 7.0-preview.1, tambem verificado).
- Wiki expoe o projeto dono (o remoteUrl da wiki) porque as paginas exigem o projeto dono no path - verificado contra a API real.

## Conferencia automatica

Todas as tools de leitura do MCP estao mapeadas no registro do plugin (o teste tests/test_docs_endpoints.py cobre as 31 tools de leitura).
