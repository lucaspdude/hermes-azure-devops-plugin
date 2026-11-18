"""The desktop panel backend: aggregate payload, cache and error shape.

Runs with the Hermes environment interpreter (it carries fastapi); on a host
without fastapi the module is skipped, the way the plugin itself degrades.
"""

import sys
import time
import unittest

import httpx
from pathlib import Path

from support import fake_client, plugin_module

try:
    import fastapi  # noqa: F401
except ModuleNotFoundError:
    fastapi = None

PLUGIN_ROOT = Path(__file__).parent.parent


def _load_backend():
    """Load dashboard/plugin_api.py the way the gateway does (standalone exec).

    The plugin modules are registered first under a fixed package name, so the
    shim resolves them without the gateway.
    """
    # Reuse the package the suite support module loads, so AdoError classes are identical
    # across the backend and the tools (a caught error must be the same class).
    from support import plugin_module

    plugin_module("registry")
    package = "hermes_plugins.azure_devops"
    source = (PLUGIN_ROOT / "dashboard" / "plugin_api.py").read_text(encoding="utf-8")
    namespace: dict = {
        "__name__": "dashboard_plugin_api_test",
        "__file__": str(PLUGIN_ROOT / "dashboard" / "plugin_api.py"),
    }
    sys.path.insert(0, str(PLUGIN_ROOT))
    exec(compile(source, str(PLUGIN_ROOT / "dashboard" / "plugin_api.py"), "exec"), namespace)
    return namespace


@unittest.skipUnless(fastapi, "fastapi is not available")
class OverviewPayloadTest(unittest.TestCase):
    def test_the_overview_carries_the_user_activity_and_degrades_without_identity(self):
        import httpx

        backend = _load_backend()

        def handler(request):
            path = request.url.path
            if path.endswith("/_apis/projects"):
                return httpx.Response(
                    200,
                    json={"value": [{"id": "proj-1", "name": "Projeto Um"}]},
                    request=request,
                )
            if path.endswith("/connectionData"):
                if request.headers.get("authorization", "").endswith("OmZha2UtcGF0LWZvci10ZXN0cy1vbmx5"):
                    return httpx.Response(
                        200,
                        json={"authenticatedUser": {"id": "user-1", "displayName": "Ada"}},
                        request=request,
                    )
                return httpx.Response(401, json={"message": "no identity"}, request=request)
            if path.endswith("/git/pullrequests"):
                return httpx.Response(
                    200,
                    json={
                        "value": [
                            {
                                "pullRequestId": 7,
                                "title": "t",
                                "isDraft": False,
                                "createdBy": {"id": "user-1"},
                                "repository": {"name": "r"},
                            },
                            {"pullRequestId": 8, "title": "other", "createdBy": {"id": "u2"}, "reviewers": []},
                        ]
                    },
                    request=request,
                )
            if path.endswith("/wit/wiql"):
                return httpx.Response(
                    200,
                    json={"workItems": [{"id": 42}, {"id": 43}]},
                    request=request,
                )
            if path.endswith("/wit/workitems"):
                return httpx.Response(
                    200,
                    json={
                        "value": [
                            {"id": 42, "fields": {"System.Title": "a", "System.State": "To Do", "System.WorkItemType": "Task"}},
                            {"id": 43, "fields": {"System.Title": "b", "System.State": "Done", "System.WorkItemType": "Bug"}},
                        ]
                    },
                    request=request,
                )
            if path.endswith("/build/builds"):
                return httpx.Response(
                    200,
                    json={
                        "value": [
                            {"id": 1, "buildNumber": "b1", "status": "completed", "result": "succeeded", "definition": {"name": "ci"}, "requestedFor": {"id": "user-1"}},
                            {"id": 2, "buildNumber": "b2", "requestedFor": {"id": "u2"}},
                        ]
                    },
                    request=request,
                )
            return httpx.Response(404, json={}, request=request)

        from support import fake_client

        payload = backend["_overview_payload"](fake_client(handler))
        self.assertEqual([p["id"] for p in payload["pullRequests"]], [7])
        self.assertEqual([w["id"] for w in payload["workItems"]], [42, 43])
        self.assertEqual([b["id"] for b in payload["builds"]], [1])
        self.assertNotIn("identityWarning", payload)

        # A PAT sem o escopo de identidade degrada com aviso, sem quebrar as secoes.
        def no_identity_handler(request):
            if "connectionData" in request.url.path:
                return httpx.Response(403, json={"message": "no identity scope"}, request=request)
            return httpx.Response(200, json={"value": []}, request=request)

        degraded = backend["_overview_payload"](fake_client(no_identity_handler))
        self.assertIn("identityWarning", degraded)
        self.assertEqual(degraded["pullRequests"], [])


@unittest.skipUnless(fastapi, "fastapi is not available")
class CacheTest(unittest.TestCase):
    def test_two_reads_inside_the_window_hit_the_api_once(self):
        backend = _load_backend()
        calls = {"n": 0}

        def build():
            calls["n"] += 1
            return {"n": calls["n"]}

        self.assertEqual(backend["_served"](("k",), build), {"n": 1})
        self.assertEqual(backend["_served"](("k",), build), {"n": 1})
        self.assertEqual(calls["n"], 1)
        backend["cache_invalidate"]()
        self.assertEqual(backend["_served"](("k",), build), {"n": 2})


@unittest.skipUnless(fastapi, "fastapi is not available")
class ReadOnlyTest(unittest.TestCase):
    def test_the_router_only_declares_get_routes(self):
        backend = _load_backend()
        router = backend["router"]
        methods = []
        for route in router.routes:
            methods.extend(sorted(getattr(route, "methods", [])))
        self.assertTrue(methods)
        # Rotas de conteúdo (overview/detalhes/releases) e a rota de configuração
        # ignored-projects são as únicas; nenhum acesso ao Azure DevOps de escrita.
        self.assertFalse({"PUT", "PATCH", "DELETE"} & set(methods))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(fastapi, "fastapi is not available")
class DetailRoutesTest(unittest.TestCase):
    def test_the_pull_request_detail_route_answers_the_same_payload_as_the_tool(self):
        backend = _load_backend()

        def handler(request):
            return httpx.Response(
                200,
                json={"pullRequestId": 7, "title": "t", "status": "active"},
                request=httpx.Request("GET", "https://x"),
            )

        backend["_panel_client"] = lambda: fake_client(handler)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(backend["router"])
        client = TestClient(app)
        response = client.get("/pull-requests/7")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["pullRequest"]["pullRequestId"], 7)

    def test_the_build_detail_route_answers_the_same_payload_as_the_tool(self):
        backend = _load_backend()

        def handler(request):
            return httpx.Response(
                200,
                json={"id": 12, "buildNumber": "b-1", "status": "completed"},
                request=httpx.Request("GET", "https://x"),
            )

        backend["_panel_client"] = lambda: fake_client(handler)
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(backend["router"])
        client = TestClient(app)
        response = client.get("/builds/12")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["build"]["buildNumber"], "b-1")

