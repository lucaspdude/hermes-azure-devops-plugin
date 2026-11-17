"""Tools of pull requests (read only).

The routes are the ones verified against the real API: the pull requests of a
repository (``/{project}/_apis/git/repositories/{repoId}/pullrequests``), one
pull request, its comment threads and its labels.

Two contracts of the verification live here:

* the filter of status travels as ``searchCriteria.status`` — the route does
  not read a plain ``status`` parameter;
* a label is a concept of the **pull request**: the repository has no label
  route, so the labels are read from ``.../pullRequests/{id}/labels``.

The repository is optional: when the project has a single Git repository, the
plugin resolves it instead of making the model repeat it. The argument is
called ``repository`` (``repositoryId`` is accepted as an alias).
"""

from typing import Any

from .client import decode_json
from .contracts import page_params
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

#: The statuses the pull request route accepts in ``searchCriteria.status``.
PULL_REQUEST_STATUSES = ("active", "abandoned", "completed", "all")


def handle_list_pull_requests(args: dict, **kwargs) -> dict[str, Any]:
    """The pull requests of a repository, filtered by status."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    status = _status_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    params["searchCriteria.status"] = status
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/pullrequests",
        params=params,
    )
    payload = decode_json(response)
    return {
        "pullRequests": [_pull_request(item) for item in list_items(payload)],
        "continuationToken": extract_continuation_token(response),
    }


def handle_get_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """One pull request of a repository, by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    pull_request_id = _pull_request_id_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request_id}"
    )
    payload = decode_json(response)
    return {"pullRequest": _pull_request(payload)}


def handle_list_pull_request_comments(args: dict, **kwargs) -> dict[str, Any]:
    """The comment threads of a pull request."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    pull_request_id = _pull_request_id_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/"
        f"{pull_request_id}/threads"
    )
    payload = decode_json(response)
    threads = [_thread(item) for item in list_items(payload)]
    return {"comments": threads, "count": len(threads)}


def handle_list_pull_request_labels(args: dict, **kwargs) -> dict[str, Any]:
    """The labels of a pull request."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    pull_request_id = _pull_request_id_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    response = adoc.get(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/"
        f"{pull_request_id}/labels"
    )
    payload = decode_json(response)
    labels = [_label(item) for item in list_items(payload)]
    return {"labels": labels, "count": len(labels)}


def _status_arg(arguments: Any) -> str:
    """The status of the filter, checked against the statuses the API accepts."""
    value = text_arg(arguments, "status")
    if not value:
        return "active"
    for candidate in PULL_REQUEST_STATUSES:
        if candidate.lower() == value.lower():
            return candidate
    raise AdoError(
        CODE_INVALID_INPUT,
        f"The status {value!r} is not one of: " + ", ".join(PULL_REQUEST_STATUSES) + ".",
    )


def _pull_request_id_arg(arguments: Any) -> str:
    """The id of the pull request the call is about."""
    pull_request_id = text_arg(arguments, "pullRequestId")
    if not pull_request_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the pull request (pullRequestId) the call is about.",
        )
    return pull_request_id


def _pull_request(item: Any) -> dict[str, Any]:
    """The fields of a pull request the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "pullRequestId": source.get("pullRequestId"),
        "title": source.get("title"),
        "description": source.get("description"),
        "status": source.get("status"),
        "isDraft": source.get("isDraft"),
        "creationDate": source.get("creationDate"),
        "closedDate": source.get("closedDate"),
        "sourceRefName": source.get("sourceRefName"),
        "targetRefName": source.get("targetRefName"),
        "mergeStatus": source.get("mergeStatus"),
        "url": source.get("url"),
        "createdBy": _person(source.get("createdBy")),
        "reviewers": [_reviewer(item) for item in _items(source.get("reviewers"))],
    }


def _thread(item: Any) -> dict[str, Any]:
    """The fields of a comment thread the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "status": source.get("status"),
        "publishedDate": source.get("publishedDate"),
        "lastUpdatedDate": source.get("lastUpdatedDate"),
        "threadContext": source.get("threadContext"),
        "comments": [_comment(item) for item in _items(source.get("comments"))],
    }


def _comment(item: Any) -> dict[str, Any]:
    """The fields of a comment the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "content": source.get("content"),
        "commentType": source.get("commentType"),
        "publishedDate": source.get("publishedDate"),
        "lastUpdatedDate": source.get("lastUpdatedDate"),
        "author": _person(source.get("author")),
    }


def _label(item: Any) -> dict[str, Any]:
    """The fields of a label the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "active": source.get("active"),
    }


def _reviewer(item: Any) -> dict[str, Any]:
    """The fields of a reviewer the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "displayName": source.get("displayName"),
        "isRequired": source.get("isRequired"),
        "vote": source.get("vote"),
    }


def _person(item: Any) -> dict[str, Any]:
    """A person of the API: the id and the display name."""
    source = item if isinstance(item, dict) else {}
    return {"id": source.get("id"), "displayName": source.get("displayName")}


def _items(value: Any) -> list[Any]:
    """A list of the API, or an empty one when the field is not a list."""
    if isinstance(value, list):
        return value
    return []


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_pull_requests",
        "List the pull requests of a repository, filtered by status (active, abandoned, "
        "completed, all). Use it to see what is open or what was merged.",
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
                "status": {
                    "type": "string",
                    "enum": list(PULL_REQUEST_STATUSES),
                    "description": "Status of the pull requests to return. Defaults to active.",
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of pull requests in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_pull_requests,
    ),
    tool_spec(
        "azure_devops_get_pull_request",
        "Get one pull request of a repository by id, with its status, branches, dates and "
        "reviewers. Use it to inspect a pull request you already found.",
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
                "pullRequestId": {
                    "type": "integer",
                    "description": "Id of the pull request.",
                },
            },
            "required": ["pullRequestId"],
        },
        handle_get_pull_request,
    ),
    tool_spec(
        "azure_devops_list_pull_request_comments",
        "List the comment threads of a pull request, with their author, text, status and dates. "
        "Use it to read the discussion of a pull request.",
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
                "pullRequestId": {
                    "type": "integer",
                    "description": "Id of the pull request.",
                },
            },
            "required": ["pullRequestId"],
        },
        handle_list_pull_request_comments,
    ),
    tool_spec(
        "azure_devops_list_pull_request_labels",
        "List the labels of a pull request. Use it to read how a pull request was categorized.",
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
                "pullRequestId": {
                    "type": "integer",
                    "description": "Id of the pull request.",
                },
            },
            "required": ["pullRequestId"],
        },
        handle_list_pull_request_labels,
    ),
]
