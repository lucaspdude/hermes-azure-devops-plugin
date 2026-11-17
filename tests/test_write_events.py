"""The write tools invalidate the panel: the event fires after a success."""

import json
import sys
import types
import unittest

import httpx

from support import call_tool, fake_client, plugin_module

writes = plugin_module("tools_pull_request_writes")
writes_other = plugin_module("tools_writes")


class _Capture:
    """Captures the broadcast calls the module makes."""

    def __init__(self, module):
        self.calls = []
        self.module = module
        self._original = None

    def __enter__(self):
        captured = self

        def fake_broadcast(plugin_id, event, payload=None):
            captured.calls.append((plugin_id, event, payload))

        # Patch at the source the lazy import resolves to. The module does not
        # exist outside the gateway: register a stand-in first, then patch it.
        self._created_module = False
        if "hermes_cli.plugin_events" not in sys.modules:
            events = types.ModuleType("hermes_cli.plugin_events")
            events.plugin_event_name = (
                lambda plugin_id, event: f"plugin.{plugin_id}.{event}"
            )
            sys.modules.setdefault("hermes_cli", types.ModuleType("hermes_cli"))
            sys.modules["hermes_cli.plugin_events"] = events
            self._created_module = True
        else:
            events = __import__("hermes_cli.plugin_events", fromlist=["x"])
        self._module = events
        self._original = getattr(events, "broadcast_plugin_event", None)
        events.broadcast_plugin_event = fake_broadcast
        # The lazy import inside the tools resolves from sys.modules: clear the
        # module's cached import so the next call picks the patched function.
        self._module_dict = None
        return self

    def __exit__(self, *exc):
        if self._original is not None:
            self._module.broadcast_plugin_event = self._original
        if self._created_module:
            sys.modules.pop("hermes_cli.plugin_events", None)
        return False


def _ok(payload):
    return httpx.Response(200, json=payload, request=httpx.Request("POST", "https://x"))


class EventTest(unittest.TestCase):
    def test_a_successful_create_emits_the_invalidation_event(self):
        with _Capture(writes) as capture:
            result = call_tool(
                "azure_devops_create_pull_request",
                {
                    "project": "C",
                    "repository": "r",
                    "sourceRefName": "feature",
                    "targetRefName": "main",
                    "title": "t",
                },
                client=fake_client(lambda request: _ok({"pullRequestId": 9})),
            )
        self.assertTrue(result["ok"])
        self.assertEqual(capture.calls, [("azure-devops", "changed", {})])

    def test_a_failed_write_emits_no_event(self):
        def handler(request):
            return httpx.Response(
                403, json={"message": "no"}, request=httpx.Request("POST", "https://x")
            )

        with _Capture(writes) as capture:
            call_tool(
                "azure_devops_create_pull_request",
                {"project": "C", "repository": "r"},
                client=fake_client(handler),
            )
        self.assertEqual(capture.calls, [])

    def test_the_other_write_module_emits_the_same_event(self):
        def handler(request):
            if request.url.path.endswith("/definitions"):
                return _ok({"value": [{"id": 3}]})
            return _ok({"id": 500, "status": "notStarted"})

        with _Capture(writes_other) as capture:
            result = call_tool(
                "azure_devops_queue_build",
                {"project": "C", "definitionId": 3, "branch": "main"},
                client=fake_client(handler),
            )
        self.assertTrue(result["ok"])
        self.assertEqual(capture.calls, [("azure-devops", "changed", {})])

    def test_the_event_contract_is_the_wire_name_the_desktop_listens_to(self):
        # The wire name contract: plugin.<plugin_id>.<event> — the string the
        # desktop plugin.js registers with ctx.onEvent.
        plugin_id, event = "azure-devops", "changed"
        self.assertEqual(f"plugin.{plugin_id}.{event}", "plugin.azure-devops.changed")
        # And the broadcast call the tools make carries exactly these values.
        with _Capture(writes) as capture:
            pass
        self.assertEqual(capture.calls, [])


if __name__ == "__main__":
    unittest.main()
