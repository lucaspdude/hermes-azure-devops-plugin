"""Test helpers: load the plugin package the way the Hermes loader does.

The plugin package IS the repository root, so the modules are imported as
``hermes_plugins.azure_devops.<module>`` — exactly how the Hermes loader
imports them, which is what makes their relative imports work.
"""

import importlib
import importlib.util
import json
import sys
import types
from pathlib import Path

import httpx

PLUGIN_DIR = Path(__file__).resolve().parents[1]
PACKAGE = "hermes_plugins.azure_devops"


def load_plugin_package():
    """Import the plugin package (the repository root as the package directory)."""
    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]
    parent = "hermes_plugins"
    if parent not in sys.modules:
        namespace = types.ModuleType(parent)
        namespace.__path__ = []  # type: ignore[attr-defined]
        namespace.__package__ = parent
        sys.modules[parent] = namespace
    spec = importlib.util.spec_from_file_location(
        PACKAGE, PLUGIN_DIR / "__init__.py", submodule_search_locations=[str(PLUGIN_DIR)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE] = module
    spec.loader.exec_module(module)
    return module


def plugin_module(name):
    """Import one module of the plugin package (``config``, ``auth``, ...)."""
    load_plugin_package()
    return importlib.import_module(f"{PACKAGE}.{name}")


class FakeContext:
    """Minimal stand-in for the Hermes PluginContext (settings and tools)."""

    def __init__(self, settings=None):
        self._settings = dict(settings or {})
        self.registered_tools = []
        self.registered_skills = []
        self.registered_commands = []

    def get_config(self, key, default=None):
        return self._settings.get(key, default)

    def register_tool(self, **kwargs):
        self.registered_tools.append(kwargs)
        return kwargs

    def register_skill(self, name, path):
        self.registered_skills.append((name, str(path)))
        return (name, str(path))

    def register_command(self, name, handler, description="", args_hint=""):
        self.registered_commands.append(
            {"name": name, "handler": handler, "description": description}
        )
        return {"name": name}

    def register_cli_command(self, name, help="", setup_fn=None, handler_fn=None, description=""):
        # The host signature has a required positional ``help``; the fake keeps it
        # required so a registration without it fails here, not only on the host.
        if not help:
            raise TypeError("register_cli_command() missing required argument: 'help'")
        self.registered_commands.append(
            {"name": name, "cli": True, "help": help, "handler": handler_fn}
        )
        return {"name": name}


def mock_transport(handler):
    """The offline transport of the suite: a fake ``httpx`` transport.

    ``handler`` is the callable ``httpx.MockTransport`` expects: it receives
    the request and returns the response, so the tests never touch the
    network.
    """
    return httpx.MockTransport(handler)


#: The PAT the suite uses: a value no Azure DevOps organization accepts.
FAKE_PAT = "fake-pat-for-tests-only"


def fake_secret_resolver(value: str = FAKE_PAT):
    """A stand-in for the Hermes secret scope.

    It answers the PAT name with the fake token and every other name with
    ``None``, exactly like a profile that only has that one secret.
    """
    pat_name = plugin_module("auth").PAT_SECRET_NAME

    def resolver(name: str):
        return value if name == pat_name else None

    return resolver


def fake_client(handler, **settings):
    """An ``AdoClient`` wired to the fake transport and to the fake PAT.

    ``handler`` is the callable of the fake transport; the settings default to
    a configured organization so the client can be built.
    """
    client = plugin_module("client")
    config = plugin_module("config")
    settings.setdefault("organization", "contoso")
    cfg = config.load_config(FakeContext(settings))
    return client.AdoClient(cfg, FAKE_PAT, transport=mock_transport(handler))


def bind_context(settings=None):
    """Bind a fake plugin context, so the tools read the settings of the test.

    The plugin binds the real context when it registers; the suite binds a
    fake one, with the same ``get_config`` surface.
    """
    toolkit = plugin_module("toolkit")
    ctx = FakeContext(settings)
    toolkit.bind_context(ctx)
    return ctx


def call_tool(name, args=None, **kwargs):
    """Call a tool of the registry and return the parsed envelope.

    The call goes through ``guarded_handler``, exactly like the Hermes
    dispatcher does, so the answer is the JSON string of the contract.
    """
    registry = plugin_module("registry")
    tool = next(tool for tool in registry.TOOLS if tool.name == name)
    raw = registry.guarded_handler(tool.handler)(args or {}, **kwargs)
    return json.loads(raw)


def manifest_provides_tools(path=None):
    """The ``provides_tools`` list of the manifest.

    Only the two shapes the generator emits are understood (``provides_tools:
    []`` and the block form), so the suite needs no YAML parser.
    """
    manifest = Path(path) if path else PLUGIN_DIR / "plugin.yaml"
    declared: list[str] = []
    in_block = False
    for line in manifest.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if in_block:
            if stripped.startswith("- "):
                declared.append(stripped[2:].strip().strip("'\""))
                continue
            if stripped:
                break
            continue
        if not stripped.startswith("provides_tools:"):
            continue
        value = stripped[len("provides_tools:") :].strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
        if value:
            raise AssertionError(f"unsupported provides_tools value: {value!r}")
        in_block = True
    return declared


def tool_divergence(declared, registered):
    """The tools the manifest and the registry disagree about.

    Returns ``(missing_from_manifest, not_registered)``, each one naming the
    tool so the failure of the consistency test says what to fix.
    """
    missing = [name for name in registered if name not in declared]
    extra = [name for name in declared if name not in registered]
    return missing, extra
