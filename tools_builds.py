"""Tools of builds and build definitions (read only).

The traps the endpoint verification found are encoded here, not spread over the
handlers:

* the page size of the builds route is ``$top`` — a ``top`` without the dollar
  sign is ignored by the API and the pagination breaks silently;
* the token of the next page of builds comes in the header
  ``x-ms-continuationtoken``, not in the body;
* the ``changes`` of a build answer in two formats — a bare array or the
  envelope ``{count, value}`` — and the plugin answers the same list in both;
* the ``timeline`` of a build answers the envelope ``{records}``;
* the ``definition`` filter of the builds route wants the **id** of the
  definition: a name has to be resolved before the call.
"""

import re
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

#: The statuses the builds route accepts in ``statusFilter``.
BUILD_STATUSES = (
    "all",
    "cancelling",
    "completed",
    "inProgress",
    "none",
    "notStarted",
    "postponed",
)

#: The id of a build definition is a GUID; anything else is a name.
_GUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def handle_list_build_definitions(args: dict, **kwargs) -> dict[str, Any]:
    """The build definitions (pipelines) of a project."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    name = text_arg(arguments, "name")
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    if name:
        params["name"] = name
    response = adoc.get(f"/{project}/_apis/build/definitions", params=params)
    payload = decode_json(response)
    definitions = [_definition(item) for item in list_items(payload)]
    if name:
        definitions = [item for item in definitions if _matches(item.get("name"), name)]
    return {
        "definitions": definitions,
        "continuationToken": extract_continuation_token(response),
    }


def handle_list_builds(args: dict, **kwargs) -> dict[str, Any]:
    """The builds of a project, filtered by status and by definition."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    params = page_params(
        int_arg(arguments, "top"),
        text_arg(arguments, "continuationToken"),
    )
    params["statusFilter"] = _status_arg(arguments, "status", BUILD_STATUSES, "all")
    definition = text_arg(arguments, "definition")
    if definition:
        params["definitions"] = _definition_id(adoc, project, definition)
    response = adoc.get(f"/{project}/_apis/build/builds", params=params)
    payload = decode_json(response)
    return {
        "builds": [_build(item) for item in list_items(payload)],
        "continuationToken": extract_continuation_token(response),
    }


def handle_get_build(args: dict, **kwargs) -> dict[str, Any]:
    """One build of a project, by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    build_id = _build_id_arg(arguments)
    response = adoc.get(f"/{project}/_apis/build/builds/{build_id}")
    payload = decode_json(response)
    return {"build": _build(payload)}


def handle_get_build_changes(args: dict, **kwargs) -> dict[str, Any]:
    """The changes of a build: the files and the commits it carried."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    build_id = _build_id_arg(arguments)
    response = adoc.get(f"/{project}/_apis/build/builds/{build_id}/changes")
    payload = decode_json(response)
    changes = [_change(item) for item in list_items(payload)]
    return {"changes": changes, "count": len(changes)}


def handle_get_build_timeline(args: dict, **kwargs) -> dict[str, Any]:
    """The timeline of a build: its steps and tasks."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    build_id = _build_id_arg(arguments)
    response = adoc.get(f"/{project}/_apis/build/builds/{build_id}/timeline")
    payload = decode_json(response)
    records = [_record(item) for item in _records(payload)]
    return {"timeline": records, "count": len(records)}


def _definition_id(adoc: Any, project: str, definition: str) -> str:
    """The id of the definition the model named: the id itself, or the name resolved.

    The ``definitions`` filter of the builds route wants the id of the
    definition, so a name is resolved against the definitions of the project
    before the builds are listed.
    """
    if _GUID.match(definition):
        return definition
    response = adoc.get(f"/{project}/_apis/build/definitions", params={"name": definition})
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
            f"There is no build definition named {definition!r} in the project {project!r}.",
        )
    if len(matches) > 1:
        names = ", ".join(str(item.get("name") or item.get("id")) for item in matches)
        raise AdoError(
            CODE_INVALID_INPUT,
            f"More than one build definition matches {definition!r} ({names}): name the "
            "definition by id.",
        )
    identifier = matches[0].get("id")
    if not identifier:
        raise AdoError(
            CODE_NOT_FOUND,
            f"The build definition named {definition!r} does not carry an id.",
        )
    return str(identifier)


def _status_arg(arguments: Any, name: str, allowed: tuple[str, ...], default: str) -> str:
    """The status of the filter, checked against the statuses the API accepts."""
    value = text_arg(arguments, name)
    if not value:
        return default
    for candidate in allowed:
        if candidate.lower() == value.lower():
            return candidate
    raise AdoError(
        CODE_INVALID_INPUT,
        f"The status {value!r} is not one of: " + ", ".join(allowed) + ".",
    )


def _build_id_arg(arguments: Any) -> str:
    """The id of the build the call is about."""
    build_id = text_arg(arguments, "buildId")
    if not build_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the build (buildId) the call is about.",
        )
    return build_id


def _records(payload: Any) -> list[Any]:
    """The records of a timeline: the envelope ``{records}``, or a bare array."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("records")
        if isinstance(records, list):
            return records
    return list_items(payload)


