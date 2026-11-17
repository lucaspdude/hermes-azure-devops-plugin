"""Tools of pull requests that change state.

The routes and payload shapes are the ones the MCP connector exercises in
production; the identity used to vote is resolved per call in
:mod:`tools_identity` (the PAT belongs to one user, and voting as someone else
answers 403).

Every write answers with the identifier (and the url, when the API provides
one) of the object it touched, so the model can confirm without a second call.
Nothing is retried: a repeated create would open a second pull request.
"""

from typing import Any

from .errors import CODE_INVALID_INPUT, CODE_NOT_FOUND, AdoError
from .registry import ToolSpec
from .toolkit import (
    args_of,
    client_for,
    int_arg,
    project_arg,
    repository_arg,
    text_arg,
    tool_spec,
)

#: The votes the pull request reviewers route accepts (10 approve, 5 reject, 0 reset).
VOTES = {"approve": 10, "reject": 5, "reset": 0}


def handle_create_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """Open a pull request from one branch into another."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    source = text_arg(arguments, "sourceRefName")
    target = text_arg(arguments, "targetRefName")
    title = text_arg(arguments, "title")
    if not source or not target or not title:
        raise AdoError(
            CODE_INVALID_INPUT,
            "The parameters sourceRefName, targetRefName and title are required.",
        )
    body: dict[str, Any] = {
        "sourceRefName": _ref(source),
        "targetRefName": _ref(target),
        "title": title,
    }
    description = text_arg(arguments, "description")
    if description:
        body["description"] = description
    if arguments.get("isDraft") is not None:
        body["isDraft"] = bool(arguments["isDraft"])
    reviewers = arguments.get("reviewerIds")
    if reviewers:
        if not isinstance(reviewers, list) or not all(isinstance(r, str) for r in reviewers):
            raise AdoError(
                CODE_INVALID_INPUT,
                "The parameter reviewerIds must be a list of identity ids.",
            )
        body["reviewers"] = [{"id": reviewer} for reviewer in reviewers]
    response = adoc.post(
        f"/{project}/_apis/git/repositories/{repository}/pullrequests",
        json=body,
    )
    created = response.json()
    return {
        "pullRequestId": created.get("pullRequestId"),
        "url": _web_url(created),
        "title": created.get("title"),
    }


def handle_add_pull_request_comment(args: dict, **kwargs) -> dict[str, Any]:
    """Comment on a pull request: a new thread, or a reply in an existing one."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    content = text_arg(arguments, "comment")
    if not content:
        raise AdoError(CODE_INVALID_INPUT, "The parameter comment is required.")
    thread = arguments.get("threadId")
    if thread is not None:
        response = adoc.post(
            f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}"
            f"/threads/{int(thread)}/comments",
            json={"content": content, "commentType": 1, "parentCommentId": 0},
        )
    else:
        response = adoc.post(
            f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}/threads",
            json={
                "comments": [{"parentCommentId": 0, "content": content, "commentType": 1}],
                "status": text_arg(arguments, "status", default="active"),
            },
        )
    created = response.json()
    comments = created.get("comments") or []
    return {
        "threadId": created.get("id") or thread,
        "commentId": comments[0].get("id") if comments else None,
        "status": created.get("status"),
    }


def handle_add_pull_request_label(args: dict, **kwargs) -> dict[str, Any]:
    """Attach a label to a pull request, creating the label when it is absent."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    label = text_arg(arguments, "label")
    if not label:
        raise AdoError(CODE_INVALID_INPUT, "The parameter label is required.")
    label_id = text_arg(arguments, "labelId")
    response = adoc.post(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}/labels",
        json={"id": label_id or None, "name": label},
    )
    created = response.json()
    return {"labelId": created.get("id"), "name": created.get("name") or label}


def handle_remove_pull_request_label(args: dict, **kwargs) -> dict[str, Any]:
    """Detach a label from a pull request (the label definition stays)."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    label_id = text_arg(arguments, "labelId")
    label = text_arg(arguments, "label")
    if not label_id and not label:
        raise AdoError(CODE_INVALID_INPUT, "Pass labelId or label.")
    if not label_id:
        # The route addresses the label by id; resolve the name first.
        listed = adoc.get(
            f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}/labels"
        ).json()
        found = next(
            (item for item in listed.get("value", []) if item.get("name") == label),
            None,
        )
        if found is None:
            raise AdoError(CODE_NOT_FOUND, f"The label {label!r} is not on the pull request.")
        label_id = found.get("id")
    adoc.delete(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}"
        f"/labels/{label_id}"
    )
    return {"labelId": label_id, "name": label, "removed": True}


