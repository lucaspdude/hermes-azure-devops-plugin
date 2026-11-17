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


@dataclass(frozen=True)
class PluginConfig:
    """The plugin's effective settings (manifest defaults applied)."""

    organization: str = ""
    base_url: str = DEFAULT_BASE_URL
    api_version: str = DEFAULT_API_VERSION
    default_project: str = DEFAULT_PROJECT
    http_timeout_ms: int = DEFAULT_HTTP_TIMEOUT_MS

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
    )


def _as_text(value: Any, default: str) -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
