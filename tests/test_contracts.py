"""contracts.py: the contracts the endpoint verification found, applied.

Every assertion here is a trap the verification walked into: the page size
that is ignored without the dollar sign, the branch that answers 404 when it
carries the full ref, the wiki that only answers in the project that owns it,
and the WIQL route that only answers a POST with a body.
"""

import json
import unittest

import httpx

from support import fake_client, fake_secret_resolver, mock_transport, plugin_module

contracts = plugin_module("contracts")

WIKI = {
    "id": "1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9",
    "name": "Docs",
    "remoteUrl": (
        "https://dev.azure.com/contoso/8a3f9d20-1111-4222-8333-444455556666"
        "/_apis/wiki/wikis/1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9"
    ),
}

ORGANIZATION_WIKI = {
    "id": "9f8e7d6c-5b4a-4392-8180-7f6e5d4c3b2a",
    "name": "Shared",
    "remoteUrl": (
        "https://dev.azure.com/contoso/_apis/wiki/wikis/9f8e7d6c-5b4a-4392-8180-7f6e5d4c3b2a"
    ),
}


class PageSizeTest(unittest.TestCase):
    def test_the_page_size_goes_with_the_dollar_sign(self):
        self.assertEqual(contracts.PAGE_SIZE_PARAM, "$top")
        self.assertEqual(contracts.page_params(top=25), {"$top": "25"})

    def test_the_page_size_reaches_the_wire_encoded(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"value": []})

        adoc = fake_client(handler)
        adoc.get("/_apis/build/builds", params=contracts.page_params(top=25))

        raw = seen[0].url.raw_path.decode("utf-8")
        self.assertIn("%24top=25", raw)
        self.assertNotIn("top=25", raw.replace("%24top=25", ""))

    def test_the_page_size_of_the_contract_is_the_one_of_the_client(self):
        pagination = plugin_module("pagination")

        self.assertEqual(contracts.PAGE_SIZE_PARAM, pagination.PAGE_SIZE_PARAM)


class BranchTest(unittest.TestCase):
    def test_the_branch_is_the_short_name(self):
        self.assertEqual(contracts.short_branch("master"), "master")
        self.assertEqual(contracts.short_branch("refs/heads/master"), "master")
        self.assertEqual(contracts.short_branch("  refs/heads/feature/x  "), "feature/x")

    def test_a_tag_is_not_a_branch(self):
        self.assertEqual(contracts.short_branch("refs/tags/v1.0"), "refs/tags/v1.0")


class WikiOwnerTest(unittest.TestCase):
    def test_the_owner_project_comes_from_the_remote_url(self):
        self.assertEqual(
            contracts.wiki_owner_project(WIKI, "contoso"),
            "8a3f9d20-1111-4222-8333-444455556666",
        )

    def test_a_wiki_of_the_organization_has_no_owner_project(self):
        self.assertEqual(contracts.wiki_owner_project(ORGANIZATION_WIKI, "contoso"), "")

    def test_the_pages_are_called_in_the_project_that_owns_the_wiki(self):
        path = contracts.wiki_pages_path(WIKI, WIKI["id"], "contoso")

        self.assertEqual(
            path,
            "/8a3f9d20-1111-4222-8333-444455556666/_apis/wiki/wikis/"
            "1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9/pages",
        )

    def test_the_request_of_the_pages_goes_to_the_owner_project(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"value": []})

        adoc = fake_client(handler)
        adoc.get(contracts.wiki_pages_path(WIKI, WIKI["id"], "contoso"))

        self.assertEqual(
            seen[0].url.path,
            "/contoso/8a3f9d20-1111-4222-8333-444455556666/_apis/wiki/wikis/"
            "1b2c3d4e-5f60-4718-8293-a4b5c6d7e8f9/pages",
        )

    def test_a_wiki_without_owner_project_is_an_invalid_input(self):
        with self.assertRaises(plugin_module("errors").AdoError) as caught:
            contracts.wiki_pages_path(ORGANIZATION_WIKI, "1", "contoso")

        self.assertEqual(caught.exception.code, "invalid_input")


class WiqlTest(unittest.TestCase):
    def test_the_body_of_the_query_is_the_query(self):
        self.assertEqual(
            contracts.wiql_body("SELECT [System.Id] FROM WorkItems"),
            {"query": "SELECT [System.Id] FROM WorkItems"},
        )

    def test_the_query_travels_as_a_post_with_a_json_body(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"workItems": []})

        adoc = fake_client(handler)
        adoc.post("/_apis/wit/wiql", json=contracts.wiql_body("SELECT [System.Id] FROM WorkItems"))

        self.assertEqual(seen[0].method, "POST")
        self.assertEqual(
            json.loads(seen[0].content.decode("utf-8")),
            {"query": "SELECT [System.Id] FROM WorkItems"},
        )


if __name__ == "__main__":
    unittest.main()


    def test_the_owner_project_comes_from_the_real_wiki_remote_url(self):
        # Formato real verificado contra a API: /{org}/{project}/_wiki/wikis/{id}
        wiki = {
            "remoteUrl": (
                "https://dev.azure.com/contoso/"
                "8a3f9d20-1111-4c2e-8d54-9f1e2d3c4b5a/_wiki/wikis/"
                "be05f447-9b93-4735-a30a-e02b5ef83707"
            )
        }
        self.assertEqual(
            contracts.wiki_owner_project(wiki, "contoso"),
            "8a3f9d20-1111-4c2e-8d54-9f1e2d3c4b5a",
        )
