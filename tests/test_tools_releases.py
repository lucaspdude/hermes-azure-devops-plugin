"""tools_releases.py: the release definitions and the releases.

The routes of Release Management do not exist on the API host: they answer on
``vsrm.dev.azure.com``, and the path carries the segment of the organization
**and** of the project.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

DEFINITIONS = [
    {
        "id": 12,
        "name": "web-release",
        "path": "\\web",
        "releaseType": "modern",
        "url": "https://vsrm.dev.azure.com/contoso/Contoso/_apis/release/definitions/12",
    },
    {
        "id": 13,
        "name": "api-release",
        "path": "\\api",
        "releaseType": "modern",
        "url": "https://vsrm.dev.azure.com/contoso/Contoso/_apis/release/definitions/13",
    },
]

RELEASES = [
    {
        "id": 42,
        "name": "Contoso-web-42",
        "status": "active",
        "createdOn": "2026-11-17T09:00:00Z",
        "modifiedOn": "2026-11-17T10:00:00Z",
        "definition": {"id": 12, "name": "web-release"},
        "environments": [
            {"id": 1, "name": "Dev", "status": "succeeded", "rank": 1},
            {"id": 2, "name": "Prod", "status": "inProgress", "rank": 2},
        ],
        "url": "https://vsrm.dev.azure.com/contoso/Contoso/_apis/release/releases/42",
    }
]

DEFINITIONS_ROUTE = "/contoso/Contoso/_apis/release/definitions"
RELEASES_ROUTE = "/contoso/Contoso/_apis/release/releases"
RELEASE_ROUTE = "/contoso/Contoso/_apis/release/releases/42"


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=payload if payload is not None else {})

    return handler, seen


def router(routes, default_status=404):
    """The fake transport of a test that makes more than one call."""
    seen = []

    def handler(request):
        seen.append(request)
        payload = routes.get(request.url.path)
        if payload is None:
            return httpx.Response(default_status, json={"message": "not found"})
        return httpx.Response(200, json=payload)

    return handler, seen


class ListReleaseDefinitionsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_definitions_route_goes_to_the_release_host(self):
        handler, seen = recorder(payload={"count": 2, "value": DEFINITIONS})

        result = call_tool(
            "azure_devops_list_release_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.host, "vsrm.dev.azure.com")
        self.assertEqual(seen[0].url.path, DEFINITIONS_ROUTE)
        self.assertEqual(
            str(seen[0].url).split("?")[0],
            "https://vsrm.dev.azure.com/contoso/Contoso/_apis/release/definitions",
        )
        self.assertTrue(result["ok"])

    def test_the_definitions_are_normalized(self):
        handler, _ = recorder(payload={"count": 2, "value": DEFINITIONS})

        result = call_tool(
            "azure_devops_list_release_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        definition = result["data"]["definitions"][0]
        self.assertEqual(definition["id"], 12)
        self.assertEqual(definition["name"], "web-release")
        self.assertEqual(definition["path"], "\\web")
        self.assertEqual(result["data"]["count"], 2)

    def test_a_name_filters_the_definitions(self):
        handler, seen = recorder(payload={"count": 2, "value": DEFINITIONS})

        result = call_tool(
            "azure_devops_list_release_definitions",
            {"project": "Contoso", "name": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["definitionName"], "api")
        definitions = result["data"]["definitions"]
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["name"], "api-release")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_release_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class ListReleasesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_releases_route_goes_to_the_release_host(self):
        handler, seen = recorder(payload={"count": 1, "value": RELEASES})

        result = call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.host, "vsrm.dev.azure.com")
        self.assertEqual(seen[0].url.path, RELEASES_ROUTE)
        self.assertEqual(
            str(seen[0].url).split("?")[0],
            "https://vsrm.dev.azure.com/contoso/Contoso/_apis/release/releases",
        )
        self.assertTrue(result["ok"])

    def test_the_releases_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": RELEASES})

        result = call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        release = result["data"]["releases"][0]
        self.assertEqual(release["id"], 42)
        self.assertEqual(release["name"], "Contoso-web-42")
        self.assertEqual(release["status"], "active")
        self.assertEqual(release["definition"]["name"], "web-release")
        self.assertEqual(release["environments"][0]["name"], "Dev")
        self.assertEqual(release["environments"][1]["status"], "inProgress")

    def test_the_definition_filters_the_releases_by_id(self):
        handler, seen = recorder(payload={"count": 1, "value": RELEASES})

        call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso", "definition": "12"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["definitionId"], "12")

    def test_a_definition_named_is_resolved_to_its_id(self):
        handler, seen = router(
            {
                DEFINITIONS_ROUTE: {"count": 2, "value": DEFINITIONS},
                RELEASES_ROUTE: {"count": 1, "value": RELEASES},
            }
        )

        result = call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso", "definition": "web-release"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].url.path, DEFINITIONS_ROUTE)
        self.assertEqual(seen[0].url.params["definitionName"], "web-release")
        self.assertEqual(seen[1].url.path, RELEASES_ROUTE)
        self.assertEqual(seen[1].url.params["definitionId"], "12")
        self.assertTrue(result["ok"])

    def test_a_definition_that_does_not_exist_answers_not_found(self):
        handler, _ = router({DEFINITIONS_ROUTE: {"count": 0, "value": []}})

        result = call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso", "definition": "ghost"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_releases",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class GetReleaseTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_release_route_goes_to_the_release_host(self):
        handler, seen = recorder(payload=RELEASES[0])

        result = call_tool(
            "azure_devops_get_release",
            {"project": "Contoso", "releaseId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.host, "vsrm.dev.azure.com")
        self.assertEqual(seen[0].url.path, RELEASE_ROUTE)
        self.assertTrue(result["ok"])

    def test_the_release_is_normalized(self):
        handler, _ = recorder(payload=RELEASES[0])

        result = call_tool(
            "azure_devops_get_release",
            {"project": "Contoso", "releaseId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        release = result["data"]["release"]
        self.assertEqual(release["id"], 42)
        self.assertEqual(release["name"], "Contoso-web-42")
        self.assertEqual(release["status"], "active")
        self.assertEqual(release["definition"]["id"], 12)
        self.assertEqual(len(release["environments"]), 2)

    def test_a_release_that_does_not_exist_answers_not_found(self):
        handler, seen = recorder(status=404, payload={"message": "release not found"})

        result = call_tool(
            "azure_devops_get_release",
            {"project": "Contoso", "releaseId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)
        self.assertEqual(len(seen), 1)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_get_release",
            {"project": "Contoso", "releaseId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")

    def test_a_call_without_release_answers_invalid_input(self):
        handler, seen = recorder(payload=RELEASES[0])

        result = call_tool(
            "azure_devops_get_release",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
