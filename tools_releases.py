"""Tools of the releases (read only).

The routes of Release Management do not exist on the API host: they answer on
``vsrm.dev.azure.com``. The client chooses the host by the path
(``/_apis/release/``), so the tools only have to mount the path — and the path
carries the segment of the organization **and** of the project: the
definitions route answers 404 without the project.

The filter of the releases route wants the **id** of the release definition,
so a name is resolved against the definitions of the project before the
releases are listed (the same rule the builds route follows).
"""

from typing import Any

from .client import decode_json
from .contracts import page_params
from .errors import CODE_INVALID_INPUT, CODE_NOT_FOUND, AdoError
from .pagination import extract_continuation_token
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


def handle_list_release_definitions(args: dict, **kwargs) -> dict[str, Any]:
    """The release definitions of a project."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    name = text_arg(arguments, "name")
    if name:
        params["definitionName"] = name
        params["isExactNameMatch"] = "false"
    response = adoc.get(f"/{project}/_apis/release/definitions", params=params)
    payload = decode_json(response)
    definitions = [_definition(item) for item in list_items(payload)]
    if name:
        definitions = [item for item in definitions if _matches(item.get("name"), name)]
    return {
        "definitions": definitions,
        "count": len(definitions),
        "continuationToken": extract_continuation_token(response),
    }


def handle_list_releases(args: dict, **kwargs) -> dict[str, Any]:
    """The releases of a project, optionally of one release definition."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    definition = text_arg(arguments, "definition")
    if definition:
        params["definitionId"] = _definition_id(adoc, project, definition)
    response = adoc.get(f"/{project}/_apis/release/releases", params=params)
    payload = decode_json(response)
    releases = [_release(item) for item in list_items(payload)]
    return {
        "releases": releases,
        "count": len(releases),
        "continuationToken": extract_continuation_token(response),
    }


def handle_get_release(args: dict, **kwargs) -> dict[str, Any]:
    """One release of a project, by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    release_id = _release_id_arg(arguments)
    params: dict[str, str] = {}
    definition = text_arg(arguments, "definition")
    if definition:
        params["definitionId"] = _definition_id(adoc, project, definition)
    response = adoc.get(f"/{project}/_apis/release/releases/{release_id}", params=params)
    payload = decode_json(response)
    return {"release": _release(payload)}


def _definition_id(adoc: Any, project: str, definition: str) -> str:
    """The id of the release definition the model named: the id itself, or the name resolved.

    The ``definitionId`` filter of the releases route wants the id of the
    definition, so a name is resolved against the definitions of the project
    before the releases are listed.
    """
    if definition.isdigit():
        return definition
    response = adoc.get(
        f"/{project}/_apis/release/definitions",
        params={"definitionName": definition, "isExactNameMatch": "false"},
    )
    payload = decode_json(response)
    candidates = list_items(payload)
    exact = [
        item
        for item in candidates
        if str(item.get("name") or "").strip().lower() == definition.lower()
    ]
    matches = exact or [
        item
        for item in candidates
        if str(item.get("name") or "").strip().lower().startswith(definition.lower())
    ]
    if not matches:
        raise AdoError(
            CODE_NOT_FOUND,
            f"There is no release definition named {definition!r} in the project {project!r}.",
        )
    if len(matches) > 1:
        names = ", ".join(str(item.get("name") or item.get("id")) for item in matches)
        raise AdoError(
            CODE_INVALID_INPUT,
            f"More than one release definition matches {definition!r} ({names}): name the "
            "definition by id.",
        )
    identifier = matches[0].get("id")
    if identifier is None:
        raise AdoError(
            CODE_NOT_FOUND,
            f"The release definition named {definition!r} does not carry an id.",
        )
    return str(identifier)


def _release_id_arg(arguments: Any) -> str:
    """The id of the release the call is about."""
    release_id = text_arg(arguments, "releaseId")
    if not release_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the release (releaseId) the call is about.",
        )
    return release_id


def _matches(name: Any, wanted: str) -> bool:
    """Whether a name carries the text the model asked for."""
    return wanted.lower() in str(name or "").lower()


def _definition(item: Any) -> dict[str, Any]:
    """The fields of a release definition the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "path": source.get("path"),
        "releaseType": source.get("releaseType"),
        "url": source.get("url"),
    }


def _release(item: Any) -> dict[str, Any]:
    """The fields of a release the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "status": source.get("status"),
        "createdOn": source.get("createdOn"),
        "modifiedOn": source.get("modifiedOn"),
        "definition": _summary(source.get("definition")),
        "environments": [_environment(entry) for entry in _environments(source)],
        "url": source.get("url"),
    }


def _environments(source: dict[str, Any]) -> list[Any]:
    """The environments of a release, wherever the payload carries them."""
    environments = source.get("environments")
    if isinstance(environments, list):
        return environments
    return []


def _environment(item: Any) -> dict[str, Any]:
    """The fields of an environment of a release the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "status": source.get("status"),
        "rank": source.get("rank"),
    }


def _summary(item: Any) -> dict[str, Any]:
    """A reference of the API: the id and the name, nothing else."""
    source = item if isinstance(item, dict) else {}
    return {"id": source.get("id"), "name": source.get("name")}


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_release_definitions",
        "List the release definitions of a project, with id, name and path.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Only the definitions whose name carries this text.",
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of definitions in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_release_definitions,
    ),
    tool_spec(
        "azure_devops_list_releases",
        "List the releases of a project, optionally of one release definition (id or name).",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "definition": {
                    "type": "string",
                    "description": (
                        "Release definition the releases belong to, by id or by name (a name is "
                        "resolved to its id before the call)."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of releases in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_releases,
    ),
    tool_spec(
        "azure_devops_get_release",
        "Get one release of a project, with its status, its definition and its environments.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "releaseId": {
                    "type": "integer",
                    "description": "Id of the release.",
                },
                "definition": {
                    "type": "string",
                    "description": (
                        "Release definition the release belongs to, by id or by name (a name is "
                        "resolved to its id before the call)."
                    ),
                },
            },
            "required": ["releaseId"],
        },
        handle_get_release,
    ),
]
