"""registry.py: one registry, the manifest block it generates, and the registration."""

import json
import unittest

from support import FakeContext, load_plugin_package, plugin_module

registry = plugin_module("registry")
package = load_plugin_package()


def fake_tool(name, **overrides):
    """A tool of the registry that talks to nothing."""
    fields = {
        "toolset": "azure-devops",
        "schema": {
            "type": "function",
            "function": {"name": name, "parameters": {"type": "object", "properties": {}}},
        },
        "handler": lambda args, **kwargs: {"tool": name},
        "check_fn": lambda: True,
        "description": f"fake tool {name}",
        "requires_env": ("AZURE_DEVOPS_PAT_TOKEN",),
    }
    fields.update(overrides)
    return registry.ToolSpec(name=name, **fields)


class GeneratorTest(unittest.TestCase):
    def test_the_generator_lists_the_tools_of_the_registry(self):
        tools = [fake_tool("azure_devops_list_projects"), fake_tool("azure_devops_list_builds")]

        self.assertEqual(
            registry.tool_names(tools),
            ["azure_devops_list_projects", "azure_devops_list_builds"],
        )

    def test_the_generator_writes_the_manifest_block(self):
        tools = [fake_tool("azure_devops_list_projects"), fake_tool("azure_devops_list_builds")]

        self.assertEqual(
            registry.provides_tools_block(tools),
            "provides_tools:\n"
            "  - azure_devops_list_projects\n"
            "  - azure_devops_list_builds\n",
        )

    def test_the_generator_is_deterministic(self):
        tools = [fake_tool("azure_devops_list_projects"), fake_tool("azure_devops_list_builds")]

        self.assertEqual(registry.provides_tools_block(tools), registry.provides_tools_block(tools))
        self.assertEqual(registry.tool_names(tools), registry.tool_names(tools))

    def test_the_generator_keeps_the_registry_order(self):
        tools = [fake_tool("azure_devops_list_builds"), fake_tool("azure_devops_list_projects")]

        self.assertEqual(
            registry.tool_names(tools),
            ["azure_devops_list_builds", "azure_devops_list_projects"],
        )
        self.assertIn(
            "  - azure_devops_list_builds\n  - azure_devops_list_projects\n",
            registry.provides_tools_block(tools),
        )

    def test_an_empty_registry_produces_an_empty_block(self):
        self.assertEqual(registry.provides_tools_block([]), "provides_tools: []\n")
        self.assertEqual(registry.tool_names([]), [])

    def test_the_block_of_the_registry_is_the_block_of_the_tools(self):
        self.assertEqual(
            registry.provides_tools_block(),
            registry.provides_tools_block(registry.TOOLS),
        )


class RegistrationTest(unittest.TestCase):
    def setUp(self):
        self.original = list(registry.TOOLS)

    def tearDown(self):
        registry.TOOLS[:] = self.original

    def test_register_registers_exactly_the_tools_of_the_registry(self):
        tools = [fake_tool("azure_devops_list_projects"), fake_tool("azure_devops_list_builds")]
        registry.TOOLS[:] = tools
        ctx = FakeContext()

        package.register(ctx)

        self.assertEqual(
            [call["name"] for call in ctx.registered_tools],
            ["azure_devops_list_projects", "azure_devops_list_builds"],
        )

    def test_register_passes_the_spec_of_each_tool(self):
        tools = [fake_tool("azure_devops_list_projects")]
        registry.TOOLS[:] = tools
        ctx = FakeContext()

        package.register(ctx)

        call = ctx.registered_tools[0]
        self.assertEqual(call["toolset"], "azure-devops")
        self.assertEqual(call["schema"], tools[0].schema)
        self.assertIs(call["check_fn"], tools[0].check_fn)
        self.assertEqual(call["requires_env"], ["AZURE_DEVOPS_PAT_TOKEN"])
        self.assertEqual(call["description"], tools[0].description)
        self.assertTrue(callable(call["handler"]))

    def test_the_registered_handler_answers_the_envelope(self):
        def handler(args, **kwargs):
            return {"projects": []}

        registry.TOOLS[:] = [fake_tool("azure_devops_list_projects", handler=handler)]
        ctx = FakeContext()

        package.register(ctx)

        payload = json.loads(ctx.registered_tools[0]["handler"]({}))
        self.assertEqual(payload, {"ok": True, "data": {"projects": []}})

    def test_an_empty_registry_registers_nothing(self):
        registry.TOOLS[:] = []
        ctx = FakeContext()

        package.register(ctx)

        self.assertEqual(ctx.registered_tools, [])


if __name__ == "__main__":
    unittest.main()
