"""Tools of the identities (read only).

Both tools read the same route — ``GET /{org}/_apis/connectionData`` — the one
the verification answered 200: the endpoint does **not** answer on the default
version of the API (``7.1`` answers 400), it answers on the preview version
``7.0-preview.1``. The version lives in the table of the client, so no tool
of the plugin hardcodes a version.

The route is the one the MCP uses to find the identity of the user the token
belongs to (the ``reviewerId`` of a vote): the authenticated user comes in
``authenticatedUser``. The identities of the organization come in
``identities`` (a map of descriptor to identity, or a list), and the two users
of the connection — the authenticated one and the authorized one — are always
part of the answer.

The display name is read from wherever the payload carries it: ``displayName``,
``customDisplayName``, the ``properties`` bag of the identity, and — as the
last resort — the ``providerDisplayName``.
"""

from typing import Any, Mapping

from .client import decode_json
from .errors import CODE_UPSTREAM_ERROR, AdoError
from .registry import ToolSpec
from .toolkit import args_of, client_for, tool_spec

#: The route of the connection data: organization level, no project.
CONNECTION_DATA_ROUTE = "/_apis/connectionData"


def handle_get_my_identity(args: dict, **kwargs) -> dict[str, Any]:
    """The identity of the user the PAT belongs to."""
    adoc = client_for(kwargs)
    payload = decode_json(adoc.get(CONNECTION_DATA_ROUTE))
    authenticated = _section(payload, "authenticatedUser")
    if not authenticated:
        raise AdoError(
            CODE_UPSTREAM_ERROR,
            "The connection data does not carry the authenticated user: the answer of "
            "Azure DevOps does not have the expected shape.",
        )
    return {"identity": _identity(authenticated)}


def handle_list_identities(args: dict, **kwargs) -> dict[str, Any]:
    """The identities of the organization."""
    adoc = client_for(kwargs)
    payload = decode_json(adoc.get(CONNECTION_DATA_ROUTE))
    identities: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in _identity_sources(payload):
        identity = _identity(source)
        key = str(identity.get("id") or identity.get("descriptor") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        identities.append(identity)
    return {"identities": identities, "count": len(identities)}


def _identity_sources(payload: Any) -> list[Mapping[str, Any]]:
    """Every identity of the payload: the two users of the connection and the map."""
    sources: list[Mapping[str, Any]] = []
    for field in ("authenticatedUser", "authorizedUser"):
        user = _section(payload, field)
        if user:
            sources.append(user)
    if not isinstance(payload, Mapping):
        return sources
    identities = payload.get("identities")
    if isinstance(identities, Mapping):
        sources.extend(item for item in identities.values() if isinstance(item, Mapping))
    elif isinstance(identities, list):
        sources.extend(item for item in identities if isinstance(item, Mapping))
    return sources


def _section(payload: Any, field: str) -> Mapping[str, Any]:
    """A section of the payload, when it is there and it is an object."""
    if not isinstance(payload, Mapping):
        return {}
    value = payload.get(field)
    return value if isinstance(value, Mapping) else {}


def _identity(item: Any) -> dict[str, Any]:
    """The fields of an identity the agent works with."""
    source = item if isinstance(item, Mapping) else {}
    return {
        "id": source.get("id"),
        "displayName": _display_name(source),
        "descriptor": source.get("descriptor"),
        "providerDisplayName": source.get("providerDisplayName"),
        "isActive": source.get("isActive"),
    }


def _display_name(source: Mapping[str, Any]) -> str:
    """The display name of the identity, wherever the payload carries it."""
    for field in ("displayName", "customDisplayName"):
        value = source.get(field)
        if value:
            return str(value).strip()
    properties = source.get("properties")
    if isinstance(properties, Mapping):
        for field in ("DisplayName", "displayName"):
            value = properties.get(field)
            if value:
                return str(value).strip()
    provider = source.get("providerDisplayName")
    return str(provider).strip() if provider else ""


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_get_my_identity",
        "Get the identity of the user the PAT belongs to, with its id and display name.",
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
        handle_get_my_identity,
    ),
    tool_spec(
        "azure_devops_list_identities",
        "List the identities of the organization, with id, display name and descriptor.",
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
        handle_list_identities,
    ),
]
