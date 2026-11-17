"""tools_wiki.py: the wikis of the organization and the pages of one wiki.

The trap of the verification lives here: the pages of a wiki only answer in
the project that **owns** it (the id of the owner comes from the ``remoteUrl``
of the wiki), and another project answers 404 ``WikiNotFoundException``.
"""

import unittest

import httpx

from support import bind_context, call_tool, fake_secret_resolver, mock_transport

WIKI = {
    "id": "1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9",
    "name": "Docs",
    "path": "/Docs",
    "url": "https://dev.azure.com/contoso/_apis/wiki/wikis/1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9",
    "remoteUrl": (
        "https://dev.azure.com/contoso/8a3f9d20-1111-4222-8333-444455556666"
        "/_apis/wiki/wikis/1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9"
    ),
}

ORGANIZATION_WIKI = {
    "id": "9f8e7d6c-5b4a-4392-8180-7f6e5d4c3b2a",
    "name": "Shared",
    "remoteUrl": "https://dev.azure.com/contoso/_apis/wiki/wikis/9f8e7d6c-5b4a-4392-8180-7f6e5d4c3b2a",
}

OWNER_PROJECT = "8a3f9d20-1111-4222-8333-444455556666"

PAGE = {
    "id": 12,
    "path": "/Home",
    "content": "<p>The home page of the wiki.</p>",
    "lastUpdatedDate": "2026-11-17T06:44:00Z",
    "remoteUrl": "https://dev.azure.com/contoso/Contoso/_apis/wiki/wikis/x/pages/Home",
}

PAGE_LIST = [
    {"id": 12, "path": "/Home", "remoteUrl": "u", "lastUpdatedDate": "2026-11-17T06:44:00Z"},
    {"id": 13, "path": "/Guides", "remoteUrl": "u", "lastUpdatedDate": "2026-11-16T10:00:00Z"},
]


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


class ListWikisTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_wikis_route_is_called(self):
        handler, seen = recorder(payload={"count": 1, "value": [WIKI]})

        result = call_tool(
            "azure_devops_list_wikis",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[0].url.path, "/contoso/_apis/wiki/wikis")
        self.assertTrue(result["ok"])

    def test_the_owner_project_comes_from_the_remote_url(self):
        handler, _ = recorder(payload={"count": 1, "value": [WIKI]})

        result = call_tool(
            "azure_devops_list_wikis",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        wiki = result["data"]["wikis"][0]
        self.assertEqual(wiki["id"], WIKI["id"])
        self.assertEqual(wiki["name"], "Docs")
        self.assertEqual(wiki["ownerProject"], OWNER_PROJECT)

    def test_a_wiki_of_the_organization_has_no_owner_project(self):
        handler, _ = recorder(payload={"count": 1, "value": [ORGANIZATION_WIKI]})

        result = call_tool(
            "azure_devops_list_wikis",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(result["data"]["wikis"][0]["ownerProject"], "")

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_wikis",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class ListWikiPagesTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_pages_are_called_in_the_project_that_owns_the_wiki(self):
        handler, seen = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
                f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages": {
                    "count": 2,
                    "value": PAGE_LIST,
                },
            }
        )

        result = call_tool(
            "azure_devops_list_wiki_pages",
            {"wikiId": WIKI["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(
            seen[1].url.path,
            f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages",
        )
        self.assertTrue(result["ok"])

    def test_the_pages_are_normalized(self):
        handler, _ = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
                f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages": {
                    "count": 2,
                    "value": PAGE_LIST,
                },
            }
        )

        result = call_tool(
            "azure_devops_list_wiki_pages",
            {"wikiId": WIKI["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        data = result["data"]
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["pages"][0]["path"], "/Home")
        self.assertEqual(data["pages"][0]["lastUpdatedDate"], "2026-11-17T06:44:00Z")
        self.assertEqual(data["wiki"]["ownerProject"], OWNER_PROJECT)

    def test_an_unknown_wiki_answers_not_found(self):
        handler, _ = router({"/contoso/_apis/wiki/wikis": {"count": 0, "value": []}})

        result = call_tool(
            "azure_devops_list_wiki_pages",
            {"wikiId": "00000000-0000-0000-0000-000000000000"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")

    def test_a_call_without_a_wiki_answers_invalid_input(self):
        handler, seen = recorder(payload={"count": 0, "value": []})

        result = call_tool(
            "azure_devops_list_wiki_pages",
            {},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "invalid_input")
        self.assertEqual(seen, [])

    def test_a_refused_call_answers_the_error_envelope(self):
        handler, _ = recorder(status=403, payload={"message": "denied"})

        result = call_tool(
            "azure_devops_list_wiki_pages",
            {"wikiId": WIKI["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "forbidden")


class GetWikiPageTest(unittest.TestCase):
    def setUp(self):
        bind_context({"organization": "contoso"})

    def test_the_page_is_read_in_the_project_that_owns_the_wiki(self):
        handler, seen = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
                f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages": PAGE,
            }
        )

        result = call_tool(
            "azure_devops_get_wiki_page",
            {"wikiId": WIKI["id"], "path": "/Home"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(
            seen[1].url.path,
            f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages",
        )
        self.assertEqual(seen[1].url.params["path"], "/Home")
        self.assertTrue(result["ok"])

    def test_the_content_and_the_date_of_the_page_are_normalized(self):
        handler, _ = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
                f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages": PAGE,
            }
        )

        result = call_tool(
            "azure_devops_get_wiki_page",
            {"wikiId": WIKI["id"], "path": "/Home"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        page = result["data"]["page"]
        self.assertEqual(page["path"], "/Home")
        self.assertEqual(page["content"], "<p>The home page of the wiki.</p>")
        self.assertEqual(page["lastUpdatedDate"], "2026-11-17T06:44:00Z")
        self.assertEqual(result["data"]["wiki"]["ownerProject"], OWNER_PROJECT)

    def test_the_home_page_is_the_default_of_the_path(self):
        handler, seen = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
                f"/contoso/{OWNER_PROJECT}/_apis/wiki/wikis/{WIKI['id']}/pages": PAGE,
            }
        )

        call_tool(
            "azure_devops_get_wiki_page",
            {"wikiId": WIKI["id"]},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertEqual(seen[1].url.params["path"], "/Home")

    def test_a_page_that_does_not_exist_answers_not_found(self):
        handler, _ = router(
            {
                "/contoso/_apis/wiki/wikis": {"count": 1, "value": [WIKI]},
            }
        )

        result = call_tool(
            "azure_devops_get_wiki_page",
            {"wikiId": WIKI["id"], "path": "/Missing"},
            transport=mock_transport(handler),
            secret_resolver=fake_secret_resolver(),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")
        self.assertEqual(result["error"]["status"], 404)


if __name__ == "__main__":
    unittest.main()
