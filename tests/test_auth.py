"""auth.py: the PAT comes from the secret scope; a missing secret is a clean error."""

import traceback
import unittest

from support import plugin_module

auth = plugin_module("auth")
errors = plugin_module("errors")


class AuthTest(unittest.TestCase):
    def test_pat_is_read_from_the_secret_scope(self):
        asked = []

        def resolver(name):
            asked.append(name)
            return "pat-value"

        self.assertEqual(auth.resolve_pat(resolver=resolver), "pat-value")
        self.assertEqual(asked, ["AZURE_DEVOPS_PAT_TOKEN"])

    def test_missing_secret_is_missing_credential(self):
        with self.assertRaises(errors.AdoError) as caught:
            auth.resolve_pat(resolver=lambda name: None)
        exc = caught.exception
        self.assertEqual(exc.code, "missing_credential")
        self.assertIn("AZURE_DEVOPS_PAT_TOKEN", str(exc))

    def test_missing_secret_has_no_stack_trace(self):
        try:
            auth.resolve_pat(resolver=lambda name: None)
        except errors.AdoError as exc:
            self.assertEqual(str(exc), exc.message)
            self.assertNotIn("Traceback", str(exc))
            self.assertIsNone(exc.__cause__)
            self.assertIsNone(exc.__context__)
        else:
            self.fail("a missing secret must raise AdoError")

    def test_failing_secret_scope_has_no_stack_trace(self):
        def failing_resolver(name):
            raise RuntimeError("the secret scope is not installed")

        try:
            auth.resolve_pat(resolver=failing_resolver)
        except errors.AdoError as exc:
            rendered = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            self.assertEqual(exc.code, "missing_credential")
            self.assertIsNone(exc.__cause__)
            self.assertNotIn("RuntimeError", rendered)
            self.assertNotIn("During handling of the above exception", rendered)
        else:
            self.fail("a failing secret scope must raise AdoError")

    def test_pat_value_never_appears_in_the_message(self):
        leaked = "azure-devops-pat-0123456789"

        def leaky_resolver(name):
            raise RuntimeError(f"could not read {leaked}")

        with self.assertRaises(errors.AdoError) as caught:
            auth.resolve_pat(resolver=leaky_resolver)
        self.assertEqual(caught.exception.code, "missing_credential")
        self.assertNotIn(leaked, str(caught.exception))

    def test_check_fn_reports_the_missing_credential(self):
        self.assertFalse(auth.check_pat_available(resolver=lambda name: None))
        self.assertTrue(auth.check_pat_available(resolver=lambda name: "pat-value"))


if __name__ == "__main__":
    unittest.main()
