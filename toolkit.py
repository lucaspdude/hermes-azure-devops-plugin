"""Plumbing shared by the tool modules.

A tool is thin: it reads the arguments, asks the client for a page and
normalizes what comes back. Everything the tools share lives here — the plugin
context (bound when the plugin registers), the client, and the reading of the
arguments.

The context is bound at registration time and read at call time: registering
does no I/O, and a tool always sees the settings of the active profile.
"""

from typing import Any, Mapping

from .auth import PAT_SECRET_NAME, check_pat_available, resolve_pat
from .client import AdoClient, decode_json
from .config import PluginConfig, load_config
from .errors import (
    CODE_INVALID_INPUT,
    CODE_NOT_CONFIGURED,
    CODE_NOT_FOUND,
    CODE_UPSTREAM_ERROR,
    AdoError,
)
from .registry import ToolSpec

#: Every tool of the plugin belongs to the same toolset.
TOOLSET = "azure-devops"

#: The plugin context, bound when the plugin registers (no I/O happens there).
_CONTEXT: Any = None


def bind_context(ctx: Any) -> None:
    """Keep the plugin context, so the handlers can read the settings."""
    global _CONTEXT
    _CONTEXT = ctx


def current_config() -> PluginConfig:
    """The settings of the plugin, read from the context of the active profile."""
    ctx = _CONTEXT
    if ctx is None:
        raise AdoError(
            CODE_NOT_CONFIGURED,
            "The Azure DevOps plugin is not registered: its settings are unavailable.",
        )
    return load_config(ctx)


def build_client(*, transport: Any = None, secret_resolver: Any = None) -> AdoClient:
    """A client for one call: the settings of the plugin and the PAT."""
    config = current_config()
    pat = resolve_pat(resolver=secret_resolver)
    return AdoClient(config, pat, transport=transport)


def client_for(kwargs: Mapping[str, Any]) -> AdoClient:
    """The client of a tool call.

    The suite injects the transport and the secret resolver; in the plugin the
    runtime transport and the secret scope of the active profile are used.
    """
    client = kwargs.get("client")
    if client is not None:
        return client
    return build_client(
        transport=kwargs.get("transport"),
        secret_resolver=kwargs.get("secret_resolver"),
    )


def check_credential() -> bool:
    """``check_fn`` of every tool: without the PAT the tool needs auth."""
    return check_pat_available()


def tool_spec(
    name: str,
    description: str,
    parameters: Mapping[str, Any],
    handler: Any,
) -> ToolSpec:
    """A tool of the plugin, with the shape every tool shares."""
    return ToolSpec(
        name=name,
        toolset=TOOLSET,
        schema={"name": name, "description": description, "parameters": dict(parameters)},
        handler=handler,
        check_fn=check_credential,
        description=description,
        requires_env=(PAT_SECRET_NAME,),
    )


def args_of(args: Any) -> Mapping[str, Any]:
    """The arguments of the call, as a mapping (never ``None``)."""
    return args if isinstance(args, Mapping) else {}


def text_arg(args: Mapping[str, Any], name: str, *, default: str = "") -> str:
    """A text argument, trimmed (the empty string when it is absent)."""
    value = args.get(name)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def int_arg(
    args: Mapping[str, Any],
    name: str,
    *,
    default: int | None = None,
    minimum: int = 1,
) -> int | None:
    """An integer argument, or ``invalid_input`` when it is not one."""
    value = args.get(name)
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise AdoError(
            CODE_INVALID_INPUT,
            f"The parameter {name!r} must be an integer.",
        ) from None
    if number < minimum:
        raise AdoError(
            CODE_INVALID_INPUT,
            f"The parameter {name!r} must be greater than or equal to {minimum}.",
        )
    return number


def project_arg(args: Mapping[str, Any], *, required: bool = True) -> str:
    """The project of the call: the one the model named, or the configured default."""
    name = text_arg(args, "project")
    if not name:
        name = current_config().default_project
    if not name and required:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the project (or configure the default_project setting): the call has no "
            "project to work on.",
        )
    return name


def repository_arg(args: Mapping[str, Any], adoc: AdoClient, project: str) -> str:
    """The repository of the call: the one the model named, or the only one of the project.

    The repository is optional in the tools that read a pull request: when the
    project has a single Git repository, the plugin asks the API which one it
    is instead of making the model repeat it. A project with more than one
    repository is an invalid input — the model has to say which one it means.
    """
    name = text_arg(args, "repository") or text_arg(args, "repositoryId")
    if name:
        return name
    response = adoc.get(f"/{project}/_apis/git/repositories")
    payload = decode_json(response)
    repositories = list_items(payload)
    if not repositories:
        raise AdoError(
            CODE_NOT_FOUND,
            f"The project {project!r} has no Git repository to read the pull requests from.",
        )
    if len(repositories) > 1:
        names = ", ".join(
            str(item.get("name") or item.get("id") or "") for item in repositories
        )
        raise AdoError(
            CODE_INVALID_INPUT,
            f"The project {project!r} has more than one repository: name the one the call is "
            f"about ({names}).",
        )
    identifier = repositories[0].get("id") or repositories[0].get("name")
    if not identifier:
        raise AdoError(
            CODE_UPSTREAM_ERROR,
            f"The only repository of the project {project!r} does not carry an id.",
        )
    return str(identifier)


def list_items(payload: Any) -> list[dict[str, Any]]:
    """The items of a list response: the ``value`` of the envelope, or a bare array."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, Mapping):
        value = payload.get("value")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []
