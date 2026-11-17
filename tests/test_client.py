"""client.py: the Azure DevOps request the plugin sends."""

import base64
import unittest

import httpx

from support import FakeContext, mock_transport, plugin_module

client = plugin_module("client")
config = plugin_module("config")
errors = plugin_module("errors")


def make_config(**settings):
    settings.setdefault("organization", "contoso")
    return config.load_config(FakeContext(settings))


class ClientTest(unittest.TestCase):
    def test_the_request_carries_the_basic_authorization(self):
        seen = {}

        def handler(request):
            seen["authorization"] = request.headers.get("authorization")
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/projects")

        expected = base64.b64encode(b":abc").decode("ascii")
        self.assertEqual(seen["authorization"], f"Basic {expected}")

    def test_the_request_accepts_json(self):
        seen = {}

        def handler(request):
            seen["accept"] = request.headers.get("accept")
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/projects")

        self.assertEqual(seen["accept"], "application/json")

    def test_the_request_carries_the_api_version(self):
        seen = {}

        def handler(request):
            seen["query"] = dict(request.url.params)
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/projects")

        self.assertEqual(seen["query"]["api-version"], "7.1")

    def test_the_connection_data_endpoint_uses_its_preview_version(self):
        seen = {}

        def handler(request):
            seen["query"] = dict(request.url.params)
            return httpx.Response(200, json={"authenticatedUser": None})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/connectionData")

        self.assertEqual(seen["query"]["api-version"], "7.0-preview.1")

    def test_the_api_version_table_is_the_source_of_truth(self):
        self.assertEqual(
            client.API_VERSION_BY_ENDPOINT,
            {"/_apis/connectionData": "7.0-preview.1"},
        )
        self.assertEqual(client.api_version_for("_apis/projects"), "7.1")
        self.assertEqual(client.api_version_for("_apis/connectionData"), "7.0-preview.1")
        self.assertEqual(client.api_version_for("_apis/projects", "6.0"), "6.0")

    def test_the_timeout_comes_from_the_setting(self):
        seen = {}

        def handler(request):
            seen["timeout"] = request.extensions.get("timeout")
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(
            make_config(http_timeout_ms=5000), "abc", transport=mock_transport(handler)
        )
        adoc.get("_apis/projects")

        self.assertEqual(seen["timeout"]["connect"], 5.0)
        self.assertEqual(seen["timeout"]["read"], 5.0)

    def test_creating_the_client_does_not_touch_the_network(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        self.assertEqual(calls, [])

        adoc.get("_apis/projects")
        self.assertEqual(len(calls), 1)

    def test_a_failed_status_becomes_an_ado_error(self):
        def handler(request):
            return httpx.Response(403, json={"message": "denied"})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        with self.assertRaises(errors.AdoError) as caught:
            adoc.get("_apis/projects")

        self.assertEqual(caught.exception.code, "forbidden")
        self.assertEqual(caught.exception.status, 403)

    def test_the_request_is_not_retried(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(500, json={"message": "boom"})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        with self.assertRaises(errors.AdoError) as caught:
            adoc.get("_apis/projects")

        self.assertEqual(caught.exception.code, "upstream_error")
        self.assertEqual(len(calls), 1)

    def test_a_timeout_becomes_a_timeout_error(self):
        def handler(request):
            raise httpx.ReadTimeout("too slow", request=request)

        adoc = client.AdoClient(
            make_config(http_timeout_ms=1500), "abc", transport=mock_transport(handler)
        )
        with self.assertRaises(errors.AdoError) as caught:
            adoc.get("_apis/projects")

        self.assertEqual(caught.exception.code, "timeout")
        self.assertIn("1500", str(caught.exception))

    def test_a_body_that_is_not_json_becomes_an_upstream_error(self):
        def handler(request):
            return httpx.Response(200, text="<html>not json</html>")

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        response = adoc.get("_apis/projects")

        with self.assertRaises(errors.AdoError) as caught:
            client.decode_json(response)

        self.assertEqual(caught.exception.code, "upstream_error")

    def test_a_broken_base_url_is_reported_as_not_configured(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(
            make_config(base_url="not-a-url"),
            "abc",
            transport=mock_transport(handler),
        )
        with self.assertRaises(errors.AdoError) as caught:
            adoc.get("_apis/projects")

        self.assertEqual(caught.exception.code, "not_configured")
        self.assertIn("base_url", str(caught.exception))
        self.assertEqual(calls, [])

    def test_a_missing_organization_never_reaches_the_network(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"value": []})

        cfg = config.load_config(FakeContext())
        with self.assertRaises(errors.AdoError) as caught:
            client.AdoClient(cfg, "abc", transport=mock_transport(handler))

        self.assertEqual(caught.exception.code, "not_configured")
        self.assertEqual(calls, [])


class HostRoutingTest(unittest.TestCase):
    def test_release_paths_go_to_the_release_host(self):
        seen = {}

        def handler(request):
            seen["url"] = request.url
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/release/definitions")

        self.assertEqual(seen["url"].host, "vsrm.dev.azure.com")
        self.assertEqual(seen["url"].path, "/contoso/_apis/release/definitions")

    def test_other_paths_go_to_the_base_url(self):
        seen = {}

        def handler(request):
            seen["url"] = request.url
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(make_config(), "abc", transport=mock_transport(handler))
        adoc.get("_apis/build/builds")

        self.assertEqual(seen["url"].host, "dev.azure.com")
        self.assertEqual(seen["url"].path, "/contoso/_apis/build/builds")

    def test_the_configured_base_url_is_used(self):
        seen = {}

        def handler(request):
            seen["url"] = request.url
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(
            make_config(base_url="https://tfs.example.com/"),
            "abc",
            transport=mock_transport(handler),
        )
        adoc.get("_apis/projects")

        self.assertEqual(seen["url"].host, "tfs.example.com")
        self.assertEqual(seen["url"].path, "/contoso/_apis/projects")

    def test_the_release_host_is_fixed(self):
        seen = {}

        def handler(request):
            seen["url"] = request.url
            return httpx.Response(200, json={"value": []})

        adoc = client.AdoClient(
            make_config(base_url="https://tfs.example.com"),
            "abc",
            transport=mock_transport(handler),
        )
        adoc.get("_apis/release/definitions")

        self.assertEqual(seen["url"].host, "vsrm.dev.azure.com")

    def test_the_release_marker_is_recognised(self):
        self.assertTrue(client.is_release_path("_apis/release/definitions"))
        self.assertTrue(client.is_release_path("/_apis/release/"))
        self.assertFalse(client.is_release_path("_apis/build/builds"))
        self.assertFalse(client.is_release_path("_apis/releases"))


if __name__ == "__main__":
    unittest.main()
