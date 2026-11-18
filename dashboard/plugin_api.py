"""The read-only backend of the Azure DevOps desktop panel.

The routes reuse the same client class, credential route and error taxonomy as
the agent tools (one PAT, one error shape), but they read the settings straight
from the active profile's config - the backend is loaded by the gateway as a
standalone file, and it must not touch the toolkit's shared context the agent
tools bind at registration.

The canonical state is the Azure DevOps API itself: the panel keeps a module
level cache for ~15s to absorb polling, invalidated by the tools' write event.

Mounted at ``/api/plugins/azure-devops/`` by the gateway when the plugin is in
``plugins.enabled``. Read-only by construction: only GET routes exist.
"""

import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request

_PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

from hermes_plugin_modules import AdoError, bind_context, decode_json  # noqa: E402

router = APIRouter()

#: The plugin id in ``plugins.entries.<id>.settings`` (the manifest name).
PLUGIN_ID = "azure-devops"

#: The module-level cache: one instance per process, invalidated by events.
_CACHE_LOCK = threading.Lock()
_CACHE: dict[tuple, tuple[float, Any]] = {}
CACHE_SECONDS = 15.0


def _cache_get(key: tuple) -> Any | None:
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit is None:
            return None
        at, value = hit
        if time.monotonic() - at > CACHE_SECONDS:
            return None
        return value


def _cache_put(key: tuple, value: Any) -> None:
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), value)


def cache_invalidate() -> None:
    """The write tools' event lands here: the next read refetches."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _plugin_settings() -> dict[str, Any]:
    """The settings of the plugin, from the active profile's config."""
    try:
        from hermes_cli.config import load_config

        config = load_config()
        entries = (config.get("plugins") or {}).get("entries") or {}
        return (entries.get(PLUGIN_ID) or {}).get("settings") or {}
    except Exception:
        return {}


class _ProfileSettingsContext:
    """A settings context that reads plugins.entries.<id>.settings from the
    profile config the gateway already loaded - never the toolkit's global."""

    def get_config(self, key: str, default: Any = None) -> Any:
        try:
            from hermes_cli.config import load_config

            config = load_config()
            entries = (config.get("plugins") or {}).get("entries") or {}
            settings = (entries.get(PLUGIN_ID) or {}).get("settings") or {}
        except Exception:
            settings = {}
        return settings.get(key, default)


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

def _panel_client() -> Any:
    """A client for one panel call: profile settings, secret scope, no global state.

    The backend binds its OWN settings context (a fresh one per call) instead of
    the toolkit's global: binding the global here would clobber the binding the
    agent tools registered, and every agent tool call would then read the panel's
    empty settings.
    """
    bind_context(_ProfileSettingsContext())
    from hermes_plugin_modules import build_client

    return build_client()


class _FakeContext:
    """The settings surface for the fallback client (never rebinds the toolkit)."""

    def __init__(self, settings: dict[str, Any]) -> None:
        self._settings = dict(settings)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)



def _overview_payload(client: Any) -> dict[str, Any]:
    """Pull requests of the user, work items assigned to them, recent builds.

    The identity comes from ``connectionData``; a PAT without the Identity
    scope degrades: the parts that do not need the identity are still listed.
    """
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
        # A API do Azure DevOps nao tem PR a nivel de organizacao: PR vive em
        # /{project}/_apis/git/pullrequests. O painel varre os projetos da
        # organizacao (a mesma rota que list_projects usa) e filtra os meus.
        org = client.config.organization
        projects_payload = decode_json(client.get("/_apis/projects", params={"$top": 200}))
        projects = [
            p
            for p in projects_payload.get("value", [])
            if not _project_ignored(p.get("id"), p.get("name"), client)
        ]
        project_ids = [p.get("id") for p in projects]
        project_by_id = {p.get("id"): p for p in projects}
        mine = []
        for pid in project_ids:
            response = client.get(
                f"/{pid}/_apis/git/pullrequests",
                params={"searchCriteria.status": "active", "$top": 10},
            )
            for item in decode_json(response).get("value", []):
                ids = {
                    str((item.get("createdBy") or {}).get("id") or ""),
                    *[
                        str((reviewer or {}).get("id") or "")
                        for reviewer in item.get("reviewers") or []
                    ],
                }
                if user_id in ids:
                    mine.append((pid, item))
        pull_requests = [
            {
                "id": item.get("pullRequestId"),
                "title": item.get("title"),
                "project": pid,
                "repository": (item.get("repository") or {}).get("name"),
                "isDraft": item.get("isDraft"),
                "createdAt": (item.get("creationDate") or ""),
                "url": (((item.get("_links") or {}).get("web") or {}).get("href")),
            }
            for pid, item in mine
        ][:20]

        wiql = (
            "SELECT [System.Id] FROM WorkItems WHERE [System.AssignedTo] = @me "
            "ORDER BY [System.ChangedDate] DESC"
        )
        ids: list[Any] = []
        for pid in project_ids:
            response = client.post(
                f"/{pid}/_apis/wit/wiql", json={"query": wiql}, params={"$top": 20}
            )
            ids.extend(item.get("id") for item in decode_json(response).get("workItems", []))
        ids = ids[:20]
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
                    "changed": (item.get("fields") or {}).get("System.ChangedDate"),
                    "url": (((item.get("_links") or {}).get("html") or {}).get("href")),
                }
                for item in decode_json(response).get("value", [])
            ]

        build_rows = []
        for pid in project_ids:
            response = client.get(f"/{pid}/_apis/build/builds", params={"$top": 10})
            for item in decode_json(response).get("value", []):
                if ((item.get("requestedFor") or {}).get("id") == user_id):
                    item = dict(item)
                    item["_project"] = pid
                    build_rows.append(item)
        builds = [
            {
                "id": item.get("id"),
                "buildNumber": item.get("buildNumber"),
                "status": item.get("status"),
                "result": item.get("result"),
                "definition": (item.get("definition") or {}).get("name"),
                "project": item.get("_project"),
                "finishedAt": (item.get("finishTime") or item.get("queueTime") or ""),
                "url": (((item.get("_links") or {}).get("web") or {}).get("href")),
            }
            for item in build_rows
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
    client = _panel_client()
    try:
        return _overview_payload(client)
    finally:
        close = getattr(client, "close", None)
        if close:
            close()


def _served(key: tuple, build: Callable[[], Any]) -> Any:
    """Cache-or-build, against the module-level store (polling absorbs here)."""
    hit = _cache_get(key)
    if hit is not None:
        return hit
    value = build()
    _cache_put(key, value)
    return value


def _releases_payload(client: Any) -> dict[str, Any]:
    """Releases recentes dos projetos da organização (mesma varredura do overview)."""
    from hermes_plugin_modules import decode_json

    org = client.config.organization
    projects_payload = decode_json(client.get("/_apis/projects", params={"$top": 200}))
    releases: list[dict[str, Any]] = []
    for pid in projects_payload.get("value", []):
        if _project_ignored(pid.get("id"), pid.get("name"), client):
            continue
        response = client.get(
            f"/{org}/{pid.get('id')}/_apis/release/releases", params={"$top": 10}
        )
        for item in decode_json(response).get("value", []):
            releases.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": item.get("status"),
                    "created": (item.get("createdOn") or ""),
                    "createdBy": ((item.get("createdBy") or {}).get("displayName") or ""),
                    "project": pid.get("name"),
                    "url": ((item.get("_links") or {}).get("web") or {}).get("href"),
                }
            )
    releases.sort(key=lambda item: item.get("created") or "", reverse=True)
    return {"releases": releases[:20]}


