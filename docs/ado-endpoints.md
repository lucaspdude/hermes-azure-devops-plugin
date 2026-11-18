# Azure DevOps endpoints — verification record

Record of the endpoint verification of the **reading** tools of the plugin,
done on **2026-11-17** against the reference Azure DevOps organization.

The verification used two credentials of the same user: a PAT of production
(minimum scopes) and a temporary PAT of full scope. **The difference between
the two answers is the difference of scope** — that is how the routes that a
classic PAT cannot reach were told apart from the routes that do not exist.

Only read routes were exercised: no write route was called, so the reference
organization was left untouched.

| | |
|---|---|
| API host | `https://dev.azure.com/{organization}` |
| Release Management | `https://vsrm.dev.azure.com/{organization}` (the release routes do not exist on the API host) |
| Default API version | `7.1` — `connectionData` answers only on `7.0-preview.1` |
| Page size | `$top` — a `top` without the dollar sign is **ignored** |
| Continuation token | header `x-ms-continuationtoken` (builds) or the body (the other routes) |

The contracts of this record are encoded once, in `contracts.py`, and proved
by `tests/test_contracts.py`.

## The 31 reading tools and their routes

`{org}` is the organization, `{project}` the project (by name or by id) and
`{repoId}` the repository (by id or by name). The routes marked **not
exercised** belong to tools whose family route answered 200, but whose exact
path was not called during the verification — they are not observations.

| # | Tool | Route | Code | Contract note |
|---|---|---|---|---|
| 1 | `azure_devops_list_projects` | `GET /{org}/_apis/projects` | 200 | 14 projects; the list is of the **organization**. |
| 2 | `azure_devops_get_project` | `GET /{org}/_apis/projects/{project}` | 200 | The project by name or by id; 404 when it does not exist. |
| 3 | `azure_devops_list_repositories` | `GET /{org}/{project}/_apis/git/repositories` | 200 | 3 repositories. |
| 4 | `azure_devops_get_repository` | `GET /{org}/{project}/_apis/git/repositories/{repoId}` | 200 | The repository by id or by name. |
| 5 | `azure_devops_list_build_definitions` | `GET /{org}/{project}/_apis/build/definitions` | 200 | The definitions of the pipelines of the project. |
| 6 | `azure_devops_list_builds` | `GET /{org}/{project}/_apis/build/builds` | 200 | The paging uses **`$top`**; the token of the next page comes in the header `x-ms-continuationtoken`. |
| 7 | `azure_devops_get_build` | `GET /{org}/{project}/_apis/build/builds/{buildId}` | not exercised | The route of the build answers 200; this exact path was not called. |
| 8 | `azure_devops_get_build_changes` | `GET /{org}/{project}/_apis/build/builds/{buildId}/changes` | 200 | Envelope `{count, value}`. |
| 9 | `azure_devops_get_build_timeline` | `GET /{org}/{project}/_apis/build/builds/{buildId}/timeline` | 200 | Envelope `{records}`. |
| 10 | `azure_devops_list_pull_requests` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/pullrequests` | 200 | Filter `status` (`active`, `abandoned`, `completed`, `all`) and `$top`. |
| 11 | `azure_devops_get_pull_request` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/pullRequests/{pullRequestId}` | 200 | — |
| 12 | `azure_devops_list_pull_request_comments` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/pullRequests/{pullRequestId}/threads` | 200 | 3 threads. |
| 13 | `azure_devops_list_pull_request_labels` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/pullRequests/{pullRequestId}/labels` | 200 | Envelope `{count, value}`. |
| 14 | `azure_devops_query_wiql` | `POST /{org}/{project}/_apis/wit/wiql` | 200 | 620 items. **Without a body it answers 411; a GET answers 405.** The page size travels as `$top`. The project is optional: without one the query runs in the whole organization (`POST /{org}/_apis/wit/wiql`, **not exercised** during the verification). |
| 15 | `azure_devops_get_work_item` | `GET /{org}/_apis/wit/workitems/{id}` | 200 | Accepts `fields=System.Id,System.Title,...`. |
| 16 | `azure_devops_list_work_items` | `GET /{org}/_apis/wit/workitems?ids=...` | not exercised | The read of a work item by id answers 200; the read by ids was not called. |
| 17 | `azure_devops_list_wikis` | `GET /{org}/_apis/wiki/wikis` | 200 | The list is of the **organization**; each wiki carries the id of the project that owns it in the `remoteUrl`. |
| 18 | `azure_devops_list_wiki_pages` | `GET /{org}/{owner-project}/_apis/wiki/wikis/{wikiId}/pages` | 200 | The project of the path must be the **owner** of the wiki; another project answers 404 `WikiNotFoundException`. |
| 19 | `azure_devops_get_wiki_page` | `GET /{org}/{owner-project}/_apis/wiki/wikis/{wikiId}/pages?path=/Home` | 404 | A page that does not exist answers 404, with an explicit message of the API. |
| 20 | `azure_devops_list_branches` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/refs?filter=heads` | 200 | — |
| 21 | `azure_devops_get_branch` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/refs/heads/{branch}` | 200 | The branch here is the short name, like in the commits. |
| 22 | `azure_devops_list_commits` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/commits` | 200 | 23 commits. `$top` works and `top` is **ignored**. The branch is the **short name** (`master`): `refs/heads/master` answers **404**. |
| 23 | `azure_devops_get_commit` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/commits/{commitId}` | 200 | — |
| 24 | `azure_devops_list_tags` | `GET /{org}/{project}/_apis/git/repositories/{repoId}/refs?filter=tags` | 200 | — |
| 25 | `azure_devops_list_build_artifacts` | `GET /{org}/{project}/_apis/build/builds/{buildId}/artifacts` | 200 | The list was empty in that build (the route answers). |
| 26 | `azure_devops_get_my_identity` | `GET /{org}/_apis/connectionData` | 200 | Answers only on `api-version=7.0-preview.1` (7.1 answers **400**). The identity is in `authenticatedUser.id`. |
| 27 | `azure_devops_list_identities` | `GET /{org}/_apis/connectionData` | 200 | The same route: the identities come from the connection data. |
| 28 | `azure_devops_list_policies` | `GET /{org}/{project}/_apis/policy/configurations` | 200 | The **viable** route of policies with a classic PAT. |
| 29 | `azure_devops_list_release_definitions` | `GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions` | 200 | Envelope `{count, value}`; the path needs the segment of the organization **and** of the project. |
| 30 | `azure_devops_list_releases` | `GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases` | 200 | Envelope `{count, value}`. |
| 31 | `azure_devops_get_release` | `GET https://vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{releaseId}` | not exercised | The route of the releases answers 200; this exact path was not called. |

