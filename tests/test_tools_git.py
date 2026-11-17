"""tools_git.py: the refs of a repository and its commits.

The traps of the verification live here: the branch of the commits route is
the **short name** (the full ref answers 404), the branch of the refs route is
the short name too, and the page size travels as ``$top``.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

REPOSITORY = {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "api",
    "url": "https://dev.azure.com/contoso/Contoso/_git/api",
    "defaultBranch": "refs/heads/master",
}

BRANCH = {
    "name": "refs/heads/master",
    "objectId": "8c7d6e5f-4a3b-42c1-9e8f-7a6b5c4d3e2f",
    "url": "https://dev.azure.com/contoso/Contoso/_apis/git/repositories/api/refs/heads/master",
}

TAG = {
    "name": "refs/tags/v1.0",
    "objectId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "url": "https://dev.azure.com/contoso/Contoso/_apis/git/repositories/api/refs/tags/v1.0",
}

COMMIT = {
    "commitId": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "comment": "Fix the timeout",
    "author": {"name": "Ada Lovelace", "email": "ada@contoso.com", "date": "2026-11-17T09:00:00Z"},
    "committer": {"name": "Ada Lovelace", "email": "ada@contoso.com", "date": "2026-11-17T09:00:00Z"},
    "changeCounts": {"Add": 1, "Edit": 2, "Delete": 0},
    "commentCount": 2,
    "url": "https://dev.azure.com/contoso/Contoso/_apis/git/repositories/api/commits/1a2b",
}

REFS_ROUTE = "/contoso/Contoso/_apis/git/repositories/api/refs"
COMMITS_ROUTE = "/contoso/Contoso/_apis/git/repositories/api/commits"

#: The route of the refs when the repository is resolved by the plugin (by id).
RESOLVED_REFS_ROUTE = (
    "/contoso/Contoso/_apis/git/repositories/3fa85f64-5717-4562-b3fc-2c963f66afa6/refs"
)


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            status,
            json=payload if payload is not None else {},
        )

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


class ListBranchesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_refs_route_is_called_with_the_heads_filter(self):
        handler, seen = recorder(payload={"count": 1, "value": [BRANCH]})

        result = call_tool(
            "azure_devops_list_branches",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, REFS_ROUTE)
        self.assertEqual(seen[0].url.params["filter"], "heads")
        self.assertTrue(result["ok"])

    def test_the_branches_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [BRANCH]})

        result = call_tool(
            "azure_devops_list_branches",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        branch = result["data"]["branches"][0]
        self.assertEqual(branch["name"], "master")
        self.assertEqual(branch["ref"], "refs/heads/master")
        self.assertEqual(branch["objectId"], BRANCH["objectId"])
        self.assertEqual(result["data"]["count"], 1)

    def test_the_only_repository_of_the_project_is_resolved(self):
        handler, seen = router(
            {
                "/contoso/Contoso/_apis/git/repositories": {"count": 1, "value": [REPOSITORY]},
                RESOLVED_REFS_ROUTE: {"count": 1, "value": [BRANCH]},
            }
        )

        result = call_tool(
            "azure_devops_list_branches",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[1].url.path, RESOLVED_REFS_ROUTE)
        self.assertTrue(result["ok"])

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_branches",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class GetBranchTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_branch_route_is_called_with_the_short_name(self):
        handler, seen = recorder(payload=BRANCH)

        result = call_tool(
            "azure_devops_get_branch",
            {"project": "Contoso", "repository": "api", "branch": "master"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, f"{REFS_ROUTE}/heads/master")
        self.assertEqual(result["data"]["branch"]["name"], "master")

    def test_the_full_ref_is_accepted_and_shortened(self):
        handler, seen = recorder(payload=BRANCH)

        call_tool(
            "azure_devops_get_branch",
            {"project": "Contoso", "repository": "api", "branch": "refs/heads/master"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, f"{REFS_ROUTE}/heads/master")

    def test_an_unknown_branch_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_branch",
            {"project": "Contoso", "repository": "api", "branch": "nope"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)

    def test_a_call_without_a_branch_answers_invalid_input(self):
        handler, seen = recorder(payload=BRANCH)

        result = call_tool(
            "azure_devops_get_branch",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class ListCommitsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_commits_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [COMMIT]})

        result = call_tool(
            "azure_devops_list_commits",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, COMMITS_ROUTE)
        self.assertTrue(result["ok"])

    def test_the_branch_travels_as_the_short_name(self):
        handler, seen = recorder(payload={"count": 1, "value": [COMMIT]})

        call_tool(
            "azure_devops_list_commits",
            {"project": "Contoso", "repository": "api", "branch": "refs/heads/master"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["branch"], "master")

    def test_the_page_size_travels_with_the_dollar_sign(self):
        handler, seen = recorder(payload={"count": 1, "value": [COMMIT]})

        call_tool(
            "azure_devops_list_commits",
            {"project": "Contoso", "repository": "api", "top": 10},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        raw = seen[0].url.raw_path.decode("utf-8")
        self.assertIn("%24top=10", raw)
        self.assertNotIn("top=10", raw.replace("%24top=10", ""))

    def test_the_commits_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [COMMIT]})

        result = call_tool(
            "azure_devops_list_commits",
            {"project": "Contoso", "repository": "api", "branch": "master"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        commit = result["data"]["commits"][0]
        self.assertEqual(commit["commitId"], COMMIT["commitId"])
        self.assertEqual(commit["comment"], "Fix the timeout")
        self.assertEqual(commit["author"]["name"], "Ada Lovelace")
        self.assertEqual(commit["author"]["date"], "2026-11-17T09:00:00Z")
        self.assertEqual(result["data"]["count"], 1)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_commits",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class GetCommitTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_commit_route_is_called_with_the_id(self):
        handler, seen = recorder(payload=COMMIT)

        result = call_tool(
            "azure_devops_get_commit",
            {"project": "Contoso", "repository": "api", "commitId": COMMIT["commitId"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            f"{COMMITS_ROUTE}/{COMMIT['commitId']}",
        )
        self.assertEqual(result["data"]["commit"]["comment"], "Fix the timeout")

    def test_the_change_count_travels_in_the_request(self):
        handler, seen = recorder(payload=COMMIT)

        call_tool(
            "azure_devops_get_commit",
            {
                "project": "Contoso",
                "repository": "api",
                "commitId": COMMIT["commitId"],
                "changeCount": 5,
            },
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["changeCount"], "5")

    def test_an_unknown_commit_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_commit",
            {"project": "Contoso", "repository": "api", "commitId": "deadbeef"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")

    def test_a_call_without_a_commit_answers_invalid_input(self):
        handler, seen = recorder(payload=COMMIT)

        result = call_tool(
            "azure_devops_get_commit",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class ListTagsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_refs_route_is_called_with_the_tags_filter(self):
        handler, seen = recorder(payload={"count": 1, "value": [TAG]})

        result = call_tool(
            "azure_devops_list_tags",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, REFS_ROUTE)
        self.assertEqual(seen[0].url.params["filter"], "tags")
        self.assertTrue(result["ok"])

    def test_the_tags_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [TAG]})

        result = call_tool(
            "azure_devops_list_tags",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        tag = result["data"]["tags"][0]
        self.assertEqual(tag["name"], "v1.0")
        self.assertEqual(tag["ref"], "refs/tags/v1.0")
        self.assertEqual(tag["objectId"], TAG["objectId"])
        self.assertEqual(result["data"]["count"], 1)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_tags",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


if __name__ == "__main__":
    unittest.main()
