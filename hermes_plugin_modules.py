"""Resolve the plugin modules for the dashboard backend.

The gateway imports ``dashboard/plugin_api.py`` as a standalone file (outside
the plugin package), so the backend cannot use relative imports. The loader of
the agent registers the plugin modules under a package whose slug follows the
install directory; this shim finds whichever namespace is loaded and
re-exports the names the panel needs.
"""

import importlib
import sys

_CANDIDATE_PACKAGES = (
    "hermes_plugins.hermes-azure-devops-plugin",
    "hermes_plugins.hermes_azure_devops_plugin",
    "hermes_plugins.azure-devops",
    "hermes_plugins.azure_devops",
)


def _loaded_plugin_package() -> str | None:
    for candidate in _CANDIDATE_PACKAGES:
        if candidate in sys.modules:
            return candidate
    for name in sys.modules:
        if name.startswith("hermes_plugins.") and "azure" in name:
            return name
        if name.startswith("hermes_plugins_") and "azure" in name:
            return name
    return None


def __getattr__(name: str):
    package = _loaded_plugin_package()
    if package is None:
        raise ImportError(
            "The Azure DevOps plugin is not loaded: the panel backend only works when the "
            "plugin is in plugins.enabled (the panel then explains the same gate)."
        )
    module = importlib.import_module(f"{package}.toolkit")
    value = getattr(module, name, None)
    if value is None:
        errors = importlib.import_module(f"{package}.errors")
        value = getattr(errors, name, None)
    if value is None:
        client = importlib.import_module(f"{package}.client")
        value = getattr(client, name, None)
    if value is None:
        identity = importlib.import_module(f"{package}.tools_identity")
        value = getattr(identity, name, None)
    if value is None:
        raise AttributeError(name)
    return value
