"""Conflito de versao (412/precondition) e reportado, nunca contornado.

A delta spec exige que um objeto alterado por outra pessoa entre a leitura e a
escrita produza o erro com a mensagem da API, sem nova tentativa e sem
alteracao parcial.
"""

import unittest

import httpx

from support import call_tool, fake_client


def _conflict(request):
    return httpx.Response(
        412,
        json={"message": "The item you are trying to update has been changed by another user."},
        request=httpx.Request("PATCH", "https://x"),
    )


class WorkItemConflictTest(unittest.TestCase):
    def test_a_412_on_the_patch_answers_the_api_message_without_retry(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return _conflict(request)

        result = call_tool(
            "azure_devops_update_work_item",
            {
                "workItemId": 42,
                "operations": [{"op": "replace", "path": "/fields/System.State", "value": "Done"}],
            },
            client=fake_client(handler),
        )
        self.assertFalse(result["ok"])
        self.assertIn("changed by another user", result["error"]["message"])
        self.assertEqual(calls["n"], 1, "nenhuma nova tentativa apos o conflito")


class WikiConflictTest(unittest.TestCase):
    def test_a_412_on_the_wiki_put_answers_without_retry(self):
        calls = {"n": 0}

        def handler(request):
            if request.url.path.endswith("/_apis/wiki/wikis"):
                return httpx.Response(
                    200,
                    json={"value": [{"id": "w-1", "remoteUrl": "https://dev.azure.com/contoso/8a3f9d20-1111-4c2e-8d54-9f1e2d3c4b5a/_wiki/wikis/w-1"}]},
                    request=httpx.Request("GET", "https://x"),
                )
            calls["n"] += 1
            return _conflict(request)

        result = call_tool(
            "azure_devops_update_wiki_page",
            {"project": "p", "wiki": "w-1", "path": "/Home", "content": "x", "version": 3},
            client=fake_client(handler),
        )
        self.assertFalse(result["ok"])
        self.assertIn("changed by another user", result["error"]["message"])
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