Supplementary observations of the verification:

| Route | Code | Contract note |
|---|---|---|
| `GET /{org}/{project}/_apis/wiki/wikis` | 200 | The list of the wikis of a project (empty in the project of the reference). |
| `POST /{org}/{project}/_apis/wit/wiql` without a body | 411 | The route requires a body. |
| `GET /{org}/{project}/_apis/wit/wiql` | 405 | The route only answers a POST. |

## Routes that did not answer

| Route | Code | What happened |
|---|---|---|
| `GET /{org}/{project}/_apis/policies/repositories/{repoId}` | **401** (PAT of minimum scopes) / **404** (PAT of full scope) | The route exists, but the authorization of the service of policies refuses the classic PAT. **Policies by repository are out of the scope of v1**: the tool reads the policy configurations of the project (`/_apis/policy/configurations`), and says so in every answer. |
| `GET /{org}/{project}/_apis/git/repositories/{repoId}/labels` | **404** | A label is a concept of the **pull request**; the repository has no such route. The labels are read from `.../pullRequests/{id}/labels`. |
| `GET /{org}/_apis/connectionData` with `api-version=7.1` | **400** | The endpoint requires a **preview** version (`7.0-preview.1` in the reference organization). The version of the API is per endpoint, and the client has a table of overrides. |

## What the verification changed in the design

1. **Policies of a repository leave the scope of v1.** The route exists, but a
   classic PAT does not reach it (401 with minimum scopes, 404 with full
   scope — the service of policies does not authorize a PAT). What answers is
   `policy/configurations`, the policy configurations of the project, with 200
   and a PAT of minimum scope. The tool of policies reads that route and
   warns that the reading by repository is not reachable with a PAT.
2. **The version of the API is per endpoint.** `connectionData` demands a
   preview version (`7.1` answers 400). The client keeps a table of overrides,
   with `7.1` as the default.
3. **Paging and filters have specific names.** Builds page by `$top` and
   answer the token in the header `x-ms-continuationtoken` (a `top` without the
   dollar sign is ignored — a pagination silently broken); commits take the
   branch as the short name (`refs/heads/master` answers 404); the wiki
   demands the project that owns it, taken from the `remoteUrl`.

Write routes (`POST`, `PATCH`, `PUT`, `DELETE`) were **not** exercised: the
verification was read only, so the reference organization was not dirtied.

## Verificação a partir do hostgator (2026-11-17)

The same battery of routes was repeated **from the hostgator**, because the
network path of the host can differ from the one of the development machine.

| | |
|---|---|
| Date | 2026-11-17 (UTC) |
| Host | `hubcredito-agent` (egress `129.121.50.54`) |
| Machine of comparison | `Lucass-MacBook-Pro-383.local` (egress `187.36.129.212`) |
| Organization | `IntegracaoFinanceira` |
| Project / repository | `Financeiro Api` / `administracao-api` (`ingestao-dados` for the pull request routes) |
| Credential | **none** — the PAT is not in the host profile yet |

Because the PAT is not in the host profile, each route was called twice, with
`curl` and the headers of the plugin:

- **with the headers of the plugin and no PAT** (`Authorization: Basic <empty>`,
  `Accept: application/json`): the organization redirects to the sign-in page
  (**302**);