def _matches(name: Any, wanted: str) -> bool:
    """Whether a name carries the text the model asked for."""
    return wanted.lower() in str(name or "").lower()


def _definition(item: Any) -> dict[str, Any]:
    """The fields of a build definition the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "path": source.get("path"),
        "type": _summary(source.get("type")),
        "queueStatus": source.get("queueStatus"),
        "revision": source.get("revision"),
        "url": source.get("url"),
    }


def _build(item: Any) -> dict[str, Any]:
    """The fields of a build the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "buildNumber": source.get("buildNumber"),
        "status": source.get("status"),
        "result": source.get("result"),
        "queueTime": source.get("queueTime"),
        "startTime": source.get("startTime"),
        "finishTime": source.get("finishTime"),
        "sourceBranch": source.get("sourceBranch"),
        "sourceVersion": source.get("sourceVersion"),
        "definition": _summary(source.get("definition")),
        "requestedBy": _person(source.get("requestedBy")),
    }


def _change(item: Any) -> dict[str, Any]:
    """The fields of a change of a build the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("changeId") or source.get("id"),
        "changeType": source.get("changeType"),
        "comment": source.get("comment"),
        "sourceLabel": source.get("sourceLabel"),
        "targetLabel": source.get("targetLabel"),
        "date": source.get("date"),
        "author": _person(source.get("author")),
        "item": _changed_item(source.get("item")),
    }


def _changed_item(item: Any) -> dict[str, Any]:
    """The file a change touched."""
    source = item if isinstance(item, dict) else {}
    return {
        "path": source.get("path"),
        "changeType": source.get("changeType"),
        "isFolder": source.get("isFolder"),
    }


def _record(item: Any) -> dict[str, Any]:
    """The fields of a record of the timeline the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "type": source.get("type"),
        "name": source.get("name"),
        "state": source.get("state"),
        "result": source.get("result"),
        "startTime": source.get("startTime"),
        "finishTime": source.get("finishTime"),
        "errorCount": source.get("errorCount"),
        "warningCount": source.get("warningCount"),
    }


def _summary(item: Any) -> dict[str, Any]:
    """A reference of the API: the id and the name, nothing else."""
    source = item if isinstance(item, dict) else {}
    return {"id": source.get("id"), "name": source.get("name")}


def _person(item: Any) -> dict[str, Any]:
    """A person of the API: the id and the display name."""
    source = item if isinstance(item, dict) else {}
    return {"id": source.get("id"), "displayName": source.get("displayName")}


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_build_definitions",
        "List the build definitions (pipelines) of a project, with id, name, path and queue status. Use it to find the pipeline a build belongs to.",
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
                    "description": "Maximum number of definitions to return in this page.",
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_build_definitions,
    ),
    tool_spec(
        "azure_devops_list_builds",
        "List the builds of a project, filtered by status and by definition (id or name). Use it to see the recent builds of a project or of a pipeline.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "status": {
                    "type": "string",
                    "enum": list(BUILD_STATUSES),
                    "description": "Status of the builds to return. Defaults to all.",
                },
                "definition": {
                    "type": "string",
                    "description": (
                        "Build definition the builds belong to, by id or by name (a name is "
                        "resolved to its id before the call)."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": (
                        "Maximum number of builds in this page (the API answers up to 5000)."
                    ),
                },
                "continuationToken": {
                    "type": "string",
                    "description": "Token of the next page, taken from the previous answer.",
                },
            },
            "required": [],
        },
        handle_list_builds,
    ),
    tool_spec(
        "azure_devops_get_build",
        "Get one build of a project by id, with its status, result, times and definition. Use it to inspect a build you already found.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "buildId": {
                    "type": "integer",
                    "description": "Id of the build.",
                },
            },
            "required": ["buildId"],
        },
        handle_get_build,
    ),
    tool_spec(
        "azure_devops_get_build_changes",
        "List the changes of a build: the files it touched and the commits it carried. Use it to see what a build actually changed.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "buildId": {
                    "type": "integer",
                    "description": "Id of the build.",
                },
            },
            "required": ["buildId"],
        },
        handle_get_build_changes,
    ),
    tool_spec(
        "azure_devops_get_build_timeline",
        "Get the timeline of a build: its steps and tasks, with their times and results. Use it to see where a build failed or took long.",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "buildId": {
                    "type": "integer",
                    "description": "Id of the build.",
                },
            },
            "required": ["buildId"],
        },
        handle_get_build_timeline,
    ),
]
