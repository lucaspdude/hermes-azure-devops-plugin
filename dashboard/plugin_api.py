"""The read-only backend of the Azure DevOps desktop panel.

The routes reuse the same client and credential the agent tools use (one PAT,
one settings source, one error taxonomy). The canonical state is the Azure
DevOps API itself: the panel caches for ~15s to absorb polling, and the tools'
write events only invalidate this cache.

Mounted at ``/api/plugins/azure-devops/`` by the gateway when the plugin is in
``plugins.enabled``. Read-only by construction: only GET routes exist, and a
mutating verb answers 405 before anything else runs.
"""

from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request

# The backend is loaded by the gateway as a standalone file (import_user_code),
# outside the plugin package: resolve the plugin modules through whichever
# namespace the loader registered (the slug differs between install modes).
from hermes_plugin_modules import AdoError, bind_context  # noqa: F401

router = APIRouter()


class _PanelContext:
    """The settings surface the gateway hands to a plugin backend."""

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self._settings = dict(settings or {})

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)


def _bind(request: Request) -> None:
    settings = getattr(getattr(request, "state", None), "plugin_settings", None)
    bind_context(_PanelContext(settings))


def _panel_error(exc: Exception) -> HTTPException:
    """One error shape for every failure: the plugin taxonomy, status kept."""
    if isinstance(exc, AdoError):
        detail: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.status is not None:
            detail["status"] = exc.status
        return HTTPException(status_code=exc.status or 502, detail=detail)
    return HTTPException(
        status_code=500,
        detail={"code": "upstream_error", "message": "The panel failed unexpectedly."},
    )


def _cache(seconds: int = 15):
    """A per-call in-memory cache, so polling does not hammer the API."""
    store: dict[tuple, tuple[float, Any]] = {}

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        import time

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            hit = store.get(key)
            if hit is not None and now - hit[0] < seconds:
                return hit[1]
            value = fn(*args, **kwargs)
            store[key] = (now, value)
            return value

        return wrapped

    return decorator


def _overview_payload(client: Any) -> dict[str, Any]:
    """Pull requests of the user, work items assigned to them, recent builds.

    The identity comes from ``connectionData``; a PAT without the Identity
    scope degrades: the parts that do not need the identity are still listed.
    """
    from hermes_plugin_modules import decode_json
    from hermes_plugin_modules import authenticated_user_id

    identity_warning = None
    try:
        user_id = authenticated_user_id(client)
    except AdoError as exc:
        identity_warning = exc.message
        user_id = None

    pull_requests: list[dict[str, Any]] = []
    work_items: list[dict[str, Any]] = []
    builds: list[dict[str, Any]] = []

    if user_id:
        org = client.config.organization
        response = client.get(
            f"/{org}/_apis/git/pullrequests",
            params={"searchCriteria.status": "active", "$top": 20},
        )
        payload = decode_json(response)
        mine = [
            item
            for item in payload.get("value", [])
            if user_id
            in {
                str((item.get("createdBy") or {}).get("id") or ""),
                *[
                    str((reviewer or {}).get("id") or "")
                    for reviewer in item.get("reviewers") or []
                ],
            }
        ]
        pull_requests = [
            {
                "id": item.get("pullRequestId"),
                "title": item.get("title"),
                "repository": (item.get("repository") or {}).get("name"),
                "isDraft": item.get("isDraft"),
            }
            for item in mine
        ]

        wiql = (
            "SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = @me "
            "ORDER BY [System.ChangedDate] DESC"
        )
        response = client.post("/_apis/wit/wiql", json={"query": wiql}, params={"$top": 20})
        ids = [item.get("id") for item in (decode_json(response).get("workItems") or [])][:20]
        if ids:
            response = client.get(
                "/_apis/wit/workitems", params={"ids": ",".join(str(i) for i in ids)}
            )
            work_items = [
                {
                    "id": item.get("id"),
                    "type": (item.get("fields") or {}).get("System.WorkItemType"),
                    "title": (item.get("fields") or {}).get("System.Title"),
                    "state": (item.get("fields") or {}).get("System.State"),
                }
                for item in decode_json(response).get("value", [])
            ]

        response = client.get(f"/{org}/_apis/build/builds", params={"$top": 50})
        builds = [
            {
                "id": item.get("id"),
                "buildNumber": item.get("buildNumber"),
                "status": item.get("status"),
                "result": item.get("result"),
                "definition": (item.get("definition") or {}).get("name"),
            }
            for item in decode_json(response).get("value", [])
            if ((item.get("requestedFor") or {}).get("id") == user_id)
        ][:10]

    payload: dict[str, Any] = {
        "pullRequests": pull_requests,
        "workItems": work_items,
        "builds": builds,
    }
    if identity_warning:
        payload["identityWarning"] = identity_warning
    return payload


def _build_overview() -> dict[str, Any]:
    from hermes_plugin_modules import build_client

    client = build_client()
    try:
        return _overview_payload(client)
    finally:
        close = getattr(client, "close", None)
        if close:
            close()


@router.get("/overview")
def overview(request: Request) -> dict[str, Any]:
    """The activity of the authenticated user (the panel's only aggregate)."""
    _bind(request)
    try:
        return _cache(seconds=15)(_build_overview)()
    except AdoError as exc:
        raise _panel_error(exc) from exc


@router.get("/pull-requests/{pull_request_id}")
def pull_request_detail(pull_request_id: int, request: Request) -> dict[str, Any]:
    """One pull request, the same payload the agent tool answers."""
    _bind(request)
    try:
        from hermes_plugin_modules import decode_json
        from hermes_plugin_modules import build_client

        client = build_client()
        try:
            response = client.get(f"/_apis/git/pullrequests/{pull_request_id}")
            return {"pullRequest": decode_json(response)}
        finally:
            close = getattr(client, "close", None)
            if close:
                close()
    except AdoError as exc:
        raise _panel_error(exc) from exc


@router.get("/builds/{build_id}")
def build_detail(build_id: int, request: Request) -> dict[str, Any]:
    """One build, the same payload the agent tool answers."""
    _bind(request)
    try:
        from hermes_plugin_modules import decode_json
        from hermes_plugin_modules import build_client

        client = build_client()
        try:
            response = client.get(f"/_apis/build/builds/{build_id}")
            return {"build": decode_json(response)}
        finally:
            close = getattr(client, "close", None)
            if close:
                close()
    except AdoError as exc:
        raise _panel_error(exc) from exc
