"""Tool of the artifacts of a build (read only).

The route is the one the verification answered 200:
``GET /{org}/{project}/_apis/build/builds/{buildId}/artifacts``. The answer is
a **bare array** (no ``value`` envelope), and every artifact carries its name,
its size and the url it is downloaded from (``resource.downloadUrl``).

The artifact a model wants to download is the one whose ``url`` is the
download url; the link to the artifact inside the API travels in
``artifactUrl``, so nothing is lost.
"""

from typing import Any

from .client import decode_json
from .errors import CODE_INVALID_INPUT, AdoError
from .registry import ToolSpec
from .toolkit import args_of, client_for, list_items, project_arg, text_arg, tool_spec


def handle_list_build_artifacts(args: dict, **kwargs) -> dict[str, Any]:
    """The artifacts a build published."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    build_id = _build_id_arg(arguments)
    response = adoc.get(f"/{project}/_apis/build/builds/{build_id}/artifacts")
    payload = decode_json(response)
    artifacts = [_artifact(item) for item in list_items(payload)]
    return {"artifacts": artifacts, "count": len(artifacts)}


def _build_id_arg(arguments: Any) -> str:
    """The id of the build the call is about."""
    build_id = text_arg(arguments, "buildId")
    if not build_id:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the build (buildId) the call is about.",
        )
    return build_id


def _artifact(item: Any) -> dict[str, Any]:
    """The fields of an artifact the agent works with."""
    source = item if isinstance(item, dict) else {}
    resource = source.get("resource")
    resource = resource if isinstance(resource, dict) else {}
    download_url = resource.get("downloadUrl") or source.get("downloadUrl")
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "size": source.get("size"),
        "url": download_url or source.get("url"),
        "artifactUrl": source.get("url"),
        "resourceType": resource.get("type"),
        "expiresOn": source.get("expiresOn"),
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_build_artifacts",
        "List the artifacts a build published, with the name, the size and the download url.",
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
        handle_list_build_artifacts,
    ),
]
