"""The operational help of the plugin, rendered from the skills.

The two embedded skills are the source of the content: this module reads them
and renders the same text for the slash command (``/ado-help``) and the CLI
subcommand (``hermes azure-devops help``), so the three surfaces cannot drift.
"""

from pathlib import Path

_SKILLS_DIR = Path(__file__).parent / "skills"

#: The order the sections appear in the guide.
_TOPICS = (
    "usage",
    "workflows",
)

_TOPIC_TITLES = {
    "usage": "Usage contract (PAT scopes, paging, error codes, pitfalls)",
    "workflows": "Workflows (recipes the agent follows)",
}

# Free-form topics the model or the user may ask for, mapped to a section.
_TOPIC_ALIASES = {
    "pat": "usage",
    "scopes": "usage",
    "paging": "usage",
    "pagination": "usage",
    "errors": "usage",
    "codes": "usage",
    "pull requests": "workflows",
    "pr": "workflows",
    "builds": "workflows",
    "work items": "workflows",
    "wiki": "workflows",
    "release": "workflows",
}


def _skill_body(topic: str) -> str:
    """The rendered body of one topic, read from the embedded skill."""
    directory = _SKILLS_DIR / f"azure-devops-{topic}"
    skill = directory / "SKILL.md"
    if not skill.is_file():
        return f"(the skill azure-devops-{topic} is missing from this installation)"
    text = skill.read_text(encoding="utf-8")
    # Strip the YAML front matter and the first heading: the guide adds its own.
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3 :]
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def help_topics() -> tuple[str, ...]:
    """The topics the guide covers, in render order."""
    return _TOPICS


def render_help(topic: str | None = None) -> str:
    """The guide, or one section of it highlighted (the rest still follows).

    An unknown topic is answered with the full guide and a note, never with an
    error: the command is a help surface, not an API.
    """
    parts = ["# Azure DevOps plugin — help", ""]
    asked = (topic or "").strip().lower()
    known = None
    if asked:
        for name, title in _TOPIC_TITLES.items():
            if asked in name or asked in title.lower():
                known = name
        if known is None:
            for alias, name in _TOPIC_ALIASES.items():
                if asked in alias:
                    known = name
                    break
    if asked and known is None:
        parts.append(f"(no section matches {topic!r}; showing the whole guide)")
        parts.append("")
    for name in _TOPICS:
        marker = " (requested)" if known == name else ""
        parts.append(f"## {_TOPIC_TITLES[name]}{marker}")
        parts.append("")
        parts.append(_skill_body(name))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
