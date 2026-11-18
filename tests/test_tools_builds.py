"""tools_builds.py: the routes of the builds, and the traps of the verification.

Every test here walks into a trap the endpoint verification found: the
``statusFilter`` that only answers when it travels in the request, the
definition named by its **name** (the route wants the id), the ``changes``
that answer in two formats, and the token of the next page that comes in the
header ``x-ms-continuationtoken``.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

DEFINITION = {
    "id": "2b3c4d5e-6f70-4812-9a3b-4c5d6e7f8091",
    "name": "ci-main",
    "path": "\\Contoso\\ci-main",
    "type": {"id": "2b3c4d5e-type", "name": "Build"},
    "queueStatus": "enabled",
    "revision": 7,
    "url": "https://dev.azure.com/contoso/Contoso/_apis/build/Definitions/2b3c4d5e",
}

OTHER_DEFINITION = {
    "id": "9c8b7a65-4321-4fed-9cba-0987654321fe",
    "name": "ci-nightly",
    "path": "\\Contoso\\ci-nightly",
    "type": {"id": "2b3c4d5e-type", "name": "Build"},
    "queueStatus": "paused",
    "revision": 3,
    "url": "https://dev.azure.com/contoso/Contoso/_apis/build/Definitions/9c8b7a65",
}

BUILD = {
    "id": 4213,
    "buildNumber": "20231117.3",
    "status": "completed",
    "result": "succeeded",
    "queueTime": "2023-11-17T10:00:00Z",
    "startTime": "2023-11-17T10:00:05Z",
    "finishTime": "2023-11-17T10:04:12Z",
    "sourceBranch": "refs/heads/master",
    "sourceVersion": "1f2e3d4c5b6a7988",
    "definition": {
        "id": DEFINITION["id"],
        "name": "ci-main",
        "path": "\\Contoso\\ci-main",
    },
    "requestedBy": {"id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d", "displayName": "Ada Lovelace"},
}

CHANGE = {
    "changeId": 12,
    "changeType": "fileChange",
    "comment": "Fixed the timeout",
    "sourceLabel": "refs/heads/master",
    "targetLabel": "refs/heads/master",
    "date": "2023-11-17T10:01:00Z",
    "author": {"id": "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d", "displayName": "Ada Lovelace"},
    "item": {"path": "/src/api.py", "changeType": "edit", "isFolder": False},
}

RECORD = {
    "id": "d1e2f3a4-b5c6-4d7e-8f90-1a2b3c4d5e6f",
    "type": "Task",
    "name": "Run tests",
    "state": "Completed",
    "result": "Succeeded",
    "startTime": "2023-11-17T10:00:20Z",
    "finishTime": "2023-11-17T10:03:00Z",
    "errorCount": 0,
    "warningCount": 1,
}


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
    """The fake transport of a test that makes more than one call.

    ``routes`` maps the path of the request to the payload it answers.
    """
    seen = []

    def handler(request):
        seen.append(request)
        payload = routes.get(request.url.path)
        if payload is None:
            return httpx.Response(default_status, json={"message": "not found"})
        return httpx.Response(200, json=payload)

    return handler, seen


class ListBuildDefinitionsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_definitions_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [DEFINITION]})

        result = call_tool(
            "azure_devops_list_build_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "GET")
        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/build/definitions")
        self.assertTrue(result["ok"])

    def test_the_definitions_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [DEFINITION]})

        result = call_tool(
            "azure_devops_list_build_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        definition = result["data"]["definitions"][0]
        self.assertEqual(definition["id"], DEFINITION["id"])
        self.assertEqual(definition["name"], "ci-main")
        self.assertEqual(definition["path"], "\\Contoso\\ci-main")
        self.assertEqual(definition["queueStatus"], "enabled")
        self.assertEqual(definition["type"]["name"], "Build")

    def test_the_name_filters_the_definitions(self):
        handler, seen = recorder(payload={"count": 2, "value": [DEFINITION, OTHER_DEFINITION]})

        result = call_tool(
            "azure_devops_list_build_definitions",
            {"project": "Contoso", "name": "ci-main"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["name"], "ci-main")
        self.assertEqual(
            [item["name"] for item in result["data"]["definitions"]],
            ["ci-main"],
        )

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, seen = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_build_definitions",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertEqual(len(seen), 1)


class ListBuildsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_builds_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [BUILD]})

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/build/builds")
        self.assertTrue(result["ok"])

    def test_the_status_filter_travels_in_the_request(self):
        handler, seen = recorder(payload={"count": 1, "value": [BUILD]})

        call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "status": "completed"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["statusFilter"], "completed")

    def test_every_status_the_api_accepts_is_accepted(self):
        for status in (
            "all",
            "cancelling",
            "completed",
            "inProgress",
            "none",
            "notStarted",
            "postponed",
        ):
            handler, seen = recorder(payload={"count": 0, "value": []})

            result = call_tool(
                "azure_devops_list_builds",
                {"project": "Contoso", "status": status},
                transport=mock_transport(handler),
                secret_resolver=fake_secret_resolver(),
            )

            self.assertTrue(result["ok"], status)
            self.assertEqual(seen[0].url.params["statusFilter"], status)

    def test_an_unknown_status_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "status": "running"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_the_name_of_the_definition_is_resolved_to_its_id(self):
        handler, seen = router(
            {
                "/contoso/Contoso/_apis/build/definitions": {
                    "count": 1,
                    "value": [DEFINITION],
                },
                "/contoso/Contoso/_apis/build/builds": {"count": 1, "value": [BUILD]},
            }
        )

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "definition": "ci-main"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/build/definitions")
        self.assertEqual(seen[0].url.params["name"], "ci-main")
        self.assertEqual(seen[1].url.path, "/contoso/Contoso/_apis/build/builds")
        self.assertEqual(seen[1].url.params["definitions"], DEFINITION["id"])
        self.assertTrue(result["ok"])

    def test_the_id_of_the_definition_is_used_without_another_call(self):
        handler, seen = recorder(payload={"count": 1, "value": [BUILD]})

        call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "definition": DEFINITION["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].url.params["definitions"], DEFINITION["id"])

    def test_an_unknown_definition_name_answers_not_found(self):
        handler, seen = router(
            {
                "/contoso/Contoso/_apis/build/definitions": {"count": 0, "value": []},
                "/contoso/Contoso/_apis/build/builds": {"count": 1, "value": [BUILD]},
            }
        )

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "definition": "ghost-pipeline"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(len(seen), 1)

    def test_the_builds_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [BUILD]})

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "days": 0},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        build = result["data"]["builds"][0]
        self.assertEqual(build["id"], 4213)
        self.assertEqual(build["buildNumber"], "20231117.3")
        self.assertEqual(build["status"], "completed")
        self.assertEqual(build["result"], "succeeded")
        self.assertEqual(build["definition"], {"id": DEFINITION["id"], "name": "ci-main"})
        self.assertEqual(build["requestedBy"]["displayName"], "Ada Lovelace")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, seen = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")
        self.assertEqual(len(seen), 1)


class GetBuildTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_build_route_is_called_with_the_id(self):
        handler, seen = recorder(payload=BUILD)

        result = call_tool(
            "azure_devops_get_build",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/build/builds/4213")
        self.assertEqual(result["data"]["build"]["id"], 4213)
        self.assertEqual(result["data"]["build"]["result"], "succeeded")

    def test_an_unknown_build_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_build",
            {"project": "Contoso", "buildId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)

    def test_a_call_without_build_answers_invalid_input(self):
        handler, seen = recorder(payload=BUILD)

        result = call_tool(
            "azure_devops_get_build",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class GetBuildChangesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_changes_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [CHANGE]})

        result = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/build/builds/4213/changes",
        )
        self.assertTrue(result["ok"])

    def test_the_changes_of_the_envelope_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [CHANGE]})

        result = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        change = result["data"]["changes"][0]
        self.assertEqual(change["id"], 12)
        self.assertEqual(change["changeType"], "fileChange")
        self.assertEqual(change["comment"], "Fixed the timeout")
        self.assertEqual(change["author"]["displayName"], "Ada Lovelace")
        self.assertEqual(change["item"]["path"], "/src/api.py")
        self.assertEqual(result["data"]["count"], 1)

    def test_the_changes_of_a_bare_array_are_normalized(self):
        handler, _ = recorder(payload=[CHANGE])

        result = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        change = result["data"]["changes"][0]
        self.assertEqual(change["id"], 12)
        self.assertEqual(change["comment"], "Fixed the timeout")
        self.assertEqual(change["item"]["path"], "/src/api.py")
        self.assertEqual(result["data"]["count"], 1)

    def test_the_two_formats_answer_the_same_list(self):
        envelope, _ = recorder(payload={"count": 1, "value": [CHANGE]})
        bare, _ = recorder(payload=[CHANGE])

        from_envelope = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(envelope),
            secret_resolver=fake_secret_resolver(),
        )
        from_bare = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(bare),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(from_envelope["data"], from_bare["data"])

    def test_an_unknown_build_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_build_changes",
            {"project": "Contoso", "buildId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


class GetBuildTimelineTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_timeline_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "records": [RECORD]})

        result = call_tool(
            "azure_devops_get_build_timeline",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.path,
            "/contoso/Contoso/_apis/build/builds/4213/timeline",
        )
        self.assertTrue(result["ok"])

    def test_the_timeline_answers_the_records(self):
        handler, _ = recorder(payload={"count": 1, "records": [RECORD]})

        result = call_tool(
            "azure_devops_get_build_timeline",
            {"project": "Contoso", "buildId": 4213},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        record = result["data"]["timeline"][0]
        self.assertEqual(record["id"], RECORD["id"])
        self.assertEqual(record["name"], "Run tests")
        self.assertEqual(record["state"], "Completed")
        self.assertEqual(record["result"], "Succeeded")
        self.assertEqual(record["warningCount"], 1)
        self.assertEqual(result["data"]["count"], 1)

    def test_an_unknown_build_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_build_timeline",
            {"project": "Contoso", "buildId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


class BuildPaginationTest(unittest.TestCase):
    """The paging of the builds: the token comes in the header."""

    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_token_of_the_header_comes_back_in_the_answer(self):
        handler, _ = recorder(
            payload={"count": 1, "value": [BUILD]},
            headers={"x-ms-continuationtoken": "page-2-token"},
        )

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["continuationToken"], "page-2-token")

    def test_the_token_received_is_sent_to_the_next_page(self):
        handler, seen = recorder(
            payload={"count": 1, "value": [BUILD]},
            headers={"x-ms-continuationtoken": "page-2-token"},
        )

        call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "top": 1},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )
        call_tool(
            "azure_devops_list_builds",
            {
                "project": "Contoso",
                "top": 1,
                "continuationToken": "page-2-token",
            },
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].url.params["$top"], "1")
        self.assertNotIn("continuationToken", seen[0].url.params)
        self.assertEqual(seen[1].url.params["$top"], "1")
        self.assertEqual(seen[1].url.params["continuationToken"], "page-2-token")

    def test_the_page_size_travels_with_the_dollar_sign(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "top": 25},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        raw = seen[0].url.raw_path.decode("utf-8")
        self.assertIn("%24top=25", raw)
        self.assertNotIn("top=25", raw.replace("%24top=25", ""))


if __name__ == "__main__":
    unittest.main()


class BuildsDaysFilterTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_old_builds_are_dropped_after_the_fetch(self):
        from datetime import datetime, timedelta, timezone

        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

        def handler(request):
            return httpx.Response(
                200,
                json={
                    "value": [
                        {"id": 1, "buildNumber": "new", "finishTime": "2026-11-15T10:00:00Z"},
                        {"id": 2, "buildNumber": "old", "finishTime": "2026-10-01T10:00:00Z"},
                    ]
                },
                request=httpx.Request("GET", "https://x"),
            )

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "days": 7},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )
        numbers = [b["buildNumber"] for b in result["data"]["builds"]]
        self.assertEqual(numbers, ["new"])

    def test_days_zero_keeps_everything(self):
        def handler(request):
            return httpx.Response(
                200,
                json={"value": [{"id": 1, "finishTime": "2026-01-01T10:00:00Z"}]},
                request=httpx.Request("GET", "https://x"),
            )

        result = call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "days": 0},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )
        self.assertEqual(len(result["data"]["builds"]), 1)

    def test_no_date_parameter_travels_in_the_query(self):
        seen = {}

        def handler(request):
            seen["params"] = dict(request.url.params)
            return httpx.Response(200, json={"value": []}, request=httpx.Request("GET", "https://x"))

        call_tool(
            "azure_devops_list_builds",
            {"project": "Contoso", "days": 7},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )
        self.assertNotIn("minFinishTime", seen["params"])
        self.assertNotIn("maxFinishTime", seen["params"])

