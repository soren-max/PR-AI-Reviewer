"""
Unit tests for GitHubService.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.github import GitHubService, parse_pr_url
from app.core.exceptions import InvalidPRUrlError, PRNotFoundError


class TestParsePRUrl:
    def test_valid_url(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/42")
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.pr_number == 42

    def test_valid_url_with_trailing_slash(self):
        result = parse_pr_url("https://github.com/owner/repo/pull/42/")
        assert result.pr_number == 42

    def test_invalid_url_not_github(self):
        with pytest.raises(InvalidPRUrlError):
            parse_pr_url("https://gitlab.com/owner/repo/merge_requests/1")

    def test_invalid_url_not_pr(self):
        with pytest.raises(InvalidPRUrlError):
            parse_pr_url("https://github.com/owner/repo/issues/1")

    def test_invalid_url_garbage(self):
        with pytest.raises(InvalidPRUrlError):
            parse_pr_url("not a url at all")


class TestGitHubService:
    @pytest.mark.asyncio
    async def test_verify_pr_exists_success(self):
        service = GitHubService()
        with patch.object(service._client, "get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json = AsyncMock(return_value={"id": 1})
            result = await service.verify_pr_exists("owner", "repo", 1)
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_pr_not_found(self):
        service = GitHubService()
        with patch.object(service._client, "get") as mock_get:
            mock_get.return_value.status_code = 404
            with pytest.raises(PRNotFoundError):
                await service.verify_pr_exists("owner", "repo", 999)

    @pytest.mark.asyncio
    async def test_fetch_pr_metadata_success(self):
        service = GitHubService()
        mock_response = {
            "title": "Add feature",
            "user": {"login": "octocat"},
            "base": {"ref": "main"},
            "head": {"ref": "feat/feature"},
            "changed_files": 5,
            "additions": 100,
            "deletions": 20,
        }
        with patch.object(service._client, "get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json = AsyncMock(return_value=mock_response)
            meta = await service.fetch_pr_metadata("owner", "repo", 1)
            assert meta.title == "Add feature"
            assert meta.author == "octocat"
            assert meta.additions == 100

    @pytest.mark.asyncio
    async def test_fetch_pr_diff_skips_binary(self):
        service = GitHubService()
        mock_files = [
            {"filename": "image.png", "status": "added", "additions": 1, "deletions": 0, "patch": None},
            {"filename": "src/app.py", "status": "modified", "additions": 10, "deletions": 5, "patch": "diff --git a/src/app.py b/src/app.py\nindex abc..def\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1,3 +1,5 @@"},
        ]
        with patch.object(service._client, "get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json = AsyncMock(return_value=mock_files)
            diffs = await service.fetch_pr_diff("owner", "repo", 1)
            assert len(diffs) == 2
            assert diffs[0].is_binary is True
            assert diffs[0].patch is None
            assert diffs[1].is_binary is False
            assert diffs[1].patch is not None
