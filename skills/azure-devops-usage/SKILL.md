---
name: azure-devops-usage
description: The usage contract of the Azure DevOps plugin - PAT scopes per family, paging, error codes, ids vs names and the verified pitfalls.
---

# Azure DevOps plugin — usage contract

## PAT scopes per operation family

| Family | Read | Write |
|---|---|---|
| Code (repos, PRs, labels, threads, votes) | `vso.code` | `vso.code_write` |
| Build (definitions, builds, artifacts, queue) | `vso.build` | `vso.build_execute` |
| Work items (WIQL, work item update) | `vso.work` | `vso.work_write` |
| Project and team (projects, repositories) | `vso.project` | `vso.project_write` |
| Release (definitions, releases) | `vso.release` | `vso.release_execute` |
| Wiki (wikis, pages, edits) | `vso.wiki` | `vso.wiki_write` |
| Identity (authenticated user, votes) | `vso.identity` | `vso.identity_manage` |

A missing scope answers `forbidden` (403) with the message of the API. The
PAT must be **organization-scoped**; a global PAT stops working on
**December 1st, 2026** — create a new one scoped to the organization.

## Paging

Every listing answers a single `continuationToken` (empty when there is no
next page). Send it back to get the following page, together with `top`
(the page size; the plugin encodes it as the API expects, `$top`). The token
of the builds route travels in the `x-ms-continuationtoken` header — the
plugin normalizes it, do not look for the header.

## Error codes

| Code | Meaning | What to do |
|---|---|---|
| `not_configured` | a required setting is missing (usually the organization) | set the plugin settings |
| `missing_credential` | the PAT is not in the profile | set `AZURE_DEVOPS_PAT_TOKEN` in the profile |
| `invalid_input` | an argument is missing or has the wrong shape | fix the arguments |
| `unauthorized` | 401 from the API | the PAT is wrong or expired |
| `forbidden` | 403 — the PAT lacks the scope, or the identity cannot act | grant the scope of the family (see the table above) |
| `not_found` | 404 — the object does not exist, or the route needs another path shape | check ids and names |
| `rate_limited` | 429 | retry later, the plugin never retries |
| `timeout` | the API did not answer inside `http_timeout_ms` | raise the setting or retry |
| `upstream_error` | 5xx, or a body the plugin could not parse | retry once; report if it persists |

## Ids vs names

- **Project**: name or id, both accepted.
- **Repository**: id (GUID) or name; optional when the project has a single
  repository.
- **Pull request**: numeric id only.
- **Build**: numeric id; the **definition** accepts id or name (resolved).
- **Wiki**: id or name; its pages only answer in the **project that owns it** —
  the plugin resolves the owner from the wiki listing.
- **Branch**: short name (`master`); a full ref (`refs/heads/master`) is
  accepted where the route expects a ref (pull requests) and rejected where it
  expects the short name (commits).

## Verified pitfalls

- Builds page by `$top`; a plain `top` parameter is silently ignored by the API.
- WIQL is **POST-only** (a GET answers 405) and always carries a JSON body.
- `connectionData` (the identity) answers on the **preview** API version; the
  plugin pins it, do not override `api_version` for it.
- Policies **per repository** are not reachable with a classic PAT; the plugin
  reads the **policy configurations of the project** instead.
- Release Management answers on `vsrm.dev.azure.com`, and the route needs the
  organization **and** the project segment — the plugin routes it.
- Labels are a **pull request** concept: the repository has no label route.
- Writes are **never retried**: a repeated create opens a second pull request.