- **with the redirect suppressed** (`X-TFS-FedAuthRedirect: Suppress`): the API
  answers the real status of the credential (**401**).

**401 is a missing credential, not a broken route.** The plugin does not even
reach the API without the PAT: `check_fn` marks the tool as "needs auth" and
the handler answers `missing_credential`.

| Route | Hostgator | Mac | Note |
|---|---|---|---|
| `GET /{org}/_apis/projects` | 302 / **401** | 302 / 401 | The list is of the **organization**. |
| `GET /{org}/_apis/projects/{project}` | 302 / **401** | 302 / 401 | The project by name. |
| `GET /{org}/{project}/_apis/git/repositories` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/build/definitions` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/build/builds?%24top=1` | 302 / **401** | 302 / 401 | The paging parameter travels encoded (`%24top`). |
| `GET /{org}/{project}/_apis/build/builds/{buildId}` | 302 / **401** | 302 / 401 | The id is a placeholder: without a PAT the builds cannot be enumerated. |
| `GET /{org}/{project}/_apis/build/builds/{buildId}/changes` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/build/builds/{buildId}/timeline` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/build/builds/{buildId}/artifacts` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/pullrequests?status=active` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{pullRequestId}` | 302 / **401** | 302 / 401 | A real pull request of the reference organization (3126). |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{pullRequestId}/threads` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{pullRequestId}/labels` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/labels` | 302 / **401** | 302 / 401 | The route that answers 404 with a PAT stays hidden behind the credential. |
| `POST /{org}/{project}/_apis/wit/wiql` (with body) | 302 / **401** | 302 / 401 | The route only answers a POST. |
| `GET /{org}/_apis/wit/workitems/{id}` | 302 / **401** | 302 / 401 | A real work item of the reference organization (674). |
| `GET /{org}/_apis/wit/workitems?ids={id}` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/_apis/wiki/wikis` | 302 / **401** | 302 / 401 | The list is of the **organization**. |
| `GET /{org}/{project}/_apis/wiki/wikis` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/wiki/wikis/{wikiId}/pages` | 302 / **401** | 302 / 401 | The wiki id is a placeholder: without a PAT the wikis cannot be enumerated. |
| `GET /{org}/{project}/_apis/wiki/wikis/{wikiId}/pages?path=/Home` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/refs?filter=heads` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/refs/heads/master` | 302 / **401** | 302 / 401 | The branch is the **short name**. |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/commits` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/commits/{commitId}` | 302 / **401** | 302 / 401 | A real commit of the reference organization. |
| `GET /{org}/{project}/_apis/git/repositories/{repo}/refs?filter=tags` | 302 / **401** | 302 / 401 | — |
| `GET /{org}/_apis/connectionData?api-version=7.0-preview.1` | **200** | 200 | The only route of the set that answers **without** a PAT: the identity of the connection is public. |
| `GET /{org}/_apis/connectionData?api-version=7.1` | **400** | 400 | The version of the API is per endpoint: `7.1` is refused, as recorded above. |
| `GET /{org}/{project}/_apis/policy/configurations` | 302 / **401** | 302 / 401 | The viable route of policies with a PAT. |
| `GET /{org}/{project}/_apis/policies/repositories/{repo}` | **404** | 404 | Same answer as in the planning: the route does not reach a classic PAT. |
| `GET vsrm.dev.azure.com/{org}/{project}/_apis/release/definitions` | 302 / **401** | 302 / 401 | — |
| `GET vsrm.dev.azure.com/{org}/{project}/_apis/release/releases` | 302 / **401** | 302 / 401 | — |
| `GET vsrm.dev.azure.com/{org}/{project}/_apis/release/releases/{releaseId}` | 302 / **401** | 302 / 401 | The id is a placeholder: without a PAT the releases cannot be enumerated. |
| `POST /{org}/{project}/_apis/wit/wiql` (without body) | **411** | 411 | The route requires a body — the contract of the planning verification. |
| `GET /{org}/{project}/_apis/wit/wiql` | **405** | 405 | The route only answers a POST. |

**Result:** the 38 routes answered **with the same code** on the hostgator and
on the development machine (the two outputs of the probe are identical, route by
route). No route failed because of the network path: the host reaches
`dev.azure.com` and `vsrm.dev.azure.com` and receives the same answers,
including the known traps (400 of `connectionData` on `7.1`, 404 of the
policies by repository, 411 of the WIQL without body, 405 of the WIQL on GET).

The authenticated answers (the 200 of the planning) are still **pending**: they
need the PAT in the profile of the host, which the user will configure. The
smoke of reading on the host is therefore blocked by the credential, not by the
routes.

## Builds: filtros de data não são suportados pela API

Verificado em 2026-11-17: os parâmetros `minFinishTime`/`maxFinishTime` da rota
`/{project}/_apis/build/builds` são **ignorados em silêncio** pela API — a resposta
é idêntica com e sem eles. O único filtro de data de builds possível é **client-side**
(buscar os mais recentes com `$top` e filtrar por `finishTime`/`queueTime`), que é o
que o plugin faz.
