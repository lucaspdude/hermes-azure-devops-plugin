"""pagination.py: one continuation token, whatever shape the API uses."""

import unittest

import httpx

from support import FakeContext, mock_transport, plugin_module

client = plugin_module("client")
config = plugin_module("config")
pagination = plugin_module("pagination")


def make_config(**settings):
    settings.setdefault("organization", "contoso")
    return config.load_config(FakeContext(settings))


class ExtractionTest(unittest.TestCase):
    def test_the_token_of_the_header_is_extracted(self):
        response = httpx.Response(
            200, json={"value": []}, headers={"x-ms-continuationtoken": "HEADER-TOKEN"}
        )
        self.assertEqual(pagination.extract_continuation_token(response), "HEADER-TOKEN")

    def test_the_token_of_the_body_is_extracted(self):
        response = httpx.Response(200, json={"continuationToken": "BODY-TOKEN"})
        self.assertEqual(pagination.extract_continuation_token(response), "BODY-TOKEN")

    def test_the_next_page_field_of_the_body_is_extracted(self):
        response = httpx.Response(200, json={"nextPage": "NEXT-TOKEN"})
        self.assertEqual(pagination.extract_continuation_token(response), "NEXT-TOKEN")

    def test_the_header_wins_over_the_body(self):
        response = httpx.Response(
            200,
            json={"continuationToken": "BODY-TOKEN"},
            headers={"x-ms-continuationtoken": "HEADER-TOKEN"},
        )
        self.assertEqual(pagination.extract_continuation_token(response), "HEADER-TOKEN")

    def test_a_last_page_has_no_token(self):
        response = httpx.Response(200, json={"value": []})
        self.assertEqual(pagination.extract_continuation_token(response), "")

    def test_a_body_that_is_not_json_has_no_token(self):
        response = httpx.Response(200, text="<html>not json</html>")
        self.assertEqual(pagination.extract_continuation_token(response), "")

    def test_the_page_is_normalized_to_a_single_field(self):
        payload = {"value": [1, 2], "nextPage": "NEXT-TOKEN", "continuationToken": "OLD"}
        normalized = pagination.normalize_page(payload, "HEADER-TOKEN")

        self.assertEqual(normalized["continuationToken"], "HEADER-TOKEN")
        self.assertNotIn("nextPage", normalized)
        self.assertEqual(normalized["value"], [1, 2])

    def test_a_last_page_is_normalized_to_an_empty_token(self):
        normalized = pagination.normalize_page({"value": []})
        self.assertEqual(normalized["continuationToken"], "")


class PropagationTest(unittest.TestCase):
    def test_the_token_is_accepted_by_the_next_page(self):
        seen = []

        def handler(request):
            seen.append(request)
            if len(seen) == 1:
                return httpx.Response(
                    200,
                    json={"value": [1]},
                    headers={"x-ms-continuationtoken": "PAGE-2"},
                )
            return httpx.Response(200, json={"value": [2]})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        first = adoc.get("_apis/build/builds")
        token = pagination.extract_continuation_token(first)
        self.assertEqual(token, "PAGE-2")

        second = adoc.get(
            "_apis/build/builds", params=pagination.pagination_params(token=token)
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(dict(seen[1].url.params)["continuationToken"], "PAGE-2")
        self.assertEqual(pagination.extract_continuation_token(second), "")

    def test_the_page_size_is_sent_with_the_dollar_sign(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/build/builds", params=pagination.pagination_params(top=2))

        self.assertIn("%24top=2", str(seen[0].url))
        self.assertEqual(dict(seen[0].url.params)["$top"], "2")


if __name__ == "__main__":
    unittest.main()
