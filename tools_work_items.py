"""Tools of work items and WIQL (read only).

The routes are the ones verified against the real API: the WIQL query
(``POST /{project}/_apis/wit/wiql``), the work item by id
(``GET /_apis/wit/workitems/{id}``) and the work items by ids
(``GET /_apis/wit/workitems?ids=...``).

Three contracts of the verification live here:

* the WIQL route only answers a **POST with a JSON body** — without a body it
  answers 411 and a GET answers 405;
* the page size of the WIQL route travels as ``$top`` in the query string,
  never inside the body;
* the default of the fields of a work item is **reduced** (id, type, title and
  state): the fields vary by type, so the model asks for the others with the
  ``fields`` argument.
"""

from typing import Any, Mapping

from .client import decode_json
from .contracts import page_params, wiql_body
from .errors import CODE_INVALID_INPUT, AdoError
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

#: The fields a work item carries by default: the reduced set of the spec.
DEFAULT_WORK_ITEM_FIELDS = (
    "System.Id",
    "System.WorkItemType",
    "System.Title",
    "System.State",
)


def handle_query_wiql(args: dict, **kwargs) -> dict[str, Any]:
    """The work items a WIQL query finds."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    query = text_arg(arguments, "query")
    if not query:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Write the WIQL query the call is about (query).",
        )
    project = project_arg(arguments, required=False)
    response = adoc.post(
        _wiql_path(project),
        params=page_params(int_arg(arguments, "top")),
        json=wiql_body(query),
    )
    payload = decode_json(response)
    work_items = [_wiql_item(item) for item in _work_items_of(payload)]
    return {
        "workItems": work_items,
        "ids": [item["id"] for item in work_items if item.get("id") is not None],
        "columns": _columns_of(payload),
        "count": len(work_items),
    }


def handle_get_work_item(args: dict, **kwargs) -> dict[str, Any]:
    """One work item, by id."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    work_item_id = _work_item_id_arg(arguments)
    response = adoc.get(
        f"/_apis/wit/workitems/{work_item_id}",
        params={"fields": ",".join(_fields_arg(arguments))},
    )
    payload = decode_json(response)
    return {"workItem": _work_item(payload)}