def handle_approve_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """Vote 10 (approve) as the authenticated user."""
    return _vote(args, kwargs, "approve")


def handle_reject_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """Vote 5 (reject) as the authenticated user."""
    return _vote(args, kwargs, "reject")


def handle_reset_pull_request_vote(args: dict, **kwargs) -> dict[str, Any]:
    """Reset the vote of the authenticated user back to no vote (0)."""
    return _vote(args, kwargs, "reset")


def handle_abandon_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """Abandon a pull request (status abandoned)."""
    return _set_status(args, kwargs, "abandoned")


def handle_complete_pull_request(args: dict, **kwargs) -> dict[str, Any]:
    """Complete (merge) a pull request, optionally squashing and deleting the branch."""
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    body: dict[str, Any] = {"status": "completed"}
    completion = {}
    if arguments.get("squashMerge") is not None:
        completion["squashMerge"] = bool(arguments["squashMerge"])
    if arguments.get("deleteSourceBranch") is not None:
        completion["deleteSourceBranch"] = bool(arguments["deleteSourceBranch"])
    if completion:
        body["completionOptions"] = completion
    response = adoc.patch(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}",
        json=body,
    )
    updated = response.json()
    return {
        "pullRequestId": updated.get("pullRequestId"),
        "status": updated.get("status"),
        "mergeCommitId": (updated.get("lastMergeCommit") or {}).get("commitId"),
        "url": _web_url(updated),
    }


def _vote(args: dict, kwargs: dict, kind: str) -> dict[str, Any]:
    from .tools_identity import authenticated_user_id

    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    user_id = authenticated_user_id(adoc)
    response = adoc.put(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}"
        f"/reviewers/{user_id}",
        json={"vote": VOTES[kind], "id": user_id},
    )
    reviewer = response.json()
    return {
        "pullRequestId": pull_request,
        "reviewerId": reviewer.get("id"),
        "vote": reviewer.get("vote"),
        "displayName": (reviewer.get("displayName") or ""),
    }


def _set_status(args: dict, kwargs: dict, status: str) -> dict[str, Any]:
    adoc = client_for(kwargs)
    arguments = args_of(args)
    project = project_arg(arguments)
    repository = repository_arg(arguments, adoc, project)
    pull_request = _pull_request_id(arguments)
    response = adoc.patch(
        f"/{project}/_apis/git/repositories/{repository}/pullRequests/{pull_request}",
        json={"status": status},
    )
    updated = response.json()
    return {
        "pullRequestId": updated.get("pullRequestId"),
        "status": updated.get("status"),
        "url": _web_url(updated),
    }


def _ref(name: str) -> str:
    """Accept a short branch name and always send the full ref."""
    return name if name.startswith("refs/") else f"refs/heads/{name}"


def _pull_request_id(arguments: Any) -> int:
    value = int_arg(arguments, "pullRequestId")
    if value is None:
        raise AdoError(CODE_INVALID_INPUT, "The parameter pullRequestId is required.")
    return value


def _web_url(pull_request: dict) -> str | None:
    links = pull_request.get("_links") or {}
    web = links.get("web") or {}
    return web.get("href") or pull_request.get("url")


def _pull_request_parameters() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "project": {
                "type": "string",
                "description": "Name or id of the project. Defaults to default_project.",
            },
            "repository": {
                "type": "string",
                "description": "Id or name of the repository. Optional when the project has "
                "a single Git repository.",
            },
            "pullRequestId": {
                "type": "integer",
                "description": "Numeric id of the pull request.",
            },
        },
        "required": ["pullRequestId"],
    }


