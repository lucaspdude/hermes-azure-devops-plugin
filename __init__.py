"""Hermes plugin for Azure DevOps.

The package IS the plugin: the Hermes loader imports this file as
``hermes_plugins.<slug>`` and resolves the sibling modules of the repository
root relative to it (``from .registry import TOOLS``).

``register(ctx)`` only wires the tool registry into the context — no network,
no secret read, no file access. Everything that talks to Azure DevOps happens
inside a tool handler.
"""

from .registry import TOOLS, ToolSpec, guarded_handler

__all__ = ["TOOLS", "ToolSpec", "guarded_handler", "register"]


def register(ctx) -> None:
    """Register every tool of the single registry.

    The handler of each tool is wrapped by ``guarded_handler``: the tool
    answers the JSON envelope and never lets an exception escape.
    """
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
