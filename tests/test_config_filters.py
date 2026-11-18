"""The new filter settings: ignored projects and the default lookback window."""

import unittest

from support import FakeContext, plugin_module

config = plugin_module("config")


class IgnoredProjectsTest(unittest.TestCase):
    def test_defaults_are_empty_list_and_seven_days(self):
        cfg = config.load_config(FakeContext({"organization": "contoso"}))
        self.assertEqual(cfg.ignored_projects, ())
        self.assertEqual(cfg.default_days, 7)

    def test_list_of_names_is_normalized_trimmed_and_deduped(self):
        cfg = config.load_config(FakeContext({
            "organization": "contoso",
            "ignored_projects": ["Proj A", "proj a", "  Proj B  ", ""],
        }))
        self.assertEqual(cfg.ignored_projects, ("Proj A", "Proj B"))

    def test_comma_separated_string_is_accepted(self):
        cfg = config.load_config(FakeContext({
            "organization": "contoso",
            "ignored_projects": "Proj A, Proj B",
        }))
        self.assertEqual(cfg.ignored_projects, ("Proj A", "Proj B"))

    def test_ids_are_kept_exact_for_id_matching(self):
        cfg = config.load_config(FakeContext({
            "organization": "contoso",
            "ignored_projects": ["8a3f9d20-1111-4c2e-8d54-9f1e2d3c4b5a"],
        }))
        self.assertEqual(cfg.ignored_project_ids, frozenset({"8a3f9d20-1111-4c2e-8d54-9f1e2d3c4b5a"}))


class DefaultDaysTest(unittest.TestCase):
    def test_default_days_is_clamped_to_the_supported_range(self):
        cfg = config.load_config(FakeContext({"organization": "c", "default_days": 500}))
        self.assertEqual(cfg.default_days, config.MAX_DAYS)
        cfg = config.load_config(FakeContext({"organization": "c", "default_days": 0}))
        self.assertEqual(cfg.default_days, config.MIN_DAYS)

    def test_max_and_min_constants(self):
        self.assertEqual(config.MAX_DAYS, 90)
        self.assertEqual(config.MIN_DAYS, 1)


if __name__ == "__main__":
    unittest.main()
