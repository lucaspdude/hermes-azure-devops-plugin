"""Tool of policies (read only).

The route of policies **by repository** is not reachable with a classic PAT:
the service of policies refuses the token (401 with a PAT of minimum scopes,
404 with a PAT of full scope — the route exists, the authorization does not).
What answers is the policy configurations of the project
(``/_apis/policy/configurations``), which is what this tool reads.

The tool says so in every answer, so nobody reads the absence of a
per-repository filter as "the repository has no policy".
"""

from typing import Any

from .client import decode_json
from .registry import ToolSpec
from .toolkit import args_of, client_for, list_items, project_arg, text_arg, tool_spec

#: The route that a classic PAT cannot reach.
POLICY_BY_REPOSITORY_ROUTE = "/_apis/policies/repositories/{repositoryId}"


def handle_list_policies(args: dict, **kwargs) -> dict[str, Any]:
    """The policy configurations of a project."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = text_arg(arguments, "repository")
    response = adoc.get(f"/{project}/_apis/policy/configurations")
    payload = decode_json(response)
    return {
        "policies": [_policy(item) for item in list_items(payload)],
        "note": _note(repository),
    }


def _note(repository: str) -> str:
    """The warning that tells the caller the route it asked for does not answer."""
    if repository:
        return (
            f"The policies of the repository {repository!r} were asked for, but the route "
            f"{POLICY_BY_REPOSITORY_ROUTE} is not reachable with a classic PAT (401 with a "
            "PAT of minimum scopes, 404 with a PAT of full scope). The policy configurations "
            "of the project are returned instead."
        )
    return (
        "The policy configurations of the project are returned: the route "
        f"{POLICY_BY_REPOSITORY_ROUTE}, which reads the policies of a single repository, is "
        "not reachable with a classic PAT (401 with a PAT of minimum scopes, 404 with a PAT of "
        "full scope)."
    )


def _policy(item: Any) -> dict[str, Any]:
    """The fields of a policy configuration the agent works with."""
    source = item if isinstance(item, dict) else {}
    policy_type = source.get("type")
    type_fields: dict[str, Any] = {}
    if isinstance(policy_type, dict):
        type_fields = {
            "id": policy_type.get("id"),
            "displayName": policy_type.get("displayName"),
        }
    return {
        "id": source.get("id"),
        "url": source.get("url"),
        "type": type_fields,
        "isEnabled": source.get("isEnabled"),
        "isBlocking": source.get("isBlocking"),
        "settings": source.get("settings"),
    }


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_list_policies",
        "List the policy configurations of a project (branch expiration, minimum review, ...).",
        {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": (
                        "Name or id of the project. Defaults to the configured default_project."
                    ),
                },
                "repository": {
                    "type": "string",
                    "description": (
                        "Repository the policies are asked for. Policies by repository are not "
                        "readable with a classic PAT: the configurations of the project are "
                        "returned instead."
                    ),
                },
            },
            "required": [],
        },
        handle_list_policies,
    ),
]
