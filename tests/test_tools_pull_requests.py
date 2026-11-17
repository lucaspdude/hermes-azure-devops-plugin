"""tools_pull_requests.py: the routes of the pull requests, their threads and labels.

The traps of the verification live here: the filter of status travels as
``searchCriteria.status`` (the route does not read a plain ``status``), and a
label is a concept of the pull request — the repository has no label route.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

REPOSITORY = {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "api",
    "url": "https://dev.azure.com/contoso/Contoso/_git/api",
    "defaultBranch": "refs/heads/master",
    "size": 4096,
}

OTHER_REPOSITORY = {
    "id": "9c8b7a65-4321-4fed-9cba-0987654321fe",
    "name": "web",
    "url": "https://dev.azure.com/contoso/Contoso/_git/web",
    "defaultBranch": "refs/heads/main",
    "size": 2048,
}

PULL_REQUEST = {
    "pullRequestId": 17,
    "title": "Fix the timeout",
    "description": "The request timed out after 30s",
    "status": "active",
    "isDraft": False,
    "creationDate": "2023-11-17T09:00:00Z",
    "closedDate": None,
    "sourceRefName": "refs/heads/fix/timeout",
    "targetRefName": "refs/heads/master",
    "mergeStatus": "succeeded",
    "url": "https://dev.azure.com/contoso/Contoso/_git/api/pullrequest/17",
    "createdBy": {"id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d", "displayName": "Ada Lovelace"},
    "reviewers": [
        {
            "id": "7c6d5e4f-3a2b-4c1d-9e8f-7a6b5c4d3e2f",
            "displayName": "Grace Hopper",
            "isRequired": True,
            "vote": 10,
        }
    ],
}

THREAD = {
    "id": 3,
    "status": "active",
    "publishedDate": "2023-11-17T10:00:00Z",
    "lastUpdatedDate": "2023-11-17T10:05:00Z",
    "threadContext": None,
    "comments": [
        {
            "id": 5,
            "parentCommentId": 0,
            "author": {"id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d", "displayName": "Ada Lovelace"},
            "content": "The timeout is now 60s.",
            "commentType": "text",
            "publishedDate": "2023-11-17T10:00:00Z",
            "lastUpdatedDate": "2023-11-17T10:00:00Z",
        }
    ],
}

LABEL = {"id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "name": "bug", "active": True}


def recorder(status=200, payload=None, headers=None):
    """The fake transport of a test: it records the request and answers."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            status,
            json=payload if payload is not None else {},
            headers=headers,
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


class ListPullRequestsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_pull_requests_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [PULL_REQUEST]})

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/git/repositories/api/pullrequests",
        )
        self.assertTrue(result["ok"])

    def test_the_status_filter_travels_in_the_request(self):
        handler, seen = recorder(payload={"count": 1, "value": [PULL_REQUEST]})

        call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso", "repository": "api", "status": "active"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["searchCriteria.status"], "active")

    def test_every_status_the_api_accepts_is_accepted(self):
        for status in ("active", "abandoned", "completed", "all"):
            handler, seen = recorder(payload={"count": 0, "value": []})

            result = call_tool(
                "azure_devops_list_pull_requests",
                {"project": "Contoso", "repository": "api", "status": status},
                transport=mock_transport(handler),
                secret_resolver=fake_secret_resolver(),
            )

            self.assertTrue(result["ok"], status)
            self.assertEqual(seen[0].url.params["searchCriteria.status"], status)

    def test_an_unknown_status_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso", "repository": "api", "status": "merged"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_the_pull_requests_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [PULL_REQUEST]})

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        pull_request = result["data"]["pullRequests"][0]
        self.assertEqual(pull_request["pullRequestId"], 17)
        self.assertEqual(pull_request["title"], "Fix the timeout")
        self.assertEqual(pull_request["status"], "active")
        self.assertEqual(pull_request["sourceRefName"], "refs/heads/fix/timeout")
        self.assertEqual(pull_request["targetRefName"], "refs/heads/master")
        self.assertEqual(pull_request["createdBy"]["displayName"], "Ada Lovelace")
        self.assertEqual(pull_request["reviewers"][0]["displayName"], "Grace Hopper")

    def test_the_only_repository_of_the_project_is_resolved(self):
        handler, seen = router(
            {
                "/contoso/Contoso/_apis/git/repositories": {
                    "count": 1,
                    "value": [REPOSITORY],
                },
                "/contoso/Contoso/_apis/git/repositories/"
                "3fa85f64-5717-4562-b3fc-2c963f66afa6/pullrequests": {
                    "count": 1,
                    "value": [PULL_REQUEST],
                },
            }
        )

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/git/repositories")
        self.assertTrue(result["ok"])

    def test_a_project_with_many_repositories_asks_for_one(self):
        handler, seen = recorder(
            payload={"count": 2, "value": [REPOSITORY, OTHER_REPOSITORY]}
        )

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertIn("api", result["error"]["message"])
        self.assertEqual(len(seen), 1)

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, seen = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_pull_requests",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertEqual(len(seen), 1)


class GetPullRequestTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_pull_request_route_is_called_with_the_id(self):
        handler, seen = recorder(payload=PULL_REQUEST)

        result = call_tool(
            "azure_devops_get_pull_request",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/git/repositories/api/pullRequests/17",
        )
        self.assertEqual(result["data"]["pullRequest"]["pullRequestId"], 17)
        self.assertEqual(result["data"]["pullRequest"]["mergeStatus"], "succeeded")

    def test_an_unknown_pull_request_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_pull_request",
            {"project": "Contoso", "repository": "api", "pullRequestId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)

    def test_a_call_without_pull_request_answers_invalid_input(self):
        handler, seen = recorder(payload=PULL_REQUEST)

        result = call_tool(
            "azure_devops_get_pull_request",
            {"project": "Contoso", "repository": "api"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class ListPullRequestCommentsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_threads_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [THREAD]})

        result = call_tool(
            "azure_devops_list_pull_request_comments",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/git/repositories/api/pullRequests/17/threads",
        )
        self.assertTrue(result["ok"])

    def test_the_comments_carry_the_author_the_text_the_status_and_the_date(self):
        handler, _ = recorder(payload={"count": 1, "value": [THREAD]})

        result = call_tool(
            "azure_devops_list_pull_request_comments",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        thread = result["data"]["comments"][0]
        self.assertEqual(thread["id"], 3)
        self.assertEqual(thread["status"], "active")
        self.assertEqual(thread["publishedDate"], "2023-11-17T10:00:00Z")
        comment = thread["comments"][0]
        self.assertEqual(comment["content"], "The timeout is now 60s.")
        self.assertEqual(comment["author"]["displayName"], "Ada Lovelace")
        self.assertEqual(comment["commentType"], "text")
        self.assertEqual(result["data"]["count"], 1)

    def test_an_unknown_pull_request_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_list_pull_request_comments",
            {"project": "Contoso", "repository": "api", "pullRequestId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


class ListPullRequestLabelsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_labels_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [LABEL]})

        result = call_tool(
            "azure_devops_list_pull_request_labels",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/git/repositories/api/pullRequests/17/labels",
        )
        self.assertTrue(result["ok"])

    def test_the_labels_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [LABEL]})

        result = call_tool(
            "azure_devops_list_pull_request_labels",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["labels"], [LABEL])
        self.assertEqual(result["data"]["count"], 1)

    def test_the_labels_are_read_from_the_pull_request_not_the_repository(self):
        handler, seen = recorder(payload={"count": 1, "value": [LABEL]})

        call_tool(
            "azure_devops_list_pull_request_labels",
            {"project": "Contoso", "repository": "api", "pullRequestId": 17},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertNotIn("/repositories/api/labels", seen[0].url.path)

    def test_an_unknown_pull_request_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_list_pull_request_labels",
            {"project": "Contoso", "repository": "api", "pullRequestId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


if __name__ == "__main__":
    unittest.main()
