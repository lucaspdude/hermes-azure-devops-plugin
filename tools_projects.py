"""Tools of projects and Git repositories (read only).

The routes are the ones verified against the real API: the projects of the
organization (``/_apis/projects``) and the repositories of a project
(``/{project}/_apis/git/repositories``).
"""

from typing import Any

from .client import decode_json
from .contracts import page_params
from .errors import CODE_INVALID_INPUT, AdoError
from .pagination import extract_continuation_token, normalize_page
from .registry import ToolSpec
from .toolkit import (
    args_of,
    client_for,
    int_arg,
    list_items,
    project_arg,
    text_arg,
    tool_spec,
)


def handle_list_projects(args: dict, **kwargs) -> dict[str, Any]:
    """The projects of the organization."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    response = adoc.get("/_apis/projects", params=params)
    payload = decode_json(response)
    page = normalize_page(payload, extract_continuation_token(response))
    return {
        "projects": [_project(item) for item in list_items(payload)],
        "continuationToken": page["continuationToken"],
    }


def handle_get_project(args: dict, **kwargs) -> dict[str, Any]:
    """One project, by name or by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    response = adoc.get(f"/_apis/projects/{project}")
    payload = decode_json(response)
    return {"project": _project(payload)}


def handle_list_repositories(args: dict, **kwargs) -> dict[str, Any]:
    """The Git repositories of a project."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    response = adoc.get(f"/{project}/_apis/git/repositories", params=params)
    payload = decode_json(response)
    page = normalize_page(payload, extract_continuation_token(response))
    return {
        "repositories": [_repository(item) for item in list_items(payload)],
        "continuationToken": page["continuationToken"],
    }


def handle_get_repository(args: dict, **kwargs) -> dict[str, Any]:
    """One Git repository of a project, by id or by name."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = text_arg(arguments, "repository")
    if not repository:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the repository (id or name) the call is about.",
        )
    response = adoc.get(f"/{project}/_apis/git/repositories/{repository}")
    payload = decode_json(response)
    return {"repository": _repository(payload)}


def _project(item: Any) -> dict[str, Any]:
    """The fields of a project the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "description": source.get("description"),
        "state": source.get("state"),
    }


def _repository(item: Any) -> dict[str, Any]:
    """The fields of a repository the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "url": source.get("url"),
        "defaultBranch": source.get("defaultBranch"),
        "size": source.get("size"),
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_projects",
        "List the projects of the Azure DevOps organization, with id, name and state. Use it to find the project a later call is about.",
        {
            "type": "object",
            "properties": {
                "top": {
                    "type": "integer",
                    "description": "Maximum number of projects to return in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_projects,
    ),
    tool_spec(
        "azure_devops_get_project",
        "Get one project of the Azure DevOps organization, by name or by id. Use it to confirm a project exists or to read its details.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Name or id of the project.",
                }
            },
            "required": ["project"],
        },
        handle_get_project,
    ),
    tool_spec(
        "azure_devops_list_repositories",
        "List the Git repositories of a project, with id, name, url and default branch. Use it to find the repository a later call is about.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of repositories to return in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_repositories,
    ),
    tool_spec(
        "azure_devops_get_repository",
        "Get one Git repository of a project, by id or by name. Use it to read the details of a repository you already know.",
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
                    "description": "Id or name of the repository.",
                },
            },
            "required": ["repository"],
        },
        handle_get_repository,
    ),
]
