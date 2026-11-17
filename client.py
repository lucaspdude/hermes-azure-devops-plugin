"""HTTP client for the Azure DevOps REST API.

The ``httpx.Client`` is built inside the tool handler, never at import time
and never in ``register()``: the Hermes doctor blocks the socket while the
plugin registers, and a long-lived client would keep a connection open between
calls.
"""

import base64
from typing import Any, Mapping

import httpx

from .config import DEFAULT_API_VERSION, PluginConfig
from .errors import (
    CODE_NOT_CONFIGURED,
    CODE_TIMEOUT,
    CODE_UPSTREAM_ERROR,
    AdoError,
    error_for_response,
    non_json_response_error,
)

#: Release Management does not exist on the regular host.
RELEASE_HOST = "https://vsrm.dev.azure.com"
RELEASE_PATH_MARKER = "/_apis/release/"

#: Endpoints that do not answer on the configured API version: the table is the
#: single source of truth, no handler hardcodes a version.
API_VERSION_BY_ENDPOINT: dict[str, str] = {
    "/_apis/connectionData": "7.0-preview.1",
}


def api_version_for(path: str, default: str = DEFAULT_API_VERSION) -> str:
    """The API version an endpoint answers on."""
    normalized = _normalize_path(path)
    for endpoint, version in API_VERSION_BY_ENDPOINT.items():
        if endpoint.lower() in normalized.lower():
            return version
    return default


def basic_auth_header(pat: str) -> str:
    """The Azure DevOps authorization header: Basic ``base64(":" + pat)``."""
    encoded = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


def build_timeout(http_timeout_ms: int) -> httpx.Timeout:
    """The timeout of every request, from the ``http_timeout_ms`` setting."""
    return httpx.Timeout(http_timeout_ms / 1000.0)


def is_release_path(path: str) -> bool:
    """True for the paths that live on the Release Management host."""
    return RELEASE_PATH_MARKER in _normalize_path(path) + "/"


def build_url(config: PluginConfig, path: str) -> str:
    """The absolute URL of a path relative to the organization."""
    relative = _normalize_path(path)
    base = RELEASE_HOST if is_release_path(relative) else _validated_base(config)
    return f"{base}/{config.organization}{relative}"


def build_http_client(
    config: PluginConfig, pat: str, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    """An ``httpx.Client`` with the plugin's headers and timeout."""
    return httpx.Client(
        headers={
            "Authorization": basic_auth_header(pat),
            "Accept": "application/json",
        },
        timeout=build_timeout(config.http_timeout_ms),
        transport=transport,
    )


def decode_json(response: httpx.Response) -> Any:
    """The JSON body of a response, or ``upstream_error`` when it is not JSON."""
    try:
        return response.json()
    except ValueError:
        raise non_json_response_error(response.status_code) from None


class AdoClient:
    """Talks to one Azure DevOps organization with one PAT.

    The instance holds only the settings and the token: the HTTP client is
    created per request, inside the tool handler that called this.
    """

    def __init__(
        self,
        config: PluginConfig,
        pat: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.config = config.require()
        self.pat = pat
        self.transport = transport

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send one request and return its response.

        A failed status is translated into an ``AdoError``; there is no retry.
        """
        url = build_url(self.config, path)
        query: dict[str, Any] = dict(params or {})
        query["api-version"] = api_version_for(path, self.config.api_version)
        request_headers = dict(headers or {})
        with build_http_client(self.config, self.pat, self.transport) as http:
            try:
                response = http.request(
                    method,
                    url,
                    params=query,
                    json=json,
                    content=content,
                    headers=request_headers,
                )
            except httpx.TimeoutException:
                raise AdoError(
                    CODE_TIMEOUT,
                    f"Azure DevOps did not answer within {self.config.http_timeout_ms} ms.",
                ) from None
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                raise AdoError(
                    CODE_UPSTREAM_ERROR,
                    f"The request to Azure DevOps failed ({type(exc).__name__}).",
                ) from None
        if not 200 <= response.status_code < 300:
            raise error_for_response(response.status_code, response.text)
        return response

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return self.request(
            "POST", path, params=params, json=json, content=content, headers=headers
        )

    def patch(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return self.request(
            "PATCH", path, params=params, json=json, content=content, headers=headers
        )

    def put(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        content: bytes | str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return self.request(
            "PUT", path, params=params, json=json, content=content, headers=headers
        )

    def delete(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        return self.request("DELETE", path, params=params, headers=headers)


def _normalize_path(path: str) -> str:
    return "/" + str(path).strip().strip("/")


def _validated_base(config: PluginConfig) -> str:
    """The base URL of the settings, when it is an URL the client can use."""
    base = config.base_url.rstrip("/")
    url = httpx.URL(base)
    if url.scheme not in ("http", "https") or not url.host:
        raise AdoError(
            CODE_NOT_CONFIGURED,
            "Azure DevOps is not configured: the base_url setting "
            f"({base!r}) is not an http(s) URL.",
        )
    return base
