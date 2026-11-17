"""errors.py: the closed taxonomy and the mapping of an HTTP failure."""

import json
import unittest

from support import plugin_module

errors = plugin_module("errors")


class TaxonomyTest(unittest.TestCase):
    def test_the_taxonomy_is_closed(self):
        self.assertEqual(
            set(errors.ERROR_CODES),
            {
                "not_configured",
                "missing_credential",
                "invalid_input",
                "unauthorized",
                "forbidden",
                "not_found",
                "rate_limited",
                "timeout",
                "upstream_error",
            },
        )

    def test_every_code_has_a_constant(self):
        for code in errors.ERROR_CODES:
            self.assertTrue(hasattr(errors, f"CODE_{code.upper()}"))

    def test_the_error_carries_code_message_status_and_type_key(self):
        exc = errors.AdoError("not_found", "missing", status=404, type_key="Key")
        self.assertEqual(exc.code, "not_found")
        self.assertEqual(exc.message, "missing")
        self.assertEqual(exc.status, 404)
        self.assertEqual(exc.type_key, "Key")
        self.assertEqual(str(exc), "missing")


class StatusMappingTest(unittest.TestCase):
    def test_401_is_unauthorized(self):
        exc = errors.error_for_response(401, '{"message": "bad token"}')
        self.assertEqual(exc.code, "unauthorized")
        self.assertEqual(exc.status, 401)

    def test_403_is_forbidden_and_points_at_the_pat_scope(self):
        exc = errors.error_for_response(403, '{"message": "denied"}')
        self.assertEqual(exc.code, "forbidden")
        self.assertIn("scope", str(exc).lower())

    def test_404_is_not_found(self):
        exc = errors.error_for_response(404, '{"message": "no such project"}')
        self.assertEqual(exc.code, "not_found")
        self.assertIn("no such project", str(exc))

    def test_429_is_rate_limited(self):
        exc = errors.error_for_response(429, '{"message": "slow down"}')
        self.assertEqual(exc.code, "rate_limited")
        self.assertEqual(exc.status, 429)

    def test_500_is_upstream_error(self):
        exc = errors.error_for_response(500, '{"message": "boom"}')
        self.assertEqual(exc.code, "upstream_error")
        self.assertEqual(exc.status, 500)

    def test_400_is_invalid_input(self):
        exc = errors.error_for_response(400, '{"message": "bad parameter"}')
        self.assertEqual(exc.code, "invalid_input")

    def test_the_body_message_and_type_key_are_preserved(self):
        body = json.dumps(
            {
                "$id": "1",
                "message": "TF401019: the project does not exist",
                "typeName": "Microsoft.TeamFoundation.Framework.Server...",
                "typeKey": "ProjectNotFoundException",
                "errorCode": 0,
            }
        )
        exc = errors.error_for_response(404, body)
        self.assertEqual(exc.code, "not_found")
        self.assertIn("TF401019", exc.message)
        self.assertEqual(exc.type_key, "ProjectNotFoundException")

    def test_a_body_that_is_not_json_keeps_the_status_code(self):
        exc = errors.error_for_response(401, "<html><body>Sign in</body></html>")
        self.assertEqual(exc.code, "unauthorized")
        self.assertIn("not JSON", str(exc))

    def test_a_body_that_is_not_json_on_500_is_upstream_error(self):
        exc = errors.error_for_response(500, "<html><body>Bad Gateway</body></html>")
        self.assertEqual(exc.code, "upstream_error")
        self.assertIn("not JSON", str(exc))

    def test_a_response_that_is_not_json_at_all_is_upstream_error(self):
        exc = errors.non_json_response_error(200)
        self.assertEqual(exc.code, "upstream_error")
        self.assertIn("not JSON", str(exc))

    def test_the_error_never_carries_a_stack_trace_in_its_message(self):
        exc = errors.error_for_response(500, '{"message": "boom"}')
        self.assertNotIn("Traceback", str(exc))
        self.assertIsNone(exc.__cause__)


if __name__ == "__main__":
    unittest.main()