def _create_parameters() -> dict[str, Any]:
    parameters = _pull_request_parameters()
    parameters["properties"].update(
        {
            "sourceRefName": {"type": "string", "description": "Source branch (name or full ref)."},
            "targetRefName": {"type": "string", "description": "Target branch (name or full ref)."},
            "title": {"type": "string", "description": "Title of the pull request."},
            "description": {"type": "string", "description": "Optional description."},
            "isDraft": {"type": "boolean", "description": "Open as a draft."},
            "reviewerIds": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional identity ids to request as reviewers.",
            },
        }
    )
    parameters["required"] = ["sourceRefName", "targetRefName", "title"]
    return parameters


def _comment_parameters() -> dict[str, Any]:
    parameters = _pull_request_parameters()
    parameters["properties"].update(
        {
            "comment": {"type": "string", "description": "Text of the comment."},
            "threadId": {
                "type": "integer",
                "description": "Reply into this thread instead of opening a new one.",
            },
            "status": {
                "type": "string",
                "description": "Status of the new thread (default active).",
            },
        }
    )
    parameters["required"] = ["comment"]
    return parameters


def _label_parameters() -> dict[str, Any]:
    parameters = _pull_request_parameters()
    parameters["properties"].update(
        {
            "label": {"type": "string", "description": "Name of the label."},
            "labelId": {"type": "string", "description": "Id of the label (instead of the name)."},
        }
    )
    return parameters


def _complete_parameters() -> dict[str, Any]:
    parameters = _pull_request_parameters()
    parameters["properties"].update(
        {
            "squashMerge": {"type": "boolean", "description": "Squash the commits when merging."},
            "deleteSourceBranch": {"type": "boolean", "description": "Delete the source branch."},
        }
    )
    return parameters


TOOLS: list[ToolSpec] = [
    tool_spec(
        "azure_devops_create_pull_request",
        "Open a pull request from one branch into another. This CHANGES Azure DevOps: use it "
        "when the user asks to open a PR, with source branch, target branch and title.",
        _create_parameters(),
        handle_create_pull_request,
    ),
    tool_spec(
        "azure_devops_add_pull_request_comment",
        "Comment on a pull request: opens a new thread, or replies into one when threadId is "
        "given. This CHANGES Azure DevOps.",
        _comment_parameters(),
        handle_add_pull_request_comment,
    ),
    tool_spec(
        "azure_devops_add_pull_request_label",
        "Attach a label to a pull request, creating the label when it is absent. This CHANGES "
        "Azure DevOps.",
        _label_parameters(),
        handle_add_pull_request_label,
    ),
    tool_spec(
        "azure_devops_remove_pull_request_label",
        "Detach a label from a pull request (the label definition itself stays). This CHANGES "
        "Azure DevOps.",
        _label_parameters(),
        handle_remove_pull_request_label,
    ),
    tool_spec(
        "azure_devops_approve_pull_request",
        "Approve a pull request (vote 10) as the identity that owns the PAT. This CHANGES "
        "Azure DevOps.",
        _pull_request_parameters(),
        handle_approve_pull_request,
    ),
    tool_spec(
        "azure_devops_reject_pull_request",
        "Reject a pull request (vote 5) as the identity that owns the PAT. This CHANGES "
        "Azure DevOps.",
        _pull_request_parameters(),
        handle_reject_pull_request,
    ),
    tool_spec(
        "azure_devops_reset_pull_request_vote",
        "Reset the vote of the identity that owns the PAT back to no vote. This CHANGES "
        "Azure DevOps.",
        _pull_request_parameters(),
        handle_reset_pull_request_vote,
    ),
    tool_spec(
        "azure_devops_abandon_pull_request",
        "Abandon a pull request (close it without merging). This CHANGES Azure DevOps.",
        _pull_request_parameters(),
        handle_abandon_pull_request,
    ),
    tool_spec(
        "azure_devops_complete_pull_request",
        "Complete (merge) a pull request, optionally squashing and deleting the source branch. "
        "This CHANGES Azure DevOps.",
        _complete_parameters(),
        handle_complete_pull_request,
    ),
]
