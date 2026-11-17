---
name: azure-devops-workflows
description: Recipes for the Azure DevOps plugin - broken builds, PR review and vote, PR from a branch, my work items, queueing a build.
---

# Azure DevOps plugin — workflows

## Investigate a broken build

1. `azure_devops_list_builds` with `status=inProgress`/`completed` filtered by the
   definition, newest first.
2. `azure_devops_get_build_timeline` of the failed build: find the task that
   failed and its parent job.
3. `azure_devops_get_build_changes` of the same build: the commits it picked up.
4. If a commit explains the failure, `azure_devops_get_commit` for the full
   message and author; then `azure_devops_list_pull_requests` to see whether the
   commit came from a PR.

## Review and vote on a pull request

1. `azure_devops_list_pull_requests` (`active`) for the repository.
2. `azure_devops_get_pull_request` for the reviewers and the vote of each one.
3. `azure_devops_list_pull_request_comments` for the discussion threads.
4. `azure_devops_approve_pull_request` (or reject/reset) — the vote is always
   the identity of the PAT owner; a second identity answers 403.
5. `azure_devops_complete_pull_request` with `squashMerge` when the branch
   policy allows it; a refused completion answers `forbidden` with the policy
   message — do not work around it.

## Open a PR from an existing branch

1. `azure_devops_list_branches` to confirm the source exists.
2. `azure_devops_create_pull_request` with source, target, title and
   description; `isDraft` when the user wants a draft.
3. Answer with the id and the url the tool returns.

## My work items

1. `azure_devops_get_my_identity` for the id of the PAT owner.
2. `azure_devops_query_wiql` with a query filtering
   `[System.AssignedTo] = '<the id or email>'` ordered by
   `[System.ChangedDate] desc`.
3. `azure_devops_get_work_item` for the fields of each one;
   `azure_devops_update_work_item` (JSON Patch) only when the user asked for
   the change.

## Queue a build

1. `azure_devops_list_build_definitions` to find the pipeline by name.
2. `azure_devops_queue_build` with the definition and the branch; the answer
   carries the id and the initial status of the build.
