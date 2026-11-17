"""Single source of truth for the plugin's tools.

``TOOLS`` is the only list of tools in the package: this module aggregates the
tools of every domain module into it, ``register(ctx)`` registers exactly what
is declared here, and the manifest's ``provides_tools`` block is generated from
the same list, so the two cannot drift apart.

The module also owns the response contract of every tool: a handler returns
the payload and may raise, and ``guarded_handler`` wraps it into the JSON
envelope (``{"ok": true, "data": ...}`` or ``{"ok": false, "error": {...}}``),
so no exception ever escapes a tool.
"""

import functools
import json
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .errors import CODE_UPSTREAM_ERROR, AdoError


@dataclass(frozen=True)
class ToolSpec:
    """One tool of the plugin."""

    name: str
    toolset: str
    schema: dict[str, Any]
    handler: Callable[..., Any]
    check_fn: Callable[[], bool] | None = None
    description: str = ""
    requires_env: tuple[str, ...] = ()


TOOLS: list[ToolSpec] = []


def tool_names(tools: Sequence[ToolSpec] | None = None) -> list[str]:
    """The names of the tools, in registry order."""
    return [tool.name for tool in (TOOLS if tools is None else tools)]


def provides_tools_block(tools: Sequence[ToolSpec] | None = None) -> str:
    """The ``provides_tools`` block of the manifest, generated from the registry.

    The block depends on nothing but the registry, so the same registry always
    produces the same manifest block.
    """
    names = tool_names(tools)
    if not names:
        return "provides_tools: []\n"
    return "provides_tools:\n" + "".join(f"  - {name}\n" for name in names)


def success_response(data: Any) -> str:
    """The happy path of a tool: ``{"ok": true, "data": ...}`` as a JSON string."""
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def error_response(error: AdoError) -> str:
    """The failure path of a tool: ``{"ok": false, "error": {...}}`` as a JSON string."""
    payload: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.status is not None:
        payload["status"] = error.status
    if error.type_key:
        payload["typeKey"] = error.type_key
    return json.dumps({"ok": False, "error": payload}, ensure_ascii=False)


def failure_response(exc: Exception) -> str:
    """The error envelope of any exception.

    The text of an unexpected exception is not repeated: it may carry a
    credential, and the taxonomy already says what happened.
    """
    if isinstance(exc, AdoError):
        return error_response(exc)
    return error_response(
        AdoError(
            CODE_UPSTREAM_ERROR,
            f"The Azure DevOps plugin failed unexpectedly ({type(exc).__name__}).",
        )
    )


def guarded_handler(handler: Callable[..., Any]) -> Callable[..., str]:
    """Wrap a tool handler so it always answers with the JSON envelope.

    The handler returns the payload and may raise; the wrapper builds the
    envelope and turns every exception into the error envelope, so a tool
    never lets an exception escape.
    """

    @functools.wraps(handler)
    def guarded(*args: Any, **kwargs: Any) -> str:
        try:
            return success_response(handler(*args, **kwargs))
        except AdoError as exc:
            return error_response(exc)
        except Exception as exc:  # noqa: BLE001 - the envelope is the contract
            return failure_response(exc)

    return guarded


#: The modules of tools, aggregated into ``TOOLS`` below. The import is at the
#: end of the module on purpose: the modules import ``ToolSpec`` from here, so
#: the definition has to exist before the import happens.
from . import (  # noqa: E402
    tools_artifacts,
    tools_builds,
    tools_git,
    tools_identity,
    tools_policies,
    tools_projects,
    tools_pull_requests,
    tools_releases,
    tools_wiki,
    tools_work_items,
)

#: The registry is the single source of truth: every module of tools adds its
#: tools here, and the manifest is generated from this very list.
for _tool_module in (
    tools_projects,
    tools_builds,
    tools_pull_requests,
    tools_work_items,
    tools_wiki,
    tools_git,
    tools_artifacts,
    tools_identity,
    tools_policies,
    tools_releases,
):
    TOOLS.extend(_tool_module.TOOLS)
