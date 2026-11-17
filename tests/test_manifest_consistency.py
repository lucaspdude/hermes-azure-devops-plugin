"""The manifest and the registry must declare the same tools.

The manifest is generated from the registry: when the two disagree, the
plugin would advertise tools it does not register (or hide tools it does),
so the divergence has to fail the suite and name the tool to fix.
"""

import unittest

from support import PLUGIN_DIR, manifest_provides_tools, plugin_module, tool_divergence

registry = plugin_module("registry")


class ManifestConsistencyTest(unittest.TestCase):
    def test_the_manifest_declares_exactly_the_registered_tools(self):
        declared = manifest_provides_tools()
        registered = registry.tool_names()
        missing, extra = tool_divergence(declared, registered)

        self.assertEqual(
            missing,
            [],
            "tool(s) registered but missing from the manifest: " + ", ".join(missing),
        )
        self.assertEqual(
            extra,
            [],
            "tool(s) declared in the manifest but not registered: " + ", ".join(extra),
        )
        self.assertEqual(declared, registered, "the manifest must list the tools in registry order")

    def test_the_manifest_holds_the_generated_block(self):
        manifest = (PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8")

        self.assertIn(registry.provides_tools_block(), manifest)

    def test_a_tool_missing_from_the_manifest_is_named(self):
        declared = ["azure_devops_list_projects"]
        registered = ["azure_devops_list_projects", "azure_devops_list_builds"]

        missing, extra = tool_divergence(declared, registered)

        self.assertEqual(missing, ["azure_devops_list_builds"])
        self.assertEqual(extra, [])

    def test_a_tool_declared_but_not_registered_is_named(self):
        declared = ["azure_devops_list_projects", "azure_devops_list_builds"]
        registered = ["azure_devops_list_projects"]

        missing, extra = tool_divergence(declared, registered)

        self.assertEqual(missing, [])
        self.assertEqual(extra, ["azure_devops_list_builds"])


if __name__ == "__main__":
    unittest.main()