def _project_ignored(project_id: Any, project_name: Any, client: Any) -> bool:
    """Whether the project is in the profile's ignored_projects setting."""
    names = getattr(client.config, "ignored_project_names", frozenset())
    ids = getattr(client.config, "ignored_project_ids", frozenset())
    if project_name and str(project_name).lower() in names:
        return True
    if project_id and str(project_id) in ids:
        return True
    return False


@router.get("/releases")
def releases(request: Request) -> dict[str, Any]:
    """Releases recentes dos projetos da organização."""
    try:
        def build() -> dict[str, Any]:
            client = _panel_client()
            try:
                return _releases_payload(client)
            finally:
                close = getattr(client, "close", None)
                if close:
                    close()
        return _served(("releases",), build)
    except AdoError as exc:
        raise _panel_error(exc) from exc


@router.post("/settings/ignored-projects")
async def set_ignored_projects(request: Request) -> dict[str, Any]:
    """Grava a lista de projetos ignorados na setting do perfil."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    projects = body.get("ignored_projects")
    if not isinstance(projects, list) or not all(isinstance(item, str) for item in projects):
        return {"ok": False, "error": {"code": "invalid_input", "message": "ignored_projects must be a list of strings"}}
    try:
        from hermes_cli.config import load_config, save_config

        config = load_config()
        entries = config.setdefault("plugins", {}).setdefault("entries", {})
        settings = entries.setdefault(PLUGIN_ID, {}).setdefault("settings", {})
        settings["ignored_projects"] = projects
        save_config(config)
    except Exception as exc:
        return {"ok": False, "error": {"code": "upstream_error", "message": str(exc)[:200]}}
    return {"ok": True, "ignored_projects": projects}


@router.get("/overview")
def overview(request: Request) -> dict[str, Any]:
    """The activity of the authenticated user (the panel's only aggregate)."""
    try:
        return _served(("overview",), _build_overview)
    except AdoError as exc:
        raise _panel_error(exc) from exc


@router.get("/pull-requests/{pull_request_id}")
def pull_request_detail(pull_request_id: int, request: Request) -> dict[str, Any]:
    """One pull request, the same payload the agent tool answers."""
    try:
        def build() -> dict[str, Any]:
            client = _panel_client()
            try:
                response = client.get(f"/_apis/git/pullrequests/{pull_request_id}")
                return {"pullRequest": decode_json(response)}
            finally:
                close = getattr(client, "close", None)
                if close:
                    close()

        return _served(("pull-requests", pull_request_id), build)
    except AdoError as exc:
        raise _panel_error(exc) from exc


@router.get("/builds/{build_id}")
def build_detail(build_id: int, request: Request) -> dict[str, Any]:
    """One build, the same payload the agent tool answers."""
    try:
        def build() -> dict[str, Any]:
            client = _panel_client()
            try:
                response = client.get(f"/_apis/build/builds/{build_id}")
                return {"build": decode_json(response)}
            finally:
                close = getattr(client, "close", None)
                if close:
                    close()

        return _served(("builds", build_id), build)
    except AdoError as exc:
        raise _panel_error(exc) from exc
