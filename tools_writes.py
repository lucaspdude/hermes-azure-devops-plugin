"""Tools that change work items, wiki pages and queued builds.

The work item update goes through the JSON Patch route
(PATCH /_apis/wit/workitems/{id}, with the JSON Patch content type), the wiki
routes need the owner project of the wiki (resolved by the listing, as the
reads do) and queueing a build posts to /{project}/_apis/build/builds after
resolving a definition name.
"""

from typing import Any

from .errors import CODE_INVALID_INPUT, AdoError
from .registry import ToolSpec
from .toolkit import (
    args_of,
    client_for,
    int_arg,
    project_arg,
    text_arg,
    tool_spec,
)


def handle_update_work_item(args: dict, **kwargs) -> dict[str, Any]:
    """Change fields of a work item through a JSON Patch document."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    work_item = int_arg(arguments, "workItemId")
    if work_item is None:
        raise AdoError(CODE_INVALID_INPUT, "The parameter workItemId is required.")
    operations = arguments.get("operations")
    if not isinstance(operations, list) or not operations:
        raise AdoError(
            CODE_INVALID_INPUT,
            "The parameter operations must be a non-empty list of {op, path, value}.",
        )
    patch = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise AdoError(CODE_INVALID_INPUT, f"operations[{index}] must be an object.")
        op = text_arg(operation, "op")
        path = text_arg(operation, "path")
        if not op or not path:
            raise AdoError(CODE_INVALID_INPUT, f"operations[{index}] needs op and path.")
        patch.append({"op": op, "path": path, "value": operation.get("value")})
    response = adoc.patch(
        f"/_apis/wit/workitems/{work_item}",
        json=patch,
        headers={"Content-Type": "application/json-patch+json"},
    )
    updated = response.json()
    fields = updated.get("fields") or {}
    links = (updated.get("_links") or {})
    return {
        "workItemId": updated.get("id"),
        "rev": updated.get("rev"),
        "title": fields.get("System.Title"),
        "state": fields.get("System.State"),
        "url": (links.get("html") or links.get("self") or {}).get("href"),
    }


def handle_create_wiki_page(args: dict, **kwargs) -> dict[str, Any]:
    """Create a wiki page at a path (the wiki and its owner project by id or name)."""
    return _write_wiki_page(args, kwargs, create=True)


def handle_update_wiki_page(args: dict, **kwargs) -> dict[str, Any]:
    """Replace the content of an existing wiki page."""
    return _write_wiki_page(args, kwargs, create=False)


def handle_queue_build(args: dict, **kwargs) -> dict[str, Any]:
    """Queue a build of a pipeline definition (by id or name) on a branch."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    definition_id = int_arg(arguments, "definitionId")
    definition = arguments.get("definition")
    if definition_id is None and not isinstance(definition, (str, int)):
        raise AdoError(
            CODE_INVALID_INPUT,
            "Pass definitionId (integer) or definition (name or id).",
        )
    if definition_id is None:
        definition_id = _resolve_definition(adoc, project, str(definition))
    body: dict[str, Any] = {"definition": {"id": definition_id}}
    branch = text_arg(arguments, "branch") or "main"
    body["sourceBranch"] = branch if branch.startswith("refs/") else f"refs/heads/{branch}"
    variables = arguments.get("variables")
    if variables:
        if not isinstance(variables, dict):
            raise AdoError(CODE_INVALID_INPUT, "The parameter variables must be an object.")
        body["variables"] = {key: {"value": str(value)} for key, value in variables.items()}
    response = adoc.post(f"/{project}/_apis/build/builds", json=body)
    queued = response.json()
    return {
        "buildId": queued.get("id"),
        "buildNumber": queued.get("buildNumber"),
        "status": queued.get("status"),
        "queuePosition": queued.get("queuePosition"),
        "url": ((queued.get("_links") or {}).get("web") or {}).get("href"),
    }


