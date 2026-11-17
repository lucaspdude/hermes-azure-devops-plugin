"""Resolve the plugin modules for the dashboard backend.

The gateway imports ``dashboard/plugin_api.py`` as a standalone file (outside
the plugin package, without the plugin root on ``sys.path``), so the backend
cannot use relative imports nor assume the agent already registered the plugin
package. Two paths, in order:

1. the agent loader namespace (``hermes_plugins.<slug>``), when the plugin is
   loaded in this process already;
2. a direct load of the plugin root (this file's parent directory), under a
   private package name - which is exactly the layout the loader produces, so
   relative imports inside the modules work unchanged.
"""

import importlib
import importlib.util
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent

#: The slugs the agent loader can have registered (manifest directory name with
#: ``-`` normalized to ``_``, per ``_directory_module_name``).
_LOADER_PACKAGES = (
    "hermes_plugins.hermes_azure_devops_plugin",
    "hermes_plugins.azure_devops",
)

#: The private package the shim loads itself, when the loader has not.
_OWN_PACKAGE = "hermes_plugin_azure_devops_backend"


def _loader_package() -> str | None:
    for candidate in _LOADER_PACKAGES:
        if candidate in sys.modules:
            return candidate
    for name in sys.modules:
        if name.startswith("hermes_plugins.") and "azure_devops" in name:
            return name
    return None


def _load_own() -> None:
    if _OWN_PACKAGE in sys.modules:
        return
    if str(PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(PLUGIN_ROOT))
    spec = importlib.util.spec_from_file_location(
        _OWN_PACKAGE,
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[_OWN_PACKAGE] = module
    spec.loader.exec_module(module)


def _package() -> str:
    loaded = _loader_package()
    if loaded:
        return loaded
    _load_own()
    return _OWN_PACKAGE


def __getattr__(name: str):
    package = _package()
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
