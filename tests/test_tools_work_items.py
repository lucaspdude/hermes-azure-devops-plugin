"""tools_work_items.py: the WIQL query, the work item by id and the work items by ids.

The traps of the verification live here: the WIQL route only answers a POST
with a JSON body (no body answers 411, a GET answers 405), the page size
travels as ``$top`` in the query string, and the fields of a work item are
reduced by default.
"""

import json
import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

WORK_ITEM = {
    "id": 42,
    "rev": 3,
    "fields": {
        "System.Id": 42,
        "System.WorkItemType": "Bug",
        "System.Title": "The timeout is 30s",
        "System.State": "Active",
    },
    "url": "https://dev.azure.com/contoso/_apis/wit/workItems/42",
}

OTHER_WORK_ITEM = {
    "id": 43,
    "rev": 1,
    "fields": {
        "System.Id": 43,
        "System.WorkItemType": "Task",
        "System.Title": "Write the docs",
        "System.State": "To Do",
    },
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
    """The fake transport of a test that makes more than one call."""
    seen = []

    def handler(request):
        seen.append(request)
        payload = routes.get(request.url.path)
        if payload is None:
            return httpx.Response(default_status, json={"message": "not found"})
        return httpx.Response(200, json=payload)

    return handler, seen


class QueryWiqlTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_query_travels_as_a_post_with_a_json_body(self):
        handler, seen = recorder(payload={"workItems": [{"id": 42, "url": "u"}]})

        result = call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].method, "POST")
        self.assertEqual(
            json.loads(seen[0].content.decode("utf-8")),
            {"query": "SELECT [System.Id] FROM WorkItems"},
        )
        self.assertTrue(result["ok"])

    def test_the_wiql_route_is_called_in_the_project(self):
        handler, seen = recorder(payload={"workItems": []})

        call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems", "project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/wit/wiql")

    def test_a_query_without_a_project_runs_in_the_organization(self):
        handler, seen = recorder(payload={"workItems": []})

        call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/_apis/wit/wiql")

    def test_the_page_size_travels_with_the_dollar_sign(self):
        handler, seen = recorder(payload={"workItems": []})

        call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems", "top": 25},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        raw = seen[0].url.raw_path.decode("utf-8")
        self.assertIn("%24top=25", raw)
        self.assertNotIn("top=25", raw.replace("%24top=25", ""))

    def test_the_ids_of_the_answer_are_normalized(self):
        handler, _ = recorder(
            payload={
                "queryType": "flat",
                "columns": [{"name": "Id", "referenceName": "System.Id"}],
                "workItems": [
                    {"id": 42, "url": "https://dev.azure.com/contoso/_apis/wit/workItems/42"},
                    {"id": 43, "url": "https://dev.azure.com/contoso/_apis/wit/workItems/43"},
                ],
            }
        )

        result = call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems", "project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        data = result["data"]
        self.assertEqual(data["ids"], [42, 43])
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["workItems"][0]["id"], 42)
        self.assertEqual(data["columns"][0]["referenceName"], "System.Id")

    def test_a_call_without_a_query_answers_invalid_input(self):
        handler, seen = recorder(payload={"workItems": []})

        result = call_tool(
            "azure_devops_query_wiql",
            {"project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_query_wiql",
            {"query": "SELECT [System.Id] FROM WorkItems"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class GetWorkItemTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_work_item_route_is_called_with_the_id(self):
        handler, seen = recorder(payload=WORK_ITEM)

        result = call_tool(
            "azure_devops_get_work_item",
            {"workItemId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/_apis/wit/workitems/42")
        self.assertTrue(result["ok"])

    def test_the_default_fields_are_the_reduced_set(self):
        handler, seen = recorder(payload=WORK_ITEM)

        call_tool(
            "azure_devops_get_work_item",
            {"workItemId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[0].url.params["fields"],
            "System.Id,System.WorkItemType,System.Title,System.State",
        )

    def test_the_fields_the_model_asks_for_travel_in_the_request(self):
        handler, seen = recorder(payload=WORK_ITEM)

        call_tool(
            "azure_devops_get_work_item",
            {"workItemId": 42, "fields": "System.Title,System.State"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.params["fields"], "System.Title,System.State")

    def test_the_work_item_is_normalized(self):
        handler, _ = recorder(payload=WORK_ITEM)

        result = call_tool(
            "azure_devops_get_work_item",
            {"workItemId": 42},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        work_item = result["data"]["workItem"]
        self.assertEqual(work_item["id"], 42)
        self.assertEqual(work_item["type"], "Bug")
        self.assertEqual(work_item["title"], "The timeout is 30s")
        self.assertEqual(work_item["state"], "Active")

    def test_an_unknown_work_item_answers_not_found(self):
        handler, _ = recorder(status=404, payload={"message": "not found"})

        result = call_tool(
            "azure_devops_get_work_item",
            {"workItemId": 999},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)

    def test_a_call_without_a_work_item_answers_invalid_input(self):
        handler, seen = recorder(payload=WORK_ITEM)

        result = call_tool(
            "azure_devops_get_work_item",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])


class ListWorkItemsTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_ids_travel_in_the_request(self):
        handler, seen = recorder(payload={"count": 2, "value": [WORK_ITEM, OTHER_WORK_ITEM]})

        result = call_tool(
            "azure_devops_list_work_items",
            {"ids": [42, 43]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/_apis/wit/workitems")
        self.assertEqual(seen[0].url.params["ids"], "42,43")
        self.assertEqual(result["data"]["count"], 2)

    def test_the_type_is_resolved_with_a_wiql_query(self):
        handler, seen = router(
            {
                "/contoso/Contoso/_apis/wit/wiql": {"workItems": [{"id": 42}, {"id": 43}]},
                "/contoso/_apis/wit/workitems": {
                    "count": 2,
                    "value": [WORK_ITEM, OTHER_WORK_ITEM],
                },
            }
        )

        result = call_tool(
            "azure_devops_list_work_items",
            {"type": "Bug", "project": "Contoso"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0].method, "POST")
        self.assertEqual(seen[0].url.path, "/contoso/Contoso/_apis/wit/wiql")
        body = json.loads(seen[0].content.decode("utf-8"))
        self.assertIn("[System.WorkItemType] = 'Bug'", body["query"])
        self.assertEqual(seen[1].url.params["ids"], "42,43")
        self.assertTrue(result["ok"])

    def test_the_work_items_of_another_type_are_left_out(self):
        handler, _ = recorder(payload={"count": 2, "value": [WORK_ITEM, OTHER_WORK_ITEM]})

        result = call_tool(
            "azure_devops_list_work_items",
            {"ids": [42, 43], "type": "Bug"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["workItems"][0]["id"], 42)

    def test_the_work_items_are_normalized(self):
        handler, _ = recorder(payload={"count": 1, "value": [WORK_ITEM]})

        result = call_tool(
            "azure_devops_list_work_items",
            {"ids": [42]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        work_item = result["data"]["workItems"][0]
        self.assertEqual(work_item["id"], 42)
        self.assertEqual(work_item["type"], "Bug")
        self.assertEqual(work_item["title"], "The timeout is 30s")
        self.assertEqual(work_item["state"], "Active")

    def test_a_call_without_ids_and_without_type_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_work_items",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_an_id_that_is_not_a_number_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_work_items",
            {"ids": ["abc"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_work_items",
            {"ids": [42]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


if __name__ == "__main__":
    unittest.main()