def handle_list_work_items(args: dict, **kwargs) -> dict[str, Any]:
    """The work items of a type, or the work items of a list of ids."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments, required=False)
    fields = _fields_arg(arguments)
    work_item_type = text_arg(arguments, "type")
    ids = _ids_arg(arguments)
    top = int_arg(arguments, "top")
    if not ids and not work_item_type:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the work items to list: their ids, or the type to list.",
        )
    if not ids:
        ids = _ids_of_type(adoc, project, work_item_type, top)
    if not ids:
        return {"workItems": [], "count": 0}
    items = _fetch_work_items(adoc, ids, fields)
    if work_item_type:
        items = [
            item
            for item in items
            if str(item.get("type") or "").lower() == work_item_type.lower()
        ]
    if top is not None:
        items = items[:top]
    return {"workItems": items, "count": len(items)}


def _wiql_path(project: str) -> str:
    """The path of the WIQL route: of the project, or of the organization."""
    if project:
        return f"/{project}/_apis/wit/wiql"
    return "/_apis/wit/wiql"


def _ids_of_type(adoc: Any, project: str, work_item_type: str, top: int | None) -> list[int]:
    """The ids of the work items of a type, asked with a WIQL query.

    The route of the work items does not filter by type: the ids of the type
    are found by a WIQL query, and the work items are read by those ids.
    """
    query = _type_query(work_item_type, project)
    response = adoc.post(
        _wiql_path(project),
        params=page_params(top),
        json=wiql_body(query),
    )
    payload = decode_json(response)
    ids: list[int] = []
    for item in _work_items_of(payload):
        identifier = item.get("id")
        if identifier is None:
            continue
        try:
            ids.append(int(identifier))
        except (TypeError, ValueError):
            continue
    return ids


def _type_query(work_item_type: str, project: str) -> str:
    """The WIQL query that finds the work items of a type."""
    conditions = []
    if project:
        conditions.append("[System.TeamProject] = @project")
    conditions.append(f"[System.WorkItemType] = '{_escape(work_item_type)}'")
    return "SELECT [System.Id] FROM WorkItems WHERE " + " AND ".join(conditions)


def _escape(text: str) -> str:
    """A text that can live inside a WIQL string literal."""
    return str(text or "").replace("'", "''")


def _fetch_work_items(adoc: Any, ids: list[int], fields: list[str]) -> list[dict[str, Any]]:
    """The work items of a list of ids, read in one call."""
    params: dict[str, str] = {"ids": ",".join(str(identifier) for identifier in ids)}
    if fields:
        params["fields"] = ",".join(fields)
    response = adoc.get("/_apis/wit/workitems", params=params)
    payload = decode_json(response)
    return [_work_item(item) for item in list_items(payload)]


def _work_items_of(payload: Any) -> list[Any]:
    """The work items of a WIQL answer: the ``workItems`` of the payload."""
    if isinstance(payload, Mapping):
        items = payload.get("workItems")
        if isinstance(items, list):
            return items
    return []


def _columns_of(payload: Any) -> list[dict[str, Any]]:
    """The columns of a WIQL answer."""
    if not isinstance(payload, Mapping):
        return []
    columns = payload.get("columns")
    if not isinstance(columns, list):
        return []
    return [
        {
            "name": column.get("name"),
            "referenceName": column.get("referenceName"),
        }
        for column in columns
        if isinstance(column, dict)
    ]


def _wiql_item(item: Any) -> dict[str, Any]:
    """The fields of a work item a WIQL answer carries."""
    source = item if isinstance(item, dict) else {}
    return {"id": source.get("id"), "url": source.get("url")}


def _work_item(item: Any) -> dict[str, Any]:
    """The fields of a work item the agent works with."""
    source = item if isinstance(item, dict) else {}
    raw_fields = source.get("fields")
    values = raw_fields if isinstance(raw_fields, dict) else {}
    identifier = source.get("id")
    if identifier is None:
        identifier = values.get("System.Id")
    return {
        "id": identifier,
        "rev": source.get("rev"),
        "type": values.get("System.WorkItemType"),
        "title": values.get("System.Title"),
        "state": values.get("System.State"),
        "url": source.get("url"),
        "fields": values,
    }


def _work_item_id_arg(arguments: Any) -> str:
    """The id of the work item the call is about."""
    work_item_id = text_arg(arguments, "workItemId") or text_arg(arguments, "id")
    if not work_item_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the work item (workItemId) the call is about.",
        )
    return work_item_id


def _ids_arg(arguments: Any) -> list[int]:
    """The ids of the work items the model named."""
    raw = arguments.get("ids")
    if raw is None or raw == "":
        return []
    values = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    ids: list[int] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        try:
            ids.append(int(text))
        except ValueError:
            raise AdoError(
                CODE_INVALID_INPUT,
                f"The work item id {text!r} is not a number.",
            ) from None
    return ids


def _fields_arg(arguments: Any) -> list[str]:
    """The fields the model asked for, or the reduced set of the default."""
    raw = arguments.get("fields")
    if raw is None or raw == "":
        return list(DEFAULT_WORK_ITEM_FIELDS)
    values = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    fields = [str(value).strip() for value in values if str(value).strip()]
    return fields or list(DEFAULT_WORK_ITEM_FIELDS)


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_query_wiql",
        "Run a WIQL query and get the ids of the work items it finds. Use it to search work "
        "items by type, state, area or iteration.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The WIQL query, for example: SELECT [System.Id] FROM WorkItems.",
                },
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project the query runs in. Optional: without it the "
                        "query runs in the whole organization."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of work items to return in this page.",
                },
            },
            "required": ["query"],
        },
        handle_query_wiql,
    ),
    tool_spec(
        "azure_devops_get_work_item",
        "Get one work item by id, with its type, title and state (and the other fields asked "
        "for).",
        {
            "type": "object",
            "properties": {
                "workItemId": {
                    "type": "integer",
                    "description": "Id of the work item.",
                },
                "fields": {
                    "type": "string",
                    "description": (
                        "Fields to read, separated by commas (System.Title,System.State,...). "
                        "Defaults to System.Id, System.WorkItemType, System.Title, System.State."
                    ),
                },
            },
            "required": ["workItemId"],
        },
        handle_get_work_item,
    ),
    tool_spec(
        "azure_devops_list_work_items",
        "List work items by type or by ids. Use it to read the details of the work items a "
        "WIQL query found.",
        {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Ids of the work items to read.",
                },
                "type": {
                    "type": "string",
                    "description": (
                        "Type of the work items to list (Bug, Task, ...). The ids of the type "
                        "are found with a WIQL query."
                    ),
                },
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project the work items belong to. Defaults to the "
                        "configured default_project."
                    ),
                },
                "fields": {
                    "type": "string",
                    "description": (
                        "Fields to read, separated by commas (System.Title,System.State,...). "
                        "Defaults to System.Id, System.WorkItemType, System.Title, System.State."
                    ),
                },
                "top": {
                    "type": "integer",
                    "description": "Maximum number of work items to return.",
                },
            },
            "required": [],
        },
        handle_list_work_items,
    ),
]
