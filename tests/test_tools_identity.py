"""tools_identity.py: the identity of the token and the identities of the organization.

The route is ``/_apis/connectionData``, which answers only on the preview
version of the API (``7.0-preview.1``): the version lives in the table of the
client, and these tests say which version travels on the wire.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

CONNECTION_DATA = {
    "authenticatedUser": {
        "id": "8f8b7a2c-1111-2222-3333-444455556666",
        "descriptor": "aad.MDAx",
        "subjectDescriptor": "aad.MDAx",
        "providerDisplayName": "Contoso",
        "isActive": True,
        "properties": {},
        "resourceVersion": 2,
        "featuresVersion": 1,
    },
    "authorizedUser": {
        "id": "8f8b7a2c-1111-2222-3333-444455556666",
        "descriptor": "aad.MDAx",
        "providerDisplayName": "Contoso",
        "isActive": True,
    },
    "instanceId": "9a8b7c6d-5555-6666-7777-888899990000",
    "deploymentId": "0b1c2d3e-4444-5555-6666-777788889999",
    "deploymentType": "hosted",
}

CONNECTION_DATA_ROUTE = "/contoso/_apis/connectionData"


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=payload if payload is not None else {})

    return handler, seen


class GetMyIdentityTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_connection_data_route_is_called(self):
        handler, seen = recorder(payload=CONNECTION_DATA)

        result = call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(seen[0].url.path, CONNECTION_DATA_ROUTE)
        self.assertTrue(result["ok"])

    def test_the_route_asks_for_the_preview_version_of_the_api(self):
        handler, seen = recorder(payload=CONNECTION_DATA)

        call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["api-version"], "7.0-preview.1")

    def test_the_identity_carries_the_id_and_the_display_name(self):
        payload = {
            "authenticatedUser": {
                "id": "8f8b7a2c-1111-2222-3333-444455556666",
                "descriptor": "aad.MDAx",
                "providerDisplayName": "Contoso",
                "isActive": True,
                "properties": {"DisplayName": "Ada Lovelace"},
            }
        }
        handler, _ = recorder(payload=payload)

        result = call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        identity = result["data"]["identity"]
        self.assertEqual(identity["id"], "8f8b7a2c-1111-2222-3333-444455556666")
        self.assertEqual(identity["displayName"], "Ada Lovelace")
        self.assertEqual(identity["descriptor"], "aad.MDAx")
        self.assertEqual(identity["isActive"], True)

    def test_the_display_name_falls_back_to_the_provider_of_the_identity(self):
        handler, _ = recorder(payload=CONNECTION_DATA)

        result = call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        identity = result["data"]["identity"]
        self.assertEqual(identity["id"], "8f8b7a2c-1111-2222-3333-444455556666")
        self.assertEqual(identity["displayName"], "Contoso")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")

    def test_a_bad_version_of_the_api_answers_invalid_input(self):
        handler, seen = recorder(status=400, payload={"message": "unsupported api-version"})

        result = call_tool(
            "azure_devops_get_my_identity",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(len(seen), 1)


class ListIdentitiesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_connection_data_route_is_called(self):
        handler, seen = recorder(payload=CONNECTION_DATA)

        result = call_tool(
            "azure_devops_list_identities",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, CONNECTION_DATA_ROUTE)
        self.assertTrue(result["ok"])

    def test_the_identities_carry_the_id_and_the_display_name(self):
        payload = {
            "authenticatedUser": {
                "id": "8f8b7a2c-1111-2222-3333-444455556666",
                "displayName": "Ada Lovelace",
                "descriptor": "aad.MDAx",
            },
            "identities": {
                "aad.MDAy": {
                    "id": "1a2b3c4d-5555-6666-7777-888899990000",
                    "displayName": "Grace Hopper",
                    "descriptor": "aad.MDAy",
                }
            },
        }
        handler, _ = recorder(payload=payload)

        result = call_tool(
            "azure_devops_list_identities",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        identities = result["data"]["identities"]
        self.assertEqual(result["data"]["count"], 2)
        self.assertEqual(identities[0]["id"], "8f8b7a2c-1111-2222-3333-444455556666")
        self.assertEqual(identities[0]["displayName"], "Ada Lovelace")
        self.assertEqual(identities[1]["id"], "1a2b3c4d-5555-6666-7777-888899990000")
        self.assertEqual(identities[1]["displayName"], "Grace Hopper")
        self.assertEqual(identities[1]["descriptor"], "aad.MDAy")

    def test_the_same_identity_is_listed_only_once(self):
        payload = {
            "authenticatedUser": {"id": "8f8b7a2c", "displayName": "Ada Lovelace"},
            "authorizedUser": {"id": "8f8b7a2c", "displayName": "Ada Lovelace"},
            "identities": {"aad.MDAx": {"id": "8f8b7a2c", "displayName": "Ada Lovelace"}},
        }
        handler, _ = recorder(payload=payload)

        result = call_tool(
            "azure_devops_list_identities",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["identities"][0]["displayName"], "Ada Lovelace")

    def test_the_identities_are_read_when_the_payload_carries_a_list(self):
        payload = {
            "identities": [
                {"id": "1a2b3c4d", "displayName": "Grace Hopper", "descriptor": "aad.MDAy"}
            ]
        }
        handler, _ = recorder(payload=payload)

        result = call_tool(
            "azure_devops_list_identities",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["identities"][0]["displayName"], "Grace Hopper")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_identities",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


if __name__ == "__main__":
    unittest.main()
