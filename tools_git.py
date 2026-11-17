"""Tools of the Git refs and commits (read only).

The routes are the ones verified against the real API: the refs of a
repository (``.../git/repositories/{repoId}/refs``), one branch
(``.../refs/heads/{branch}``), the commits (``.../commits``) and one commit
(``.../commits/{commitId}``).

Two contracts of the verification live here:

* the branch of the commits route is the **short name** (``master``): the full
  ref (``refs/heads/master``) answers 404;
* the page size of the commits route travels as ``$top`` — a ``top`` without
  the dollar sign is ignored and the pagination breaks silently.
"""

from typing import Any

from .client import decode_json
from .contracts import page_params, short_branch
from .errors import CODE_INVALID_INPUT, AdoError
from .pagination import extract_continuation_token
from .registry import ToolSpec
from .toolkit import (
    args_of,
    client_for,
    int_arg,
    list_items,
    project_arg,
    repository_arg,
    text_arg,
    tool_spec,
)

#: The prefix of the refs of the tags.
TAG_PREFIX = "refs/tags/"


def handle_list_branches(args: dict, **kwargs) -> dict[str, Any]:
    """The branches of a repository."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    params["filter"] = "heads"
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/refs",
        params=params,
    )
    payload = decode_json(response)
    branches = [_ref(item) for item in list_items(payload)]
    return {
        "branches": branches,
        "count": len(branches),
        "continuationToken": extract_continuation_token(response),
    }


def handle_get_branch(args: dict, **kwargs) -> dict[str, Any]:
    """One branch of a repository, by name."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    branch = _branch_arg(arguments)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/refs/heads/{branch}"
    )
    payload = decode_json(response)
    return {"branch": _ref(payload)}


def handle_list_commits(args: dict, **kwargs) -> dict[str, Any]:
    """The commits of a repository, optionally of one branch."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    branch = text_arg(arguments, "branch")
    if branch:
        params["branch"] = short_branch(branch)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/commits",
        params=params,
    )
    payload = decode_json(response)
    commits = [_commit(item) for item in list_items(payload)]
    return {
        "commits": commits,
        "count": len(commits),
        "continuationToken": extract_continuation_token(response),
    }


def handle_get_commit(args: dict, **kwargs) -> dict[str, Any]:
    """One commit of a repository, by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    commit_id = _commit_id_arg(arguments)
    params: dict[str, str] = {}
    change_count = int_arg(arguments, "changeCount")
    if change_count is not None:
        params["changeCount"] = str(change_count)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/commits/{commit_id}",
        params=params,
    )
    payload = decode_json(response)
    return {"commit": _commit(payload)}


def handle_list_tags(args: dict, **kwargs) -> dict[str, Any]:
    """The tags of a repository."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    params["filter"] = "tags"
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/refs",
        params=params,
    )
    payload = decode_json(response)
    tags = [_ref(item) for item in list_items(payload)]
    return {
        "tags": tags,
        "count": len(tags),
        "continuationToken": extract_continuation_token(response),
    }


def _branch_arg(arguments: Any) -> str:
    """The branch the call is about, as the short name the API expects."""
    branch = text_arg(arguments, "branch")
    if not branch:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the branch the call is about.",
        )
    return short_branch(branch)


def _commit_id_arg(arguments: Any) -> str:
    """The id of the commit the call is about."""
    commit_id = text_arg(arguments, "commitId")
    if not commit_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the commit (commitId) the call is about.",
        )
    return commit_id


def _ref(item: Any) -> dict[str, Any]:
    """The fields of a ref (a branch or a tag) the agent works with."""
    source = item if isinstance(item, dict) else {}
    name = str(source.get("name") or "")
    return {
        "name": _short_ref(name),
        "ref": name,
        "objectId": source.get("objectId"),
        "url": source.get("url"),
    }


def _short_ref(name: str) -> str:
    """The short name of a ref: ``master`` of ``refs/heads/master``."""
    text = str(name or "").strip()
    if text.startswith(TAG_PREFIX):
        return text[len(TAG_PREFIX) :]
    return short_branch(text)


def _commit(item: Any) -> dict[str, Any]:
    """The fields of a commit the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "commitId": source.get("commitId"),
        "comment": source.get("comment"),
        "author": _git_person(source.get("author")),
        "committer": _git_person(source.get("committer")),
        "changeCounts": source.get("changeCounts"),
        "commentCount": source.get("commentCount"),
        "url": source.get("url"),
    }


def _git_person(item: Any) -> dict[str, Any]:
    """The author of a commit: the name, the email and the date."""
    source = item if isinstance(item, dict) else {}
    return {
        "name": source.get("name"),
        "email": source.get("email"),
        "date": source.get("date"),
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_branches",
        "List the branches of a repository, with the commit each one points to.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Id or name of the repository. Optional when the project has a single "
                        "Git repository."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of branches in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_branches,
    ),
    tool_spec(
        "azure_devops_get_branch",
        "Get one branch of a repository, by name, with the commit it points to.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Id or name of the repository. Optional when the project has a single "
                        "Git repository."
                    ),
                },
                "branch": {
                    "type": "string",
                    "description": "Name of the branch, without the refs/heads/ prefix.",
                },
            },
            "required": ["branch"],
        },
        handle_get_branch,
    ),
    tool_spec(
        "azure_devops_list_commits",
        "List the commits of a repository, of one branch or of all of them.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Id or name of the repository. Optional when the project has a single "
                        "Git repository."
                    ),
                },
                "branch": {
                    "type": "string",
                    "description": (
                        "Branch the commits belong to, without the refs/heads/ prefix (the API "
                        "answers 404 for the full ref)."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of commits in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_commits,
    ),
    tool_spec(
        "azure_devops_get_commit",
        "Get one commit of a repository, by id, with its author, message and changed files.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Id or name of the repository. Optional when the project has a single "
                        "Git repository."
                    ),
                },
                "commitId": {
                    "type": "string",
                    "description": "Id of the commit.",
                },
                "changeCount": {
                    "type": "integer",
                    "description": "Number of changed files the answer carries.",
                },
            },
            "required": ["commitId"],
        },
        handle_get_commit,
    ),
    tool_spec(
        "azure_devops_list_tags",
        "List the tags of a repository, with the commit each one points to.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Id or name of the repository. Optional when the project has a single "
                        "Git repository."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of tags in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_tags,
    ),
]
