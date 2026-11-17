"""docs/ado-endpoints.md: the record of the endpoint verification.

The record is the memory of the verification: the routes that answered, the
routes that did not, and the contract each one carries. A tool that is not in
the record is a tool whose route was never checked — so the record has to
cover the whole reading surface, and the suite says so.
"""

import unittest

from support import PLUGIN_DIR

DOC = PLUGIN_DIR / "docs" / "ado-endpoints.md"

#: The reading surface of the plugin: the record has to cover all of it.
READ_TOOLS = (
    "azure_devops_list_projects",
    "azure_devops_get_project",
    "azure_devops_list_repositories",
    "azure_devops_get_repository",
    "azure_devops_list_build_definitions",
    "azure_devops_list_builds",
    "azure_devops_get_build",
    "azure_devops_get_build_changes",
    "azure_devops_get_build_timeline",
    "azure_devops_list_pull_requests",
    "azure_devops_get_pull_request",
    "azure_devops_list_pull_request_comments",
    "azure_devops_list_pull_request_labels",
    "azure_devops_query_wiql",
    "azure_devops_get_work_item",
    "azure_devops_list_work_items",
    "azure_devops_list_wikis",
    "azure_devops_list_wiki_pages",
    "azure_devops_get_wiki_page",
    "azure_devops_list_branches",
    "azure_devops_get_branch",
    "azure_devops_list_commits",
    "azure_devops_get_commit",
    "azure_devops_list_tags",
    "azure_devops_list_build_artifacts",
    "azure_devops_get_my_identity",
    "azure_devops_list_identities",
    "azure_devops_list_policies",
    "azure_devops_list_release_definitions",
    "azure_devops_list_releases",
    "azure_devops_get_release",
)


class EndpointRecordTest(unittest.TestCase):
    def setUp(self):
        self.record = DOC.read_text(encoding="utf-8")

    def test_the_record_exists(self):
        self.assertTrue(DOC.is_file(), f"the record of the verification is missing: {DOC}")

    def test_the_record_covers_the_31_reading_tools(self):
        self.assertEqual(len(READ_TOOLS), 31)

        missing = [name for name in READ_TOOLS if name not in self.record]

        self.assertEqual(
            missing,
            [],
            "tool(s) missing from the record of the verification: " + ", ".join(missing),
        )

    def test_the_record_carries_the_date_of_the_verification(self):
        self.assertIn("2026-11-17", self.record)

    def test_the_record_carries_the_codes_of_the_routes(self):
        self.assertIn("200", self.record)
        self.assertIn("401", self.record)
        self.assertIn("404", self.record)
        self.assertIn("400", self.record)

    def test_the_record_carries_the_routes_that_failed(self):
        self.assertIn("/_apis/policies/repositories/", self.record)
        self.assertIn("/_apis/git/repositories/{repoId}/labels", self.record)
        self.assertIn("connectionData", self.record)
        self.assertIn("preview", self.record)

    def test_the_record_carries_the_contracts_of_the_verification(self):
        self.assertIn("$top", self.record)
        self.assertIn("x-ms-continuationtoken", self.record)
        self.assertIn("refs/heads/master", self.record)
        self.assertIn("remoteUrl", self.record)
        self.assertIn("411", self.record)
        self.assertIn("405", self.record)

    def test_the_record_names_the_hosts_of_the_calls(self):
        self.assertIn("https://dev.azure.com/{organization}", self.record)
        self.assertIn("https://vsrm.dev.azure.com/{organization}", self.record)


if __name__ == "__main__":
    unittest.main()
