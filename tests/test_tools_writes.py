"""The write tools, against the fake transport.

Every write carries the identifier of the object it touched, changes state
with the method and payload the route expects, and answers the error envelope
(message of the API preserved) when Azure DevOps refuses.
"""

import json
import unittest

from support import bind_context, call_tool, fake_client, plugin_module

registry = plugin_module("registry")
errors = plugin_module("errors")


def _client(handler):
    return fake_client(handler)


def _ok(payload):
    import httpx

    return httpx.Response(200, json=payload, request=httpx.Request("POST", "https://x"))


class CreatePullRequestTest(unittest.TestCase):
    def test_the_payload_carries_the_refs_title_and_options(self):
        seen = {}

        def handler(request):
            seen["method"] = request.method
            seen["path"] = request.url.path
            seen["body"] = json.loads(request.content)
            return _ok({"pullRequestId": 42, "title": "t", "_links": {"web": {"href": "https://dev/42"}}})

        result = call_tool(
            "azure_devops_create_pull_request",
            {
                "project": "Contoso",
                "repository": "repo1",
                "sourceRefName": "feature/x",
                "targetRefName": "main",
                "title": "t",
                "isDraft": True,
                "reviewerIds": ["abc"],
            },
            client=_client(handler),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(seen["method"], "POST")
        self.assertTrue(seen["path"].endswith("/pullrequests"))
        self.assertEqual(seen["body"]["sourceRefName"], "refs/heads/feature/x")
        self.assertEqual(seen["body"]["targetRefName"], "refs/heads/main")
        self.assertTrue(seen["body"]["isDraft"])
        self.assertEqual(seen["body"]["reviewers"], [{"id": "abc"}])
        self.assertEqual(result["data"]["pullRequestId"], 42)
        self.assertEqual(result["data"]["url"], "https://dev/42")

    def test_a_call_without_required_fields_answers_invalid_input(self):
        def handler(request):  # pragma: no cover - never called
            return _ok({})

        result = call_tool(
            "azure_devops_create_pull_request",
            {"project": "Contoso", "repository": "repo1"},
            client=_client(handler),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")


class CommentTest(unittest.TestCase):
    def test_a_new_thread_posts_to_the_threads_route(self):
        seen = {}

        def handler(request):
            seen["method"] = request.method
            seen["path"] = request.url.path
            seen["body"] = json.loads(request.content)
            return _ok({"id": 7, "comments": [{"id": 9}], "status": "active"})

        result = call_tool(
            "azure_devops_add_pull_request_comment",
            {"project": "C", "repository": "r", "pullRequestId": 5, "comment": "hi"},
            client=_client(handler),
        )
        self.assertEqual(seen["path"].endswith("/pullRequests/5/threads"), True)
        self.assertEqual(result["data"]["threadId"], 7)
        self.assertEqual(result["data"]["commentId"], 9)

    def test_a_reply_posts_into_the_thread(self):
        seen = {}

        def handler(request):
            seen["path"] = request.url.path
            return _ok({"id": 7, "comments": [{"id": 10}]})

        call_tool(
            "azure_devops_add_pull_request_comment",
            {"project": "C", "repository": "r", "pullRequestId": 5, "comment": "hi", "threadId": 3},
            client=_client(handler),
        )
        self.assertTrue(seen["path"].endswith("/threads/3/comments"))


class LabelTest(unittest.TestCase):
    def test_adding_a_label_posts_and_answers_the_label(self):
        def handler(request):
            return _ok({"id": "lbl-1", "name": "review"})

        result = call_tool(
            "azure_devops_add_pull_request_label",
            {"project": "C", "repository": "r", "pullRequestId": 5, "label": "review"},
            client=_client(handler),
        )
        self.assertEqual(result["data"]["labelId"], "lbl-1")

    def test_removing_by_name_resolves_the_id_first(self):
        seen = []

        def handler(request):
            seen.append(request.url.path)
            if request.method == "GET":
                return _ok({"value": [{"id": "lbl-1", "name": "review"}]})
            return _ok({})

        result = call_tool(
            "azure_devops_remove_pull_request_label",
            {"project": "C", "repository": "r", "pullRequestId": 5, "label": "review"},
            client=_client(handler),
        )
        self.assertTrue(any(p.endswith("/labels/lbl-1") for p in seen))
        self.assertTrue(result["data"]["removed"])


class VotesTest(unittest.TestCase):
    def test_the_vote_resolves_the_authenticated_user_per_call(self):
        seen = []

        def handler(request):
            seen.append((request.method, request.url.path))
            if "connectionData" in request.url.path:
                return _ok({"authenticatedUser": {"id": "user-1"}})
            return _ok({"id": "user-1", "vote": 10, "displayName": "Ada"})

        result = call_tool(
            "azure_devops_approve_pull_request",
            {"project": "C", "repository": "r", "pullRequestId": 5},
            client=_client(handler),
        )
        route = [p for m, p in seen if "reviewers" in p]
        self.assertEqual(len(route), 1)
        self.assertTrue(route[0].endswith("/reviewers/user-1"))
        self.assertEqual(result["data"]["vote"], 10)

    def test_reject_votes_five_and_reset_zero(self):
        votes = []

        def handler(request):
            if "connectionData" in request.url.path:
                return _ok({"authenticatedUser": {"id": "user-1"}})
            body = json.loads(request.content) if request.content else {}
            votes.append(body.get("vote"))
            return _ok({"id": "user-1", "vote": body.get("vote")})

        for name, expected in (
            ("azure_devops_reject_pull_request", 5),
            ("azure_devops_reset_pull_request_vote", 0),
        ):
            with self.subTest(name):
                votes.clear()
                result = call_tool(
                    name,
                    {"project": "C", "repository": "r", "pullRequestId": 5},
                    client=_client(handler),
                )
                self.assertEqual(votes[0], expected)
                self.assertEqual(result["data"]["vote"], expected)

    def test_a_refused_vote_keeps_the_message_of_the_api(self):
        import httpx

        def handler(request):
            if "connectionData" in request.url.path:
                return _ok({"authenticatedUser": {"id": "user-1"}})
            return httpx.Response(
                403,
                json={"message": "The identity cannot vote."},
                request=httpx.Request("PUT", "https://x"),
            )

        result = call_tool(
            "azure_devops_approve_pull_request",
            {"project": "C", "repository": "r", "pullRequestId": 5},
            client=_client(handler),
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertIn("The identity cannot vote.", result["error"]["message"])


class StatusTest(unittest.TestCase):
    def test_abandon_sends_the_abandoned_status(self):
        seen = {}

        def handler(request):
            seen["method"] = request.method
            seen["body"] = json.loads(request.content)
            return _ok({"pullRequestId": 5, "status": "abandoned"})

        result = call_tool(
            "azure_devops_abandon_pull_request",
            {"project": "C", "repository": "r", "pullRequestId": 5},
            client=_client(handler),
        )
        self.assertEqual(seen["method"], "PATCH")
        self.assertEqual(seen["body"], {"status": "abandoned"})
        self.assertEqual(result["data"]["status"], "abandoned")

    def test_complete_squash_and_delete_travel_in_completion_options(self):
        seen = {}

        def handler(request):
            seen["body"] = json.loads(request.content)
            return _ok({"pullRequestId": 5, "status": "completed", "lastMergeCommit": {"commitId": "c1"}})

        result = call_tool(
            "azure_devops_complete_pull_request",
            {"project": "C", "repository": "r", "pullRequestId": 5, "squashMerge": True, "deleteSourceBranch": True},
            client=_client(handler),
        )
        self.assertEqual(
            seen["body"],
            {"status": "completed", "completionOptions": {"squashMerge": True, "deleteSourceBranch": True}},
        )
        self.assertEqual(result["data"]["mergeCommitId"], "c1")


class WorkItemTest(unittest.TestCase):
    def test_the_patch_document_travels_with_the_patch_content_type(self):
        seen = {}

        def handler(request):
            seen["method"] = request.method
            seen["content_type"] = request.headers.get("content-type", "")
            seen["body"] = json.loads(request.content)
            return _ok({"id": 42, "rev": 8, "fields": {"System.Title": "t", "System.State": "Done"}})

        result = call_tool(
            "azure_devops_update_work_item",
            {"workItemId": 42, "operations": [{"op": "replace", "path": "/fields/System.State", "value": "Done"}]},
            client=_client(handler),
        )
        self.assertEqual(seen["method"], "PATCH")
        self.assertIn("json-patch", seen["content_type"])
        self.assertEqual(seen["body"], [{"op": "replace", "path": "/fields/System.State", "value": "Done"}])
        self.assertEqual(result["data"]["state"], "Done")

    def test_an_empty_patch_is_invalid_input_without_a_call(self):
        def handler(request):  # pragma: no cover
            return _ok({})

        result = call_tool(
            "azure_devops_update_work_item",
            {"workItemId": 42, "operations": []},
            client=_client(handler),
        )
        self.assertEqual(result["error"]["code"], "invalid_input")


class WikiWriteTest(unittest.TestCase):
    def test_the_page_is_written_in_the_owner_project_of_the_wiki(self):
        seen = {}

        def handler(request):
            if request.url.path.endswith("/_apis/wiki/wikis"):
                return _ok({"value": [{"id": "w-1", "name": "docs", "remoteUrl": "https://dev.azure.com/contoso/8a3f/_apis/wiki/wikis/w-1"}]})
            seen["method"] = request.method
            seen["path"] = request.url.path
            seen["body"] = request.content.decode()
            return _ok({"path": "/Home", "version": 2})

        result = call_tool(
            "azure_devops_create_wiki_page",
            {"project": "other", "wiki": "docs", "path": "/Home", "content": "# hello"},
            client=_client(handler),
        )
        self.assertEqual(seen["method"], "PUT")
        self.assertIn("/8a3f/", seen["path"])
        self.assertEqual(result["data"]["version"], 2)

    def test_updating_requires_the_version(self):
        def handler(request):
            if request.url.path.endswith("/_apis/wiki/wikis"):
                return _ok({"value": [{"id": "w-1", "remoteUrl": "https://dev.azure.com/contoso/8a3f/_apis/wiki/wikis/w-1"}]})
            return _ok({})

        result = call_tool(
            "azure_devops_update_wiki_page",
            {"project": "p", "wiki": "w-1", "path": "/Home", "content": "x"},
            client=_client(handler),
        )
        self.assertEqual(result["error"]["code"], "invalid_input")


class QueueBuildTest(unittest.TestCase):
    def test_a_definition_name_is_resolved_before_the_queue(self):
        seen = []

        def handler(request):
            seen.append((request.method, request.url.path, request.url.params.get("name")))
            if "definitions" in request.url.path:
                return _ok({"value": [{"id": 12}]})
            return _ok({"id": 500, "buildNumber": "b-1", "status": "notStarted"})

        result = call_tool(
            "azure_devops_queue_build",
            {"project": "C", "definition": "ci-main", "branch": "main"},
            client=_client(handler),
        )
        definitions = [s for s in seen if "definitions" in s[1]]
        queues = [s for s in seen if s[1].endswith("/builds") and s[0] == "POST"]
        self.assertEqual(len(definitions), 1)
        self.assertEqual(len(queues), 1)
        self.assertEqual(result["data"]["buildId"], 500)

    def test_an_unknown_definition_answers_not_found(self):
        def handler(request):
            return _ok({"value": []})

        result = call_tool(
            "azure_devops_queue_build",
            {"project": "C", "definition": "nope"},
            client=_client(handler),
        )
        self.assertEqual(result["error"]["code"], "not_found")


if __name__ == "__main__":
    unittest.main()