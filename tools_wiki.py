"""Tools of the wiki (read only).

The contract of the verification lives here: the list of the wikis is of the
**organization** (``GET /_apis/wiki/wikis``) and each wiki carries the id of
the project that owns it in its ``remoteUrl``. The pages of a wiki only answer
in the project that owns it — another project answers 404
``WikiNotFoundException`` — so the plugin finds the wiki first and calls its
pages in the owner project.
"""

from typing import Any

from .client import decode_json
from .contracts import wiki_owner_project, wiki_pages_path
from .errors import CODE_INVALID_INPUT, CODE_NOT_FOUND, AdoError
from .registry import ToolSpec
from .toolkit import args_of, client_for, list_items, text_arg, tool_spec

#: The route that lists the wikis of the organization.
WIKIS_ROUTE = "/_apis/wiki/wikis"

#: The page the tools read when the model does not name one.
DEFAULT_PAGE_PATH = "/Home"


def handle_list_wikis(args: dict, **kwargs) -> dict[str, Any]:
    """The wikis of the organization, with the project that owns each one."""
    adoc = client_for(kwargs)
    response = adoc.get(WIKIS_ROUTE)
    payload = decode_json(response)
    organization = adoc.config.organization
    wikis = [_wiki(item, organization) for item in list_items(payload)]
    return {"wikis": wikis, "count": len(wikis)}


def handle_list_wiki_pages(args: dict, **kwargs) -> dict[str, Any]:
    """The pages of a wiki, read in the project that owns it."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    wiki = _wiki_arg(adoc, arguments)
    response = adoc.get(_pages_path(adoc, wiki))
    payload = decode_json(response)
    pages = [_page(item) for item in list_items(payload)]
    return {
        "pages": pages,
        "count": len(pages),
        "wiki": _wiki(wiki, adoc.config.organization),
    }


def handle_get_wiki_page(args: dict, **kwargs) -> dict[str, Any]:
    """One page of a wiki, with its content and the date of its last change."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    wiki = _wiki_arg(adoc, arguments)
    page_path = text_arg(arguments, "path") or DEFAULT_PAGE_PATH
    response = adoc.get(_pages_path(adoc, wiki), params={"path": page_path})
    payload = decode_json(response)
    return {
        "page": _page(payload),
        "wiki": _wiki(wiki, adoc.config.organization),
    }


def _wiki_arg(adoc: Any, arguments: Any) -> dict[str, Any]:
    """The wiki the call is about, found in the wikis of the organization.

    The owner project of the wiki is only known by its ``remoteUrl``, so the
    plugin reads the wikis of the organization before the pages.
    """
    identifier = text_arg(arguments, "wikiId") or text_arg(arguments, "wiki")
    if not identifier:
        raise AdoError(
            CODE_INVALID_INPUT,
            "Name the wiki (wikiId) the call is about.",
        )
    response = adoc.get(WIKIS_ROUTE)
    payload = decode_json(response)
    wikis = list_items(payload)
    matches = [
        wiki
        for wiki in wikis
        if str(wiki.get("id") or "").strip().lower() == identifier.lower()
        or str(wiki.get("name") or "").strip().lower() == identifier.lower()
    ]
    if not matches:
        raise AdoError(
            CODE_NOT_FOUND,
            f"There is no wiki {identifier!r} in the organization: list the wikis and use the "
            "id of the one the call is about.",
        )
    return matches[0]


def _pages_path(adoc: Any, wiki: dict[str, Any]) -> str:
    """The path of the pages of a wiki, always in the project that owns it."""
    return wiki_pages_path(wiki, str(wiki.get("id") or ""), adoc.config.organization)


def _wiki(item: Any, organization: str) -> dict[str, Any]:
    """The fields of a wiki the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "name": source.get("name"),
        "path": source.get("path"),
        "url": source.get("url"),
        "remoteUrl": source.get("remoteUrl"),
        "ownerProject": wiki_owner_project(source, organization),
    }


def _page(item: Any) -> dict[str, Any]:
    """The fields of a page of a wiki the agent works with."""
    source = item if isinstance(item, dict) else {}
    return {
        "id": source.get("id"),
        "path": source.get("path"),
        "content": source.get("content"),
        "lastUpdatedDate": (
            source.get("lastUpdatedDate")
            or source.get("modifiedDate")
            or source.get("lastModifiedDate")
        ),
        "remoteUrl": source.get("remoteUrl"),
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_wikis",
        "List the wikis of the organization, with the project that owns each one.",
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
        handle_list_wikis,
    ),
    tool_spec(
        "azure_devops_list_wiki_pages",
        "List the pages of a wiki, in the project that owns it.",
        {
            "type": "object",
            "properties": {
                "wikiId": {
                    "type": "string",
                    "description": "Id of the wiki (as listed by azure_devops_list_wikis).",
                },
            },
            "required": ["wikiId"],
        },
        handle_list_wiki_pages,
    ),
    tool_spec(
        "azure_devops_get_wiki_page",
        "Get one page of a wiki, with its content and the date of its last change.",
        {
            "type": "object",
            "properties": {
                "wikiId": {
                    "type": "string",
                    "description": "Id of the wiki (as listed by azure_devops_list_wikis).",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "Path of the page in the wiki, for example /Home. Defaults to /Home."
                    ),
                },
            },
            "required": ["wikiId"],
        },
        handle_get_wiki_page,
    ),
]
