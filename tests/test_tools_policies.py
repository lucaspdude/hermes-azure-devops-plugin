"""tools_policies.py: the policy configurations of the project, and the warning."""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

POLICY = {
    "id": "fa2e6b1c-2b71-4a5f-9c39-1f0a2c3d4e5f",
    "url": "https://dev.azure.com/contoso/Contoso/_apis/policy/configurations/fa2e6b1c",
    "revision": 3,
    "isEnabled": True,
    "isBlocking": True,
    "type": {
        "id": "fa2e6b1c-policy-type",
        "displayName": "Minimum number of reviewers",
        "description": "Requires a minimum number of reviewers",
    },
    "settings": {"minimumApproverCount": 2, "scope": [{"repositoryId": None}]},
}


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=payload if payload is not None else {})

    return handler, seen


class ListPoliciesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_policies_are_read_from_the_configurations_of_the_project(self):
        handler, seen = recorder(payload={"count": 1, "value": [POLICY]})

        result = call_tool(
            "azure_devops_list_policies",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/policy/configurations")
        self.assertTrue(result["ok"])

    def test_the_policy_configurations_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [POLICY]})

        result = call_tool(
            "azure_devops_list_policies",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        policy = result["data"]["policies"][0]
        self.assertEqual(policy["id"], POLICY["id"])
        self.assertEqual(policy["isEnabled"], True)
        self.assertEqual(policy["isBlocking"], True)
        self.assertEqual(policy["type"]["displayName"], "Minimum number of reviewers")
        self.assertEqual(policy["settings"]["minimumApproverCount"], 2)

    def test_the_answer_says_the_policy_by_repository_is_not_reachable(self):
        handler, _ = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_policies",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        note = result["data"]["note"]
        self.assertIn("/_apis/policies/repositories/", note)
        self.assertIn("classic PAT", note)

    def test_the_answer_names_the_repository_that_was_asked_for(self):
        handler, _ = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_policies",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        note = result["data"]["note"]
        self.assertIn("'api'", note)
        self.assertIn("/_apis/policies/repositories/", note)
        self.assertIn("classic PAT", note)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, seen = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_policies",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertEqual(len(seen), 1)

    def test_a_call_without_project_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_policies",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
