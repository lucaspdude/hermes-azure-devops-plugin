"""Hermes plugin for Azure DevOps.

The package IS the plugin: the Hermes loader imports this file as
``hermes_plugins.<slug>`` and resolves the sibling modules of the repository
root relative to it (``from .registry import TOOLS``).

``register(ctx)`` only wires the tool registry into the context — no network,
no secret read, no file access. Everything that talks to Azure DevOps happens
inside a tool handler.
"""

from . import (
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
from .registry import TOOLS, ToolSpec, guarded_handler
from .toolkit import bind_context

__all__ = ["TOOLS", "ToolSpec", "guarded_handler", "register"]

#: The registry is the single source of truth: every module of tools adds its
#: tools here, and the manifest is generated from this very list.
TOOLS.extend(tools_projects.TOOLS)
TOOLS.extend(tools_builds.TOOLS)
TOOLS.extend(tools_pull_requests.TOOLS)
TOOLS.extend(tools_work_items.TOOLS)
TOOLS.extend(tools_wiki.TOOLS)
TOOLS.extend(tools_git.TOOLS)
TOOLS.extend(tools_artifacts.TOOLS)
TOOLS.extend(tools_identity.TOOLS)
TOOLS.extend(tools_policies.TOOLS)
TOOLS.extend(tools_releases.TOOLS)


def register(ctx) -> None:
    """Register every tool of the single registry.

    The handler of each tool is wrapped by ``guarded_handler``: the tool
    answers the JSON envelope and never lets an exception escape.
    """
    bind_context(ctx)
    for tool in TOOLS:
        ctx.register_tool(
            name=tool.name,
            toolset=tool.toolset,
            schema=tool.schema,
            handler=guarded_handler(tool.handler),
            check_fn=tool.check_fn,
            requires_env=list(tool.requires_env),
            description=tool.description,
        )
