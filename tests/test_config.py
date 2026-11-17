"""config.py: the manifest defaults are applied and a missing organization is reported."""

import unittest

from support import FakeContext, plugin_module

config = plugin_module("config")
errors = plugin_module("errors")


class ConfigTest(unittest.TestCase):
    def test_missing_organization_is_not_configured(self):
        cfg = config.load_config(FakeContext())
        self.assertEqual(cfg.missing_settings, ["organization"])
        self.assertFalse(cfg.is_configured)
        with self.assertRaises(errors.AdoError) as caught:
            cfg.require()
        self.assertEqual(caught.exception.code, "not_configured")
        self.assertIn("organization", str(caught.exception))

    def test_defaults_are_applied(self):
        cfg = config.load_config(FakeContext({"organization": "contoso"}))
        self.assertEqual(cfg.organization, "contoso")
        self.assertEqual(cfg.base_url, "https://dev.azure.com")
        self.assertEqual(cfg.api_version, "7.1")
        self.assertEqual(cfg.default_project, "")
        self.assertEqual(cfg.http_timeout_ms, 30000)
        self.assertTrue(cfg.is_configured)
        self.assertEqual(cfg.missing_settings, [])

    def test_configured_settings_win_over_defaults(self):
        cfg = config.load_config(
            FakeContext(
                {
                    "organization": "contoso",
                    "base_url": "https://dev.azure.com/",
                    "api_version": "7.0-preview.1",
                    "default_project": "Payments",
                    "http_timeout_ms": 5000,
                }
            )
        )
        self.assertEqual(cfg.base_url, "https://dev.azure.com")
        self.assertEqual(cfg.api_version, "7.0-preview.1")
        self.assertEqual(cfg.default_project, "Payments")
        self.assertEqual(cfg.http_timeout_ms, 5000)


if __name__ == "__main__":
    unittest.main()
