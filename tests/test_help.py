"""The help surfaces: the same content, rendered from the two embedded skills."""

import unittest

from support import plugin_module

help_module = plugin_module("help")


class HelpTest(unittest.TestCase):
    def test_the_guide_carries_both_sections(self):
        guide = help_module.render_help()
        self.assertIn("Usage contract", guide)
        self.assertIn("Workflows", guide)

    def test_the_guide_carries_the_scopes_of_every_family(self):
        guide = help_module.render_help()
        for scope in (
            "vso.code",
            "vso.build",
            "vso.work",
            "vso.project",
            "vso.release",
            "vso.wiki",
            "vso.identity",
        ):
            self.assertIn(scope, guide)

    def test_the_guide_carries_the_error_codes(self):
        guide = help_module.render_help()
        for code in (
            "not_configured",
            "missing_credential",
            "invalid_input",
            "unauthorized",
            "forbidden",
            "not_found",
            "rate_limited",
            "timeout",
            "upstream_error",
        ):
            self.assertIn(code, guide)

    def test_a_requested_topic_is_highlighted(self):
        guide = help_module.render_help("pull requests")
        self.assertIn("(requested)", guide)
        self.assertIn("Workflows", guide)

    def test_an_unknown_topic_still_answers_the_guide(self):
        guide = help_module.render_help("xyz")
        self.assertIn("no section matches", guide)
        self.assertIn("Usage contract", guide)

    def test_the_skills_are_the_source_of_the_content(self):
        for topic in help_module.help_topics():
            body = help_module._skill_body(topic)
            self.assertGreater(len(body), 200, topic)


class RegistrationTest(unittest.TestCase):
    def test_the_skills_and_the_help_command_are_registered(self):
        from support import bind_context

        ctx = bind_context()
        package = plugin_module("__init__")
        package.register(ctx)
        names = {name for name, _ in ctx.registered_skills}
        self.assertEqual(names, {"azure-devops-usage", "azure-devops-workflows"})
        commands = [c["name"] for c in ctx.registered_commands]
        self.assertIn("ado-help", commands)


if __name__ == "__main__":
    unittest.main()
