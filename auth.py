"""The Azure DevOps PAT, resolved through the Hermes secret scope.

The token never comes from a file, from ``os.environ`` or from ``auth.json``:
the only source is ``agent.secret_scope.get_secret`` on the active profile.
"""

from typing import Callable, Optional

from .errors import CODE_MISSING_CREDENTIAL, AdoError

PAT_SECRET_NAME = "AZURE_DEVOPS_PAT_TOKEN"

#: Reads a secret by name and returns its value (``None`` when it is not set).
SecretResolver = Callable[[str], Optional[str]]


def _secret_scope_resolver(name: str) -> Optional[str]:
    """Read a secret from the Hermes secret scope.

    The import lives inside the function: ``agent.secret_scope`` only exists
    inside the Hermes runtime, and the plugin must stay importable outside it
    (the test suite resolves the secret through an injected resolver).
    """
    from agent.secret_scope import get_secret

    return get_secret(name)


def resolve_pat(resolver: Optional[SecretResolver] = None) -> str:
    """Return the PAT, or raise ``missing_credential``.

    The error never quotes the token and never chains a traceback: the message
    is the whole answer the user gets.
    """
    read = resolver or _secret_scope_resolver
    try:
        value = read(PAT_SECRET_NAME)
    except Exception as exc:  # noqa: BLE001 - any failure here is "no credential"
        raise AdoError(CODE_MISSING_CREDENTIAL, _unreadable_message(exc)) from None
    if value is None or not str(value).strip():
        raise AdoError(CODE_MISSING_CREDENTIAL, _missing_message())
    return str(value).strip()


def check_pat_available(resolver: Optional[SecretResolver] = None) -> bool:
    """``check_fn`` for the tools: False withdraws the tool (Hermes reports it as needing auth)."""
    try:
        resolve_pat(resolver)
    except AdoError:
        return False
    return True


def _missing_message() -> str:
    return (
        f"Azure DevOps PAT not found. Set {PAT_SECRET_NAME} in the active Hermes profile "
        "(the plugin's requires_env entry) and retry."
    )


def _unreadable_message(exc: Exception) -> str:
    if getattr(exc, "secret_name", None):
        # UnscopedSecretError: the profile's secret scope is not installed, which
        # is a Hermes scoping bug rather than a missing token.
        return (
            f"Hermes could not read {PAT_SECRET_NAME} for the active profile (the secret scope "
            "is not installed). Run `hermes gateway restart` and retry."
        )
    return _missing_message()
