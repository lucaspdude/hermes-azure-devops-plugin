"""Closed error taxonomy of the plugin.

Every failure the plugin reports carries one actionable code, so the agent (and
the user) can tell "the token is missing" from "the API said no" without
reading a stack trace.
"""

import json
from typing import Any

CODE_NOT_CONFIGURED = "not_configured"
CODE_MISSING_CREDENTIAL = "missing_credential"
CODE_INVALID_INPUT = "invalid_input"
CODE_UNAUTHORIZED = "unauthorized"
CODE_FORBIDDEN = "forbidden"
CODE_NOT_FOUND = "not_found"
CODE_RATE_LIMITED = "rate_limited"
CODE_TIMEOUT = "timeout"
CODE_UPSTREAM_ERROR = "upstream_error"

ERROR_CODES = (
    CODE_NOT_CONFIGURED,
    CODE_MISSING_CREDENTIAL,
    CODE_INVALID_INPUT,
    CODE_UNAUTHORIZED,
    CODE_FORBIDDEN,
    CODE_NOT_FOUND,
    CODE_RATE_LIMITED,
    CODE_TIMEOUT,
    CODE_UPSTREAM_ERROR,
)


class AdoError(Exception):
    """A failure with an actionable code.

    ``str(exc)`` is the single sentence the user reads: it never carries a
    stack trace and never carries a credential value.
    """

    def __init__(self, code: str, message: str, status: int | None = None, type_key: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.type_key = type_key

    def __str__(self) -> str:
        return self.message


#: HTTP status -> code of the taxonomy.
STATUS_TO_CODE: dict[int, str] = {
    400: CODE_INVALID_INPUT,
    401: CODE_UNAUTHORIZED,
    403: CODE_FORBIDDEN,
    404: CODE_NOT_FOUND,
    408: CODE_TIMEOUT,
    429: CODE_RATE_LIMITED,
}

_DEFAULT_MESSAGES: dict[str, str] = {
    CODE_INVALID_INPUT: "Azure DevOps rejected the request as invalid.",
    CODE_UNAUTHORIZED: "Azure DevOps rejected the credentials.",
    CODE_FORBIDDEN: "Azure DevOps denied the operation.",
    CODE_NOT_FOUND: "Azure DevOps did not find the requested resource.",
    CODE_TIMEOUT: "Azure DevOps timed out the request.",
    CODE_RATE_LIMITED: "Azure DevOps rate-limited the request.",
    CODE_UPSTREAM_ERROR: "Azure DevOps failed to serve the request.",
}

#: The one hint the user needs when Azure DevOps says "no": a PAT that is
#: valid but not scoped for the operation.
SCOPE_HINT = "The PAT may not have the scope this operation requires."


def code_for_status(status_code: int) -> str:
    """The taxonomy code of an HTTP failure status."""
    if status_code in STATUS_TO_CODE:
        return STATUS_TO_CODE[status_code]
    if 400 <= status_code < 500:
        return CODE_INVALID_INPUT
    return CODE_UPSTREAM_ERROR


def error_for_response(status_code: int, body: str | bytes | None = None) -> AdoError:
    """Map a failed HTTP response to the closed taxonomy.

    The Azure DevOps error body (``message`` and ``typeKey``) is preserved
    when it is JSON; a body that is not JSON never changes the code of a
    status that has one of its own (401 stays ``unauthorized``), it only makes
    the message say that the body was unreadable.
    """
    code = code_for_status(status_code)
    message, type_key = parse_error_body(body)
    if message is None:
        message = f"{_DEFAULT_MESSAGES.get(code, _DEFAULT_MESSAGES[CODE_UPSTREAM_ERROR])} (HTTP {status_code})."
    if code == CODE_FORBIDDEN and SCOPE_HINT not in message:
        message = f"{message} {SCOPE_HINT}"
    if not _is_json(body) and str(body or "").strip():
        message = f"{message} The response body was not JSON."
    return AdoError(code, message, status=status_code, type_key=type_key)


def non_json_response_error(status_code: int) -> AdoError:
    """The API answered with something that is not JSON: the contract broke."""
    return AdoError(
        CODE_UPSTREAM_ERROR,
        f"Azure DevOps returned a response that is not JSON (HTTP {status_code}).",
        status=status_code,
    )


def parse_error_body(body: str | bytes | None) -> tuple[str | None, str | None]:
    """The ``(message, typeKey)`` of an Azure DevOps error body, if it has them."""
    payload, _ = _decode_json(body)
    return _message_and_type_key(payload)


def _decode_json(body: str | bytes | None) -> tuple[Any, bool]:
    """The parsed body and whether it was JSON at all."""
    if body is None:
        return None, True
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    if not text.strip():
        return None, True
    try:
        return json.loads(text), True
    except ValueError:
        return None, False


def _is_json(body: str | bytes | None) -> bool:
    """Whether the body is JSON at all."""
    _, parsed = _decode_json(body)
    return parsed


def _message_and_type_key(payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    sources: list[dict[str, Any]] = [payload]
    nested = payload.get("value")
    if isinstance(nested, dict):
        sources.append(nested)
    message: str | None = None
    type_key: str | None = None
    for source in sources:
        if message is None:
            message = _as_text(source.get("message"))
        if type_key is None:
            type_key = _as_text(source.get("typeKey"))
    return message, type_key


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
