"""
Tests for ``github_client.py`` — GitHub REST API v3 client.

All external HTTP calls are mocked via ``@patch`` decorators.
No real network requests are made — tests run in < 0.5s.
"""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from github_client import (
    GitHubClient,
    PRDetail,
    FileChange,
    PRReviewData,
    RateLimit,
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubConflictError,
    GitHubServerError,
    GitHubConnectionError,
    GitHubClientError,
)


# ===========================================================================
# Mock response factory
# ===========================================================================

def _mock_response(
    status: int = 200,
    json_data: dict | list | None = None,
    text_data: str = "",
    headers: dict | None = None,
) -> MagicMock:
    """Build a ``requests.Response``-shaped mock."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.ok = status < 400
    resp.headers = {
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Reset": str(int(time.time()) + 3600),
        "X-RateLimit-Used": "1",
        **(headers or {}),
    }
    resp.request = MagicMock()
    resp.request.path_url = "/repos/octocat/Hello-World/pulls/1"

    if status >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=requests.HTTPError(f"{status} Error", response=resp)
        )
    else:
        resp.raise_for_status = MagicMock()

    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
        resp.text = json.dumps(json_data)
    else:
        resp.text = text_data
        resp.content = text_data.encode()
    return resp


SAMPLE_PR = {
    "number": 1, "state": "open", "title": "Fix login redirect",
    "body": "Updated callback URL.", "user": {"login": "octocat"},
    "base": {"ref": "main", "sha": "a"},
    "head": {"ref": "feat/fix", "sha": "b"},
    "mergeable": True, "changed_files": 2, "additions": 50, "deletions": 10,
    "html_url": "https://github.com/octocat/Hello-World/pull/1",
    "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-02T00:00:00Z",
}

SAMPLE_FILES = [{
    "filename": "src/auth.py", "status": "modified",
    "additions": 30, "deletions": 5, "changes": 35,
    "patch": "@@ -1,3 +1,8 @@\n+import os",
    "raw_url": "", "blob_url": "", "contents_url": "",
}]

SAMPLE_DIFF = "diff --git a/src/auth.py b/src/auth.py\n@@ -1,3 +1,8 @@\n+import os\n"


# ===========================================================================
# Data class tests (no mocking needed)
# ===========================================================================


class TestPRDetail:
    def test_all_fields(self) -> None:
        pr = PRDetail("Fix", "Fixed auth", "alice", "open", "main", "feat",
                      "a", "b", True, 2, 50, 10, "url", "2025-01-01", "2025-01-02")
        assert pr.title == "Fix"
        assert pr.author == "alice"
        assert pr.mergeable is True

    def test_mergeable_none(self) -> None:
        pr = PRDetail("", "", "", "open", "", "", "", "", None, 0, 0, 0, "", "", "")
        assert pr.mergeable is None


class TestFileChange:
    def test_is_binary(self) -> None:
        assert FileChange("img.png", "added", 1, 0, 1, patch=None).is_binary is True
        assert FileChange("main.py", "modified", 10, 5, 15,
                          patch="@@ -1,3 +1,5 @@").is_binary is False

    def test_previous_filename(self) -> None:
        fc = FileChange("new.py", "renamed", 0, 0, 0, patch=None,
                        previous_filename="old.py")
        assert fc.previous_filename == "old.py"


class TestRateLimit:
    def test_is_exhausted(self) -> None:
        future = int(time.time()) + 3600
        assert RateLimit(0, 5000, future, 5000).is_exhausted is True
        assert RateLimit(100, 5000, future, 4900).is_exhausted is False

    def test_reset_in_seconds(self) -> None:
        past = int(time.time()) - 60
        assert RateLimit(5000, 5000, past, 0).reset_in_seconds >= 0


# ===========================================================================
# GitHubClient — successful calls (@patch on requests.Session.request)
# ===========================================================================

PATCH_TARGET = "github_client.requests.Session.request"


class TestClientSuccess:
    """All external HTTP mocked via @patch."""

    @pytest.fixture
    def client(self) -> GitHubClient:
        return GitHubClient(token="test-token", max_retries=0)

    # ------------------------------------------------------------------
    # get_pr()
    # ------------------------------------------------------------------

    @patch(PATCH_TARGET)
    def test_get_pr(self, mock_request: MagicMock, client: GitHubClient) -> None:
        mock_request.return_value = _mock_response(200, SAMPLE_PR)

        pr = client.get_pr("octocat", "Hello-World", 1)

        assert isinstance(pr, PRDetail)
        assert pr.title == "Fix login redirect"
        assert pr.author == "octocat"
        assert pr.description == "Updated callback URL."
        assert pr.state == "open"
        assert pr.base_branch == "main"
        assert pr.head_branch == "feat/fix"
        assert pr.mergeable is True
        assert pr.additions == 50
        assert pr.deletions == 10

    @patch(PATCH_TARGET)
    def test_get_pr_mergeable_none(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        data = dict(SAMPLE_PR)
        data["mergeable"] = None
        mock_request.return_value = _mock_response(200, data)

        pr = client.get_pr("octocat", "Hello-World", 1)
        assert pr.mergeable is None

    @patch(PATCH_TARGET)
    def test_rate_limit_tracked(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(200, SAMPLE_PR)

        assert client.rate_limit is None
        client.get_pr("octocat", "Hello-World", 1)
        rl = client.rate_limit
        assert rl is not None
        assert rl.remaining == 4999
        assert rl.limit == 5000

    # ------------------------------------------------------------------
    # get_pr_files()
    # ------------------------------------------------------------------

    @patch(PATCH_TARGET)
    def test_get_pr_files(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(200, SAMPLE_FILES)

        files = client.get_pr_files("octocat", "Hello-World", 1)

        assert len(files) == 1
        assert files[0].filename == "src/auth.py"
        assert files[0].status == "modified"
        assert files[0].is_binary is False

    @patch(PATCH_TARGET)
    def test_get_pr_files_pagination(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        page1 = [{"filename": f"f{i}.py", "status": "added",
                  "additions": 1, "deletions": 0, "changes": 1, "patch": ""}
                 for i in range(100)]
        page2 = [{"filename": "extra.py", "status": "added",
                  "additions": 1, "deletions": 0, "changes": 1, "patch": ""}]
        mock_request.side_effect = [
            _mock_response(200, page1),
            _mock_response(200, page2),
        ]

        files = client.get_pr_files("octocat", "Hello-World", 1, per_page=100)

        assert len(files) == 101
        assert mock_request.call_count == 2

    @patch(PATCH_TARGET)
    def test_get_pr_files_empty(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(200, [])
        assert client.get_pr_files("octocat", "Hello-World", 1) == []

    # ------------------------------------------------------------------
    # get_pr_diff()
    # ------------------------------------------------------------------

    @patch(PATCH_TARGET)
    def test_get_pr_diff(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(200, text_data=SAMPLE_DIFF)

        diff = client.get_pr_diff("octocat", "Hello-World", 1)

        assert "diff --git" in diff

    @patch(PATCH_TARGET)
    def test_get_pr_diff_accept_header(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(200, text_data="")

        client.get_pr_diff("octocat", "Hello-World", 1)

        call_headers = mock_request.call_args[1].get("headers", {})
        assert call_headers.get("Accept") == "application/vnd.github.v3.diff"

    # ------------------------------------------------------------------
    # review_pr()
    # ------------------------------------------------------------------

    @patch(PATCH_TARGET)
    def test_review_pr(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.side_effect = [
            _mock_response(200, SAMPLE_PR),
            _mock_response(200, SAMPLE_FILES),
            _mock_response(200, text_data=SAMPLE_DIFF),
        ]

        data = client.review_pr("octocat", "Hello-World", 1)

        assert isinstance(data, PRReviewData)
        assert data.pr.title == "Fix login redirect"
        assert len(data.files) == 1
        assert "diff --git" in data.diff
        assert mock_request.call_count == 3


# ===========================================================================
# Error handling (@patch on requests.Session.request)
# ===========================================================================


class TestClientErrors:
    @pytest.fixture
    def client(self) -> GitHubClient:
        return GitHubClient(token="test-token", max_retries=0)

    @patch(PATCH_TARGET)
    def test_401_auth_error(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(401)
        with pytest.raises(GitHubAuthError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_404_not_found(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(404)
        with pytest.raises(GitHubNotFoundError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_403_rate_limit(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(403)
        with pytest.raises(GitHubRateLimitError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_429_with_retry_after(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(
            429, headers={"Retry-After": "30"}
        )
        with pytest.raises(GitHubRateLimitError) as exc:
            client.get_pr("octocat", "Hello-World", 1)
        assert exc.value.retry_after == 30.0

    @patch(PATCH_TARGET)
    def test_409_conflict(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(409)
        with pytest.raises(GitHubConflictError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_500_server_error(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(500)
        with pytest.raises(GitHubServerError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_503_server_error(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(503)
        with pytest.raises(GitHubServerError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_connection_error(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.side_effect = requests.ConnectionError("DNS failed")
        with pytest.raises(GitHubConnectionError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_timeout(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.side_effect = requests.Timeout("timed out")
        with pytest.raises(GitHubConnectionError):
            client.get_pr("octocat", "Hello-World", 1)

    @patch(PATCH_TARGET)
    def test_unknown_status(
        self, mock_request: MagicMock, client: GitHubClient
    ) -> None:
        mock_request.return_value = _mock_response(418)
        with pytest.raises(requests.HTTPError):
            client.get_pr("octocat", "Hello-World", 1)


class TestErrorHierarchy:
    def test_all_subclasses(self) -> None:
        assert issubclass(GitHubAuthError, GitHubClientError)
        assert issubclass(GitHubNotFoundError, GitHubClientError)
        assert issubclass(GitHubRateLimitError, GitHubClientError)
        assert issubclass(GitHubConflictError, GitHubClientError)
        assert issubclass(GitHubServerError, GitHubClientError)
        assert issubclass(GitHubConnectionError, GitHubClientError)

    def test_not_found_message(self) -> None:
        resp = _mock_response(404)
        err = GitHubNotFoundError("/repos/a/b/pulls/999", resp)
        assert "not found" in str(err).lower()
        assert err.resource == "/repos/a/b/pulls/999"


# ===========================================================================
# Retry logic (@patch on both Session.request and time.sleep)
# ===========================================================================


class TestRetry:
    @pytest.fixture
    def client(self) -> GitHubClient:
        return GitHubClient(token="test-token", max_retries=2)

    @patch(PATCH_TARGET)
    @patch("time.sleep")
    def test_503_then_200(
        self,
        mock_sleep: MagicMock,
        mock_request: MagicMock,
        client: GitHubClient,
    ) -> None:
        mock_request.side_effect = [
            _mock_response(503),
            _mock_response(200, SAMPLE_PR),
        ]
        pr = client.get_pr("octocat", "Hello-World", 1)
        assert pr.title == "Fix login redirect"
        assert mock_request.call_count == 2

    @patch(PATCH_TARGET)
    @patch("time.sleep")
    def test_all_503_exhausted(
        self,
        mock_sleep: MagicMock,
        mock_request: MagicMock,
        client: GitHubClient,
    ) -> None:
        mock_request.return_value = _mock_response(503)
        with pytest.raises(GitHubServerError):
            client.get_pr("octocat", "Hello-World", 1)
        assert mock_request.call_count == 3  # 1 initial + 2 retries

    @patch(PATCH_TARGET)
    @patch("time.sleep")
    def test_connection_retried(
        self,
        mock_sleep: MagicMock,
        mock_request: MagicMock,
        client: GitHubClient,
    ) -> None:
        mock_request.side_effect = [
            requests.ConnectionError("reset"),
            _mock_response(200, SAMPLE_PR),
        ]
        pr = client.get_pr("octocat", "Hello-World", 1)
        assert pr.title == "Fix login redirect"
        assert mock_request.call_count == 2

    @patch(PATCH_TARGET)
    @patch("time.sleep")
    def test_connection_exhausted(
        self,
        mock_sleep: MagicMock,
        mock_request: MagicMock,
        client: GitHubClient,
    ) -> None:
        mock_request.side_effect = requests.ConnectionError("timeout")
        with pytest.raises(GitHubConnectionError):
            client.get_pr("octocat", "Hello-World", 1)
        assert mock_request.call_count == 3


# ===========================================================================
# Context manager (no HTTP mocking needed)
# ===========================================================================


class TestContextManager:
    def test_with_block(self) -> None:
        client = GitHubClient()
        with patch.object(client._session, "close") as mc:
            with client as c:
                assert c is client
        mc.assert_called_once()

    def test_close(self) -> None:
        client = GitHubClient()
        with patch.object(client._session, "close") as mc:
            client.close()
        mc.assert_called_once()


# ===========================================================================
# Integration: github_url + github_client (@patch)
# ===========================================================================


class TestIntegration:
    @patch(PATCH_TARGET)
    def test_parse_and_fetch(self, mock_request: MagicMock) -> None:
        from github_url import parse_pr_url

        parsed = parse_pr_url("https://github.com/octocat/Hello-World/pull/1")
        assert parsed.owner == "octocat"
        assert parsed.repo == "Hello-World"
        assert parsed.pull_number == 1

        mock_request.side_effect = [
            _mock_response(200, SAMPLE_PR),
            _mock_response(200, SAMPLE_FILES),
            _mock_response(200, text_data=SAMPLE_DIFF),
        ]

        client = GitHubClient(token="test-token", max_retries=0)
        data = client.review_pr(parsed.owner, parsed.repo, parsed.pull_number)

        assert data.pr.title == "Fix login redirect"
        assert data.files[0].filename == "src/auth.py"
        assert "diff --git" in data.diff
