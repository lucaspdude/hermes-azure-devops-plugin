"""tools_artifacts.py: the artifacts a build published.

The route answers a **bare array** (no ``value`` envelope), and the url the
artifact is downloaded from travels in ``resource.downloadUrl``.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

ARTIFACTS = [
    {
        "id": 11,
        "name": "drop",
        "url": "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts",
        "resource": {
            "type": "Container",
            "data": "drop",
            "url": "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts",
            "downloadUrl": "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts?artifactName=drop",
        },
        "size": 4096,
        "expiresOn": "2026-12-17T09:00:00Z",
    },
    {
        "id": 12,
        "name": "logs",
        "url": "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts",
        "resource": {
            "type": "FilePath",
            "downloadUrl": "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts?artifactName=logs",
        },
        "size": 128,
    },
]

ARTIFACTS_ROUTE = "/contoso/Contoso/_apis/build/builds/42/artifacts"


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=payload if payload is not None else {})

    return handler, seen


class ListBuildArtifactsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_artifacts_route_is_called_with_the_build(self):
        handler, seen = recorder(payload=ARTIFACTS)

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso", "buildId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(seen[0].url.path, ARTIFACTS_ROUTE)
        self.assertTrue(result["ok"])

    def test_the_name_the_size_and_the_url_of_every_artifact_are_returned(self):
        handler, _ = recorder(payload=ARTIFACTS)

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso", "buildId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        artifacts = result["data"]["artifacts"]
        self.assertEqual(len(artifacts), 2)
        self.assertEqual(result["data"]["count"], 2)

        first = artifacts[0]
        self.assertEqual(first["name"], "drop")
        self.assertEqual(first["size"], 4096)
        self.assertEqual(
            first["url"],
            "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts?artifactName=drop",
        )
        self.assertEqual(
            first["artifactUrl"],
            "https://dev.azure.com/contoso/Contoso/_apis/build/builds/42/artifacts",
        )
        self.assertEqual(first["resourceType"], "Container")

        second = artifacts[1]
        self.assertEqual(second["name"], "logs")
        self.assertEqual(second["size"], 128)
        self.assertTrue(second["url"].endswith("artifactName=logs"))

    def test_a_build_without_artifacts_answers_an_empty_list(self):
        handler, _ = recorder(payload=[])

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso", "buildId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["artifacts"], [])
        self.assertEqual(result["data"]["count"], 0)

    def test_a_build_that_does_not_exist_answers_not_found(self):
        handler, seen = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso", "buildId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(len(seen), 1)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso", "buildId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")

    def test_a_call_without_build_answers_invalid_input(self):
        handler, seen = recorder(payload=[])

        result = call_tool(
            "azure_devops_list_build_artifacts",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
