"""The response envelope of every tool: success, error, and no escaping exception.

Every tool answers a JSON string: ``{"ok": true, "data": ...}`` on the happy
path and ``{"ok": false, "error": {...}}`` on the failure path. No exception
escapes the handler, whatever the API does.
"""

import inspect
import json
import unittest

import httpx

from support import FakeContext, fake_client, fake_secret_resolver, mock_transport, plugin_module

auth = plugin_module("auth")
client = plugin_module("client")
config = plugin_module("config")
errors = plugin_module("errors")
registry = plugin_module("registry")


class SuccessEnvelopeTest(unittest.TestCase):
    def test_the_success_envelope_is_ok_true_with_the_data(self):
        payload = json.loads(registry.success_response({"projects": []}))

        self.assertEqual(payload, {"ok": True, "data": {"projects": []}})

    def test_the_success_envelope_is_a_json_string(self):
        self.assertIsInstance(registry.success_response({"a": 1}), str)


class ErrorEnvelopeTest(unittest.TestCase):
    def test_the_error_envelope_is_ok_false_with_the_error(self):
        error = errors.AdoError(
            errors.CODE_NOT_FOUND,
            "Azure DevOps did not find the requested resource.",
            status=404,
            type_key="ProjectNotFoundException",
        )

        payload = json.loads(registry.error_response(error))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_found")
        self.assertEqual(payload["error"]["message"], error.message)
        self.assertEqual(payload["error"]["status"], 404)
        self.assertEqual(payload["error"]["typeKey"], "ProjectNotFoundException")

    def test_the_error_envelope_carries_the_minimum_context(self):
        error = errors.AdoError(errors.CODE_TIMEOUT, "Azure DevOps timed out the request.")

        payload = json.loads(registry.error_response(error))

        self.assertEqual(set(payload["error"]), {"code", "message"})

    def test_the_error_envelope_is_a_json_string(self):
        self.assertIsInstance(registry.error_response(errors.AdoError("timeout", "slow")), str)


class GuardedHandlerTest(unittest.TestCase):
    def test_a_successful_handler_answers_the_success_envelope(self):
        guarded = registry.guarded_handler(lambda args, **kwargs: {"projects": []})

        payload = json.loads(guarded({}))

        self.assertEqual(payload, {"ok": True, "data": {"projects": []}})

    def test_an_ado_error_answers_the_error_envelope(self):
        def handler(args, **kwargs):
            raise errors.AdoError(errors.CODE_FORBIDDEN, "Azure DevOps denied the operation.")

        guarded = registry.guarded_handler(handler)

        payload = json.loads(guarded({}))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "forbidden")

    def test_an_unexpected_exception_never_escapes(self):
        def handler(args, **kwargs):
            raise RuntimeError("the API did something nobody expected")

        guarded = registry.guarded_handler(handler)

        payload = json.loads(guarded({}))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "upstream_error")

    def test_the_text_of_an_unexpected_exception_is_not_repeated(self):
        secret = "azure-devops-pat-0123456789"

        def handler(args, **kwargs):
            raise RuntimeError(f"the token {secret} leaked here")

        guarded = registry.guarded_handler(handler)

        self.assertNotIn(secret, guarded({}))

    def test_a_payload_that_is_not_json_serializable_does_not_escape(self):
        guarded = registry.guarded_handler(lambda args, **kwargs: object())

        payload = json.loads(guarded({}))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "upstream_error")

    def test_the_guard_keeps_the_signature_of_the_handler(self):
        def handler(args, task_id=None):
            return {"task_id": task_id}

        guarded = registry.guarded_handler(handler)

        self.assertEqual(list(inspect.signature(guarded).parameters), ["args", "task_id"])


class ToolHandlerTest(unittest.TestCase):
    """The envelope of a handler that talks to Azure DevOps through the harness."""

    def handler(self, args, **kwargs):
        settings = kwargs.get("settings") or {}
        cfg = config.load_config(FakeContext(settings)).require()
        pat = auth.resolve_pat(resolver=fake_secret_resolver())
        adoc = client.AdoClient(
            cfg,
            pat,
            transport=mock_transport(
                lambda request: httpx.Response(200, json={"value": [{"id": "contoso"}]})
            ),
        )
        return adoc.get("_apis/projects").json()

    def test_a_configured_handler_answers_the_success_envelope(self):
        guarded = registry.guarded_handler(self.handler)

        payload = json.loads(guarded({}, settings={"organization": "contoso"}))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"], {"value": [{"id": "contoso"}]})

    def test_a_handler_without_the_organization_answers_not_configured(self):
        guarded = registry.guarded_handler(self.handler)

        payload = json.loads(guarded({}, settings={}))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "not_configured")
        self.assertIn("organization", payload["error"]["message"])

    def test_a_failing_api_answers_the_error_envelope(self):
        def handler(args, **kwargs):
            adoc = fake_client(lambda request: httpx.Response(403, json={"message": "denied"}))
            return adoc.get("_apis/projects").json()

        guarded = registry.guarded_handler(handler)

        payload = json.loads(guarded({}))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "forbidden")
        self.assertEqual(payload["error"]["status"], 403)


if __name__ == "__main__":
    unittest.main()
