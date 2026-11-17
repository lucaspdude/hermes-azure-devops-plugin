"""Normalised pagination for the Azure DevOps REST API.

Azure DevOps hands the continuation token over in two different places: the
``x-ms-continuationtoken`` header (builds) or inside the body (the other
APIs). The plugin exposes one field only — ``continuationToken`` — and feeds
it back as the ``continuationToken`` query parameter of the next page.
"""

from typing import Any, Mapping

#: The single field the tools expose.
CONTINUATION_TOKEN_FIELD = "continuationToken"

#: Where the builds API puts the token.
CONTINUATION_TOKEN_HEADER = "x-ms-continuationtoken"

#: Where the other APIs put the token.
BODY_TOKEN_FIELDS = ("continuationToken", "nextPage")

#: Azure DevOps ignores a page size without the dollar sign.
PAGE_SIZE_PARAM = "$top"


def extract_continuation_token(response: Any) -> str:
    """The continuation token of a page, or ``""`` when there is no next page."""
    token = _header_token(response)
    if token:
        return token
    return _body_token(response)


def normalize_page(payload: Mapping[str, Any], token: str | None = None) -> dict[str, Any]:
    """The payload with the single ``continuationToken`` field the tools expose."""
    normalized = {key: value for key, value in payload.items() if key not in BODY_TOKEN_FIELDS}
    if token is None:
        token = _token_from_payload(payload)
    normalized[CONTINUATION_TOKEN_FIELD] = token or ""
    return normalized


def pagination_params(top: int | None = None, token: str | None = None) -> dict[str, str]:
    """The query parameters of a page: the page size and the token to continue."""
    params: dict[str, str] = {}
    if top is not None:
        params[PAGE_SIZE_PARAM] = str(top)
    if token:
        params[CONTINUATION_TOKEN_FIELD] = token
    return params


def _header_token(response: Any) -> str:
    headers = getattr(response, "headers", None) or {}
    token = headers.get(CONTINUATION_TOKEN_HEADER)
    if token:
        return str(token).strip()
    items = getattr(headers, "items", None)
    if items is None:
        return ""
    for name, value in items():
        if str(name).lower() == CONTINUATION_TOKEN_HEADER:
            return str(value).strip()
    return ""


def _body_token(response: Any) -> str:
    loader = getattr(response, "json", None)
    if loader is None:
        return ""
    try:
        payload = loader()
    except Exception:  # noqa: BLE001 - a body that is not JSON carries no token
        return ""
    return _token_from_payload(payload)


def _token_from_payload(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    sources: list[Mapping[str, Any]] = [payload]
    nested = payload.get("value")
    if isinstance(nested, Mapping):
        sources.append(nested)
    for source in sources:
        for field in BODY_TOKEN_FIELDS:
            value = source.get(field)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return ""
