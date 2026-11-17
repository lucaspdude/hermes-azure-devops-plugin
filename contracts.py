"""The API contracts verified against the real Azure DevOps API (2026-11-17).

The findings of the endpoint verification are not documentation: they are
contracts the API really enforces. Each one is encoded once, here, and every
tool goes through it — so the traps the verification found cannot come back
in one tool only.

The record of the verification (routes, codes, notes) is in
``docs/ado-endpoints.md``.
"""

from typing import Any, Mapping
from urllib.parse import urlsplit

from .errors import CODE_INVALID_INPUT, AdoError
from .pagination import PAGE_SIZE_PARAM, pagination_params

__all__ = [
    "PAGE_SIZE_PARAM",
    "page_params",
    "short_branch",
    "wiki_owner_project",
    "wiki_pages_path",
    "wiql_body",
]

#: The commits API wants the branch as the short name (``master``).
BRANCH_PREFIX = "refs/heads/"

#: The marker of the REST routes in a path.
_APIS_MARKER = "_apis"
_WIKI_MARKER = "_wiki"  # the real remoteUrl shape: /{org}/{project}/_wiki/wikis/{id}


def page_params(top: int | None = None, token: str | None = None) -> dict[str, str]:
    """The query parameters of a page.

    The page size is ``$top``: Azure DevOps ignores a ``top`` without the dollar
    sign, which paginates silently wrong (the verification saw the builds
    route answer the whole list).
    """
    return pagination_params(top, token)


def short_branch(branch: str) -> str:
    """The branch name the commits API expects: ``master``, not ``refs/heads/master``.

    The verification answered 404 for ``refs/heads/master`` and 200 for
    ``master``: the commits route wants the short name.
    """
    name = str(branch or "").strip()
    if name.startswith(BRANCH_PREFIX):
        name = name[len(BRANCH_PREFIX) :]
    return name


def wiki_owner_project(wiki: Mapping[str, Any], organization: str = "") -> str:
    """The project that owns the wiki, taken from the wiki's ``remoteUrl``.

    The wikis of the organization (``/_apis/wiki/wikis``) belong to different
    projects, and each one carries the id of its owner in the ``remoteUrl``.
    The pages of a wiki only answer in the project that owns it (another
    project answers 404 ``WikiNotFoundException``).

    Returns an empty string for a wiki of the organization itself, which has no
    owner project.
    """
    remote_url = _remote_url(wiki)
    if not remote_url:
        return ""
    segments = [segment for segment in urlsplit(remote_url).path.split("/") if segment]
    marker = next((m for m in (_APIS_MARKER, _WIKI_MARKER) if m in segments), None)
    if marker is None:
        return ""
    index = segments.index(marker)
    if index < 2:
        # ``/{organization}/_wiki/...``: a wiki of the organization, no owner.
        return ""
    owner = segments[index - 1]
    if organization and owner.lower() == organization.lower():
        return ""
    return owner


def wiki_pages_path(
    wiki: Mapping[str, Any],
    wiki_id: str,
    organization: str = "",
) -> str:
    """The path of the pages of a wiki, always in the project that owns it."""
    owner = wiki_owner_project(wiki, organization)
    if not owner:
        raise AdoError(
            CODE_INVALID_INPUT,
            "The wiki does not carry the project that owns it: the remoteUrl has no project "
            "segment. List the wikis of the organization again and use the one that has a "
            "remoteUrl.",
        )
    return f"/{owner}/_apis/wiki/wikis/{wiki_id}/pages"


def wiql_body(query: str) -> dict[str, Any]:
    """The body of a WIQL query.

    The route only answers a POST with a JSON body: without a body it answers
    411, and a GET answers 405. The page size travels as the ``$top`` query
    parameter, never inside the body.
    """
    return {"query": str(query or "")}


def _remote_url(wiki: Mapping[str, Any]) -> str:
    """The ``remoteUrl`` of a wiki, wherever it sits in the payload."""
    if not isinstance(wiki, Mapping):
        return ""
    candidates = [wiki.get("remoteUrl")]
    properties = wiki.get("properties")
    if isinstance(properties, Mapping):
        candidates.append(properties.get("remoteUrl"))
    for candidate in candidates:
        if candidate:
            return str(candidate).strip()
    return ""