def _write_wiki_page(args: dict, kwargs: dict, *, create: bool) -> dict[str, Any]:
    """Create or replace a page of a wiki, in the project that owns the wiki."""
    from .tools_wiki import _pages_path, _wiki_arg

    adoc = client_for(kwargs)
    arguments = args_of(args)
    wiki = _wiki_arg(adoc, arguments)
    page_path = text_arg(arguments, "path")
    content = text_arg(arguments, "content")
    if not page_path or not content:
        raise AdoError(
            CODE_INVALID_INPUT,
            "The parameters path and content are required.",
        )
    version = int_arg(arguments, "version", minimum=0)
    headers: dict[str, str] = {"Content-Type": "text/plain; charset=utf-8"}
    if create:
        response = adoc.put(
            _pages_path(adoc, wiki),
            params={"path": page_path},
            content=content,
            headers=headers,
        )
    else:
        if version is None:
            raise AdoError(
                CODE_INVALID_INPUT,
                "The parameter version is required to update a wiki page (the version of "
                "the page being replaced).",
            )
        headers["If-Match"] = str(version)
        response = adoc.put(
            _pages_path(adoc, wiki),
            params={"path": page_path},
            content=content,
            headers=headers,
        )
    page = response.json()
    return {
        "path": page.get("path") or page_path,
        "version": page.get("version"),
        "url": ((page.get("_links") or {}).get("page") or {}).get("href"),
    }


def _resolve_definition(adoc: Any, project: str, name: str) -> int:
    """The id of a build definition named *name* (exact match, then first)."""
    if name.isdigit():
        return int(name)
    listed = adoc.get(
        f"/{project}/_apis/build/definitions",
        params={"name": name},
    ).json()
    values = listed.get("value", [])
    if not values:
        from .errors import CODE_NOT_FOUND

        raise AdoError(CODE_NOT_FOUND, f"No build definition named {name!r}.")
    return int(values[0]["id"])


def _work_item_parameters() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "workItemId": {"type": "integer", "description": "Numeric id of the work item."},
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string", "description": "add, replace, remove or test."},
                        "path": {
                            "type": "string",
                            "description": "Field path, e.g. /fields/System.State.",
                        },
                        "value": {"description": "New value of the field."},
                    },
                    "required": ["op", "path"],
                },
                "description": "The JSON Patch operations to apply, in order.",
            },
        },
        "required": ["workItemId", "operations"],
    }


def _wiki_parameters(with_version: bool = False) -> dict[str, Any]:
    parameters = {
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "Name or id of any project; the owner project of the wiki is "
                "resolved from the wiki listing.",
            },
            "wiki": {"type": "string", "description": "Id or name of the wiki."},
            "path": {"type": "string", "description": "Path of the page, e.g. /Runbooks/Deploy."},
            "content": {"type": "string", "description": "Full content of the page."},
        },
        "required": ["wiki", "path", "content"],
    }
    if with_version:
        parameters["properties"]["version"] = {
            "type": "integer",
            "description": "Current version of the page (required to update).",
        }
        parameters["required"] = ["wiki", "path", "content", "version"]
    return parameters


def _queue_parameters() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "Name or id of the project. Defaults to default_project.",
            },
            "definitionId": {"type": "integer", "description": "Id of the build definition."},
            "definition": {
                "type": "string",
                "description": "Name (or id) of the build definition, resolved to the id.",
            },
            "branch": {"type": "string", "description": "Source branch (default main)."},
            "variables": {
                "type": "object",
                "description": "Optional build variables as an object of values.",
            },
        },
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_update_work_item",
        "Change fields of a work item through a JSON Patch list of operations. This CHANGES "
        "Azure DevOps.",
        _work_item_parameters(),
        handle_update_work_item,
    ),
    tool_spec(
        "azure_devops_create_wiki_page",
        "Create a wiki page with content at a path. This CHANGES Azure DevOps.",
        _wiki_parameters(),
        handle_create_wiki_page,
    ),
    tool_spec(
        "azure_devops_update_wiki_page",
        "Replace the content of an existing wiki page (pass the current version). This CHANGES "
        "Azure DevOps.",
        _wiki_parameters(with_version=True),
        handle_update_wiki_page,
    ),
    tool_spec(
        "azure_devops_queue_build",
        "Queue a build of a pipeline definition on a branch. This CHANGES Azure DevOps.",
        _queue_parameters(),
        handle_queue_build,
    ),
]
