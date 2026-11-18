"""Plugin settings, read from the Hermes profile config.

The manifest declares the settings and their defaults; this module is the one
place that reads them, so a tool never guesses a value the user configured.
"""

from dataclasses import dataclass
from typing import Any

from .errors import CODE_NOT_CONFIGURED, AdoError

DEFAULT_BASE_URL = "https://dev.azure.com"
DEFAULT_API_VERSION = "7.1"
DEFAULT_PROJECT = ""
DEFAULT_HTTP_TIMEOUT_MS = 30000
DEFAULT_DAYS = 7
MIN_DAYS = 1
MAX_DAYS = 90


@dataclass(frozen=True)
class PluginConfig:
    """The plugin's effective settings (manifest defaults applied)."""

    organization: str = ""
    base_url: str = DEFAULT_BASE_URL
    api_version: str = DEFAULT_API_VERSION
    default_project: str = DEFAULT_PROJECT
    http_timeout_ms: int = DEFAULT_HTTP_TIMEOUT_MS
    ignored_projects: tuple[str, ...] = ()
    default_days: int = DEFAULT_DAYS

    @property
    def ignored_project_names(self) -> frozenset[str]:
        """Ignored project names, lowercase for case-insensitive matching."""
        return frozenset(name.lower() for name in self.ignored_projects)

    @property
    def ignored_project_ids(self) -> frozenset[str]:
        """Ignored project ids, exact match."""
        return frozenset(self.ignored_projects)

    @property
    def missing_settings(self) -> list[str]:
        """Settings the user still has to provide (``organization`` is mandatory)."""
        return [] if self.organization else ["organization"]

    @property
    def is_configured(self) -> bool:
        """True when every mandatory setting is present."""
        return not self.missing_settings

    def require(self) -> "PluginConfig":
        """Return self, or raise ``not_configured`` naming what is missing."""
        missing = self.missing_settings
        if missing:
            raise AdoError(
                CODE_NOT_CONFIGURED,
                "Azure DevOps is not configured: set "
                + ", ".join(f"plugins.entries.azure-devops.settings.{name}" for name in missing)
                + " in the Hermes profile config.",
            )
        return self


def load_config(ctx) -> PluginConfig:
    """Read the plugin settings through the context, applying the manifest defaults."""
    return PluginConfig(
        organization=_as_text(ctx.get_config("organization", ""), ""),
        base_url=_as_text(ctx.get_config("base_url", DEFAULT_BASE_URL), DEFAULT_BASE_URL).rstrip("/"),
        api_version=_as_text(ctx.get_config("api_version", DEFAULT_API_VERSION), DEFAULT_API_VERSION),
        default_project=_as_text(ctx.get_config("default_project", DEFAULT_PROJECT), DEFAULT_PROJECT),
        http_timeout_ms=_as_int(
            ctx.get_config("http_timeout_ms", DEFAULT_HTTP_TIMEOUT_MS), DEFAULT_HTTP_TIMEOUT_MS
        ),
        ignored_projects=_as_project_list(ctx.get_config("ignored_projects", [])),
        default_days=_clamp_days(_as_int(ctx.get_config("default_days", DEFAULT_DAYS), DEFAULT_DAYS)),
    )


def _as_project_list(value: Any) -> tuple[str, ...]:
    """The ignored-projects setting: a list of names or ids, trimmed, deduped."""
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple)):
        parts = [str(part).strip() for part in value]
    else:
        parts = []
    seen: set[str] = set()
    projects: list[str] = []
    for part in parts:
        if part and part.lower() not in seen:
            seen.add(part.lower())
            projects.append(part)
    return tuple(projects)


def _clamp_days(value: int) -> int:
    """Keep the lookback window inside the supported 1..90 range."""
    return max(MIN_DAYS, min(MAX_DAYS, value))


def _as_text(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
