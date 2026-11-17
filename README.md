# hermes-azure-devops-plugin

Azure DevOps for the [Hermes Agent](https://github.com/NousResearch/hermes-agent):
the agent reads and changes projects, repositories, builds, pull requests, work
items, wikis and releases through **44 native tools**, with a Desktop panel of
your own activity and an embedded guide that tells the model which PAT scope
each operation needs.

Native Hermes plugin (Python, in-process). No MCP server, no sidecar process.

## Tools

| `azure_devops_list_projects` | List the projects of the Azure DevOps organization, with id, name and state. |
| `azure_devops_get_project` | Get one project of the Azure DevOps organization, by name or by id. |
| `azure_devops_list_repositories` | List the Git repositories of a project, with id, name, url and default branch. |
| `azure_devops_get_repository` | Get one Git repository of a project, by id or by name. |
| `azure_devops_list_build_definitions` | List the build definitions (pipelines) of a project, with id, name, path and queue status. |
| `azure_devops_list_builds` | List the builds of a project, filtered by status and by definition (id or name). |
| `azure_devops_get_build` | Get one build of a project by id, with its status, result, times and definition. |
| `azure_devops_get_build_changes` | List the changes of a build: the files it touched and the commits it carried. |
| `azure_devops_get_build_timeline` | Get the timeline of a build: its steps and tasks, with their times and results. |
| `azure_devops_list_pull_requests` | List the pull requests of a repository, filtered by status (active, abandoned, completed, all). |
| `azure_devops_get_pull_request` | Get one pull request of a repository by id, with its status, branches, dates and reviewers. |
| `azure_devops_list_pull_request_comments` | List the comment threads of a pull request, with their author, text, status and dates. |
| `azure_devops_list_pull_request_labels` | List the labels of a pull request. |
| `azure_devops_create_pull_request` | Open a pull request from one branch into another. |
| `azure_devops_add_pull_request_comment` | Comment on a pull request: opens a new thread, or replies into one when threadId is given. |
| `azure_devops_add_pull_request_label` | Attach a label to a pull request, creating the label when it is absent. |
| `azure_devops_remove_pull_request_label` | Detach a label from a pull request (the label definition itself stays). |
| `azure_devops_approve_pull_request` | Approve a pull request (vote 10) as the identity that owns the PAT. |
| `azure_devops_reject_pull_request` | Reject a pull request (vote 5) as the identity that owns the PAT. |
| `azure_devops_reset_pull_request_vote` | Reset the vote of the identity that owns the PAT back to no vote. |
| `azure_devops_abandon_pull_request` | Abandon a pull request (close it without merging). |
| `azure_devops_complete_pull_request` | Complete (merge) a pull request, optionally squashing and deleting the source branch. |
| `azure_devops_update_work_item` | Change fields of a work item through a JSON Patch list of operations. |
| `azure_devops_create_wiki_page` | Create a wiki page with content at a path. |
| `azure_devops_update_wiki_page` | Replace the content of an existing wiki page (pass the current version). |
| `azure_devops_queue_build` | Queue a build of a pipeline definition on a branch. |
| `azure_devops_query_wiql` | Run a WIQL query and get the ids of the work items it finds. |
| `azure_devops_get_work_item` | Get one work item by id, with its type, title and state (and the other fields asked for). |
| `azure_devops_list_work_items` | List work items by type or by ids. |
| `azure_devops_list_wikis` | List the wikis of the organization, with the project that owns each one. |
| `azure_devops_list_wiki_pages` | List the pages of a wiki, in the project that owns it. |
| `azure_devops_get_wiki_page` | Get one page of a wiki, with its content and the date of its last change. |
| `azure_devops_list_branches` | List the branches of a repository, with the commit each one points to. |
| `azure_devops_get_branch` | Get one branch of a repository, by name, with the commit it points to. |
| `azure_devops_list_commits` | List the commits of a repository, of one branch or of all of them. |
| `azure_devops_get_commit` | Get one commit of a repository, by id, with its author, message and changed files. |
| `azure_devops_list_tags` | List the tags of a repository, with the commit each one points to. |
| `azure_devops_list_build_artifacts` | List the artifacts a build published, with the name, the size and the download url. |
| `azure_devops_get_my_identity` | Get the identity of the user the PAT belongs to, with its id and display name. |
| `azure_devops_list_identities` | List the identities of the organization, with id, display name and descriptor. |
| `azure_devops_list_policies` | List the policy configurations of a project (branch expiration, minimum review, . |
| `azure_devops_list_release_definitions` | List the release definitions of a project, with id, name and path. |
| `azure_devops_list_releases` | List the releases of a project, optionally of one release definition (id or name). |
| `azure_devops_get_release` | Get one release of a project, with its status, its definition and its environments. |

## What it does

| Family | Tools |
|---|---|
| Projects and repositories | list/get projects, list/get repositories |
| Builds | definitions, list builds (paged), get build, changes, timeline, artifacts, queue build |
| Pull requests | list/get, comments, labels (add/remove), votes (approve/reject/reset), abandon, complete, create |
| Work items | WIQL query, get, list, update (JSON Patch) |
| Wiki | list wikis/pages, get page, create/update page |
| Git refs | branches, commits, tags |
| Release | definitions, releases, get release |
| Identity | authenticated user, organization identities |
| Policies | policy configurations of a project |

Writes are explicit: every tool that changes state says so in its description,
answers with the id (and url) of the object it touched, and is **never retried**
(a repeated create would open a second pull request).

## Install

```bash
hermes plugins install lucaspdude/hermes-azure-devops-plugin
```

Or from a local checkout (the way the development host does it):

```bash
rsync -az --delete --exclude .git --exclude __pycache__ ./ host:/root/.hermes/plugins/azure-devops/
hermes plugins enable azure-devops
```

## Configure

| Setting | Default | Meaning |
|---|---|---|
| `organization` | *(required, no default)* | The Azure DevOps organization — the plugin is generic and never guesses one. |
| `base_url` | `https://dev.azure.com` | Change for a sovereign cloud or on-premises server. |
| `api_version` | `7.1` | REST API version (preview-only endpoints are pinned by the plugin). |
| `default_project` | *(empty)* | Project used when a tool is called without one. |
| `http_timeout_ms` | `30000` | Timeout of each request. |

### Credential

The plugin reads the token **only** through the Hermes secret scope:

```
AZURE_DEVOPS_PAT_TOKEN=<your PAT>
```

Set it in the `*.env* of the active Hermes profile* (never in `config.yaml`).
The PAT must be **organization-scoped**; global PATs stop working on
**December 1st, 2026**. Grant only the scopes the operations need — the
embedded `/ado-help` lists the scope of every family (`vso.code`,
`vso.build`, `vso.work`, `vso.project`, `vso.release`, `vso.wiki`,
`vso.identity`).

## Help inside the conversation

```
/ado-help              # the whole guide
/ado-help pull requests   # highlights one section
```

The same text answers to `hermes azure-devops help` in a terminal, and ships
as two embedded skills (`azure-devops-usage`, `azure-devops-workflows`) the
agent loads on demand.

## Desktop panel

When the desktop half is enabled (Capabilities → Plugins), the plugin
contributes an `/azure-devops` page with **your** activity — pull requests you
own or review, work items assigned to you, your recent builds — plus a sidebar
entry and a status bar chip. The panel is read-only; changes go through the
agent, where the Hermes approval flow applies. Tool writes invalidate the panel
by event; the page also polls, so a lost event converges on its own.

### Gates to know

1. The plugin must be in `plugins.enabled` — otherwise the panel backend is
   not mounted and the page explains it instead of rendering an empty screen.
2. The desktop half is opt-in at **Capabilities → Plugins** (app-level toggle).

## Troubleshooting

| Symptom | Cause | What to do |
|---|---|---|
| `missing_credential` on every call | the PAT is not in the profile | set `AZURE_DEVOPS_PAT_TOKEN` in the profile `.env` |
| `not_configured` | the organization setting is missing | set `organization` in the plugin settings |
| `forbidden` on votes | the PAT identity is not a reviewer, or lacks the scope | grant `vso.code_write` + `vso.identity`; votes are always the PAT owner's |
| `not_found` on a wiki page | the page was requested in the wrong project | the plugin resolves the owner project — list wikis first |
| `forbidden` completing a PR | a branch policy refuses it | the plugin reports the API message and does not bypass policies |
| the Desktop page says the backend is off | the plugin is not in `plugins.enabled` | enable it, then reload the desktop plugins |

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The suite is offline: every HTTP interaction runs on `httpx.MockTransport`,
and no test reads a credential. Run it with the interpreter of the host's
Hermes environment (it carries `httpx`).

## Disclosure

This plugin, when its tools are called:

- sends requests to `dev.azure.com` (and `vsrm.dev.azure.com` for Release
  Management) with the configured organization;
- reads the credential exclusively through `agent.secret_scope.get_secret`
  (the Hermes credential route) — never from `.env` directly, `auth.json`, or
  the process environment;
- changes Azure DevOps state when write tools are approved (pull requests,
  comments, labels, votes, work item updates, wiki pages, queued builds);
- never retries a write, never bypasses branch policies, and answers every
  failure inside a JSON envelope with the message of the API.

## License

MIT — see [LICENSE](./LICENSE).
