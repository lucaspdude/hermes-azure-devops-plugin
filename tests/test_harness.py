"""The offline harness of the suite: fake transport, fake secret, no PAT, no network.

The suite never depends on ``AZURE_DEVOPS_PAT_TOKEN`` and never reaches the
network: the secret is injected at the resolution point and the transport is
an ``httpx.MockTransport``.
"""

import os
import socket
import unittest

import httpx

from support import FAKE_PAT, fake_client, fake_secret_resolver, plugin_module

auth = plugin_module("auth")


class FakeSecretTest(unittest.TestCase):
    def test_the_fake_secret_answers_the_pat_name_only(self):
        resolver = fake_secret_resolver()

        self.assertEqual(resolver("AZURE_DEVOPS_PAT_TOKEN"), FAKE_PAT)
        self.assertIsNone(resolver("SOME_OTHER_SECRET"))

    def test_the_fake_secret_resolves_the_pat(self):
        self.assertEqual(auth.resolve_pat(resolver=fake_secret_resolver()), FAKE_PAT)

    def test_the_environment_is_not_the_source_of_the_pat(self):
        os.environ["AZURE_DEVOPS_PAT_TOKEN"] = "pat-from-the-environment"
        try:
            self.assertEqual(auth.resolve_pat(resolver=fake_secret_resolver()), FAKE_PAT)
        finally:
            os.environ.pop("AZURE_DEVOPS_PAT_TOKEN", None)

    def test_the_check_fn_of_the_tools_accepts_the_fake_secret(self):
        self.assertTrue(auth.check_pat_available(resolver=fake_secret_resolver()))


class OfflineTransportTest(unittest.TestCase):
    def test_the_fake_transport_answers_the_request(self):
        seen = []

        def handler(request):
            seen.append(request.url)
            return httpx.Response(200, json={"value": []})

        adoc = fake_client(handler)
        response = adoc.get("_apis/projects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(seen), 1)

    def test_the_harness_client_carries_the_fake_pat(self):
        seen = {}

        def handler(request):
            seen["authorization"] = request.headers.get("authorization")
            return httpx.Response(200, json={"value": []})

        adoc = fake_client(handler)
        adoc.get("_apis/projects")

        self.assertTrue(seen["authorization"].startswith("Basic "))
        self.assertNotIn(FAKE_PAT, seen["authorization"])

    def test_no_socket_is_opened(self):
        opened = []
        real_socket = socket.socket

        def blocked(*args, **kwargs):
            opened.append(args)
            raise AssertionError("the suite must not open a socket")

        socket.socket = blocked
        try:
            adoc = fake_client(lambda request: httpx.Response(200, json={"value": []}))
            adoc.get("_apis/projects")
        finally:
            socket.socket = real_socket

        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()
