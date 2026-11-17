"""Toda tool registrada descreve-se de forma curta e acionavel, sem carregar o contrato.

O contrato (escopos de PAT, paginacao, codigos de erro) vive nas skills; a
descricao da tool e o que aparece no contexto do modelo e tem que ser curta.
"""

import unittest

from support import plugin_module

registry = plugin_module("registry")

# O contrato pertence as skills: nenhum desses termos deve aparecer na descricao.
CONTRACT_TERMS = ("vso.", "continuationToken", "x-ms-continuationtoken", "api-version", "scope")


class DescriptionTest(unittest.TestCase):
    def test_every_tool_has_a_check_fn(self):
        missing = [t.name for t in registry.TOOLS if t.check_fn is None]
        self.assertEqual(missing, [])

    def test_every_tool_has_a_substantive_description(self):
        short = [t.name for t in registry.TOOLS if len(t.description.strip()) < 40]
        self.assertEqual(short, [])

    def test_no_description_carries_the_contract(self):
        carriers = [
            t.name
            for t in registry.TOOLS
            for term in CONTRACT_TERMS
            if term in t.description
        ]
        self.assertEqual(carriers, [])

    def test_descriptions_say_what_and_when(self):
        vague = [t.name for t in registry.TOOLS if t.description.strip().endswith(".") is False]
        self.assertEqual(vague, [])


if __name__ == "__main__":
    unittest.main()
