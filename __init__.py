"""Hermes plugin for Azure DevOps.

The package IS the plugin: the Hermes loader imports this file as
``hermes_plugins.<slug>`` and resolves the sibling modules of the repository
root relative to it (``from .registry import TOOLS``).

``register(ctx)`` only wires the tool registry into the context — no network,
no secret read, no file access. Everything that talks to Azure DevOps happens
inside a tool handler.
"""

from .registry import TOOLS, ToolSpec, guarded_handler
from .toolkit import bind_context

__all__ = ["TOOLS", "ToolSpec", "guarded_handler", "register"]


def register(ctx) -> None:
    """Register every tool of the single registry.

    The handler of each tool is wrapped by ``guarded_handler``: the tool
    answers the JSON envelope and never lets an exception escape.
    """
    bind_context(ctx)
    # Skills: the source of the content the help renders.
    _register_skills(ctx)
    # The help surfaces: the same text, inside the conversation and in a terminal.
    _register_help(ctx)
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

def _register_skills(ctx) -> None:
    """Register every SKILL.md under skills/ (read-only, plugin namespaced)."""
    from pathlib import Path

    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.is_file():
            ctx.register_skill(child.name, skill_md)


def _register_help(ctx) -> None:
    """The /ado-help slash command and the hermes azure-devops help subcommand."""
    from .help import render_help

    def _slash(raw_args: str, **kwargs):
        return render_help(raw_args)

    ctx.register_command(
        "ado-help",
        _slash,
        description="Azure DevOps plugin help: PAT scopes, paging, error codes, recipes.",
        args_hint="[topic]",
    )

    def _cli_setup(parser):
        sub = parser.add_parser("help", help="Azure DevOps plugin help")
        sub.add_argument("topic", nargs="?", default="", help="Highlight one section")
        sub.set_defaults(_topic="")

    def _cli_handler(args):
        return render_help(getattr(args, "topic", ""))

    try:
        ctx.register_cli_command(
            "azure-devops",
            setup_fn=_cli_setup,
            handler_fn=_cli_handler,
            description="Azure DevOps plugin help",
        )
    except Exception:
        # The CLI subcommand registration needs a parser the host provides; when it
        # is unavailable the slash command still answers the same content.
        pass
