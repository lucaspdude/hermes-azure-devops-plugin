"""tools_projects.py: the routes of projects and repositories, and their answers."""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

PROJECT = {
    "id": "6f9c1e0a-6c3e-4f5d-9a11-3f0b6f2f4a21",
    "name": "Contoso",
    "description": "The main project",
    "state": "wellFormed",
    "url": "https://dev.azure.com/contoso/_apis/projects/6f9c1e0a-6c3e-4f5d-9a11-3f0b6f2f4a21",
}

REPOSITORY = {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "api",
    "url": "https://dev.azure.com/contoso/Contoso/_git/api",
    "defaultBranch": "refs/heads/master",
    "size": 4096,
    "project": {"id": PROJECT["id"], "name": "Contoso"},
}


def recorder(status=200, payload=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(status, json=payload if payload is not None else {})

    return handler, seen


class ListProjectsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_projects_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [PROJECT]})

        result = call_tool(
            "azure_devops_list_projects",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(seen[0].url.path, "/contoso/_apis/projects")
        self.assertTrue(result["ok"])

    def test_the_projects_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [PROJECT]})

        result = call_tool(
            "azure_devops_list_projects",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            result["data"]["projects"],
            [
                {
                    "id": PROJECT["id"],
                    "name": "Contoso",
                    "description": "The main project",
                    "state": "wellFormed",
                }
            ],
        )
        self.assertEqual(result["data"]["continuationToken"], "")

    def test_the_continuation_token_of_the_page_is_answered(self):
        handler, _ = recorder(
            payload={"count": 1, "value": [PROJECT], "continuationToken": "next-page"}
        )

        result = call_tool(
            "azure_devops_list_projects",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["continuationToken"], "next-page")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, seen = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_projects",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertEqual(len(seen), 1)


class GetProjectTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_project_route_is_called_with_the_name(self):
        handler, seen = recorder(payload=PROJECT)

        result = call_tool(
            "azure_devops_get_project",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/_apis/projects/Contoso")
        self.assertEqual(result["data"]["project"]["name"], "Contoso")
        self.assertEqual(result["data"]["project"]["state"], "wellFormed")

    def test_the_project_route_accepts_the_id(self):
        handler, seen = recorder(payload=PROJECT)

        call_tool(
            "azure_devops_get_project",
            {"project": PROJECT["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, f"/contoso/_apis/projects/{PROJECT['id']}")

    def test_an_unknown_project_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_project",
            {"project": "Ghost"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)


class ListRepositoriesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_repositories_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [REPOSITORY]})

        result = call_tool(
            "azure_devops_list_repositories",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/git/repositories")
        self.assertTrue(result["ok"])

    def test_the_repositories_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [REPOSITORY]})

        result = call_tool(
            "azure_devops_list_repositories",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            result["data"]["repositories"],
            [
                {
                    "id": REPOSITORY["id"],
                    "name": "api",
                    "url": REPOSITORY["url"],
                    "defaultBranch": "refs/heads/master",
                    "size": 4096,
                }
            ],
        )

    def test_the_configured_default_project_is_used(self):
        bind_context({"organization": "contoso", "default_project": "Fallback"})
        handler, seen = recorder(payload={"count": 0, "value": []})

        call_tool(
            "azure_devops_list_repositories",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Fallback/_apis/git/repositories")

    def test_a_call_without_project_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_repositories",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class GetRepositoryTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_repository_route_is_called_and_normalized(self):
        handler, seen = recorder(payload=REPOSITORY)

        result = call_tool(
            "azure_devops_get_repository",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/git/repositories/api")
        self.assertEqual(
            result["data"]["repository"],
            {
                "id": REPOSITORY["id"],
                "name": "api",
                "url": REPOSITORY["url"],
                "defaultBranch": "refs/heads/master",
                "size": 4096,
            },
        )

    def test_an_unknown_repository_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_repository",
            {"project": "Contoso", "repository": "ghost"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


if __name__ == "__main__":
    unittest.main()
