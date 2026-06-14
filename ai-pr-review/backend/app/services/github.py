"""
GitHub API client — fetches PR metadata and unified diffs.
"""
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import GitHubAPIError, InvalidPRUrlError, PRNotFoundError

PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/pull/(?P<number>\d+)/?$"
)


@dataclass(frozen=True)
class ParsedPR:
    """Result of parsing a GitHub PR URL."""

    owner: str
    repo: str
    pr_number: int


@dataclass
class PRMetadata:
    """PR metadata from GitHub API."""

    title: str
    author: str
    base_branch: str
    head_branch: str
    changed_files_count: int
    additions: int
    deletions: int


@dataclass
class FileDiff:
    """A single file's change information."""

    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    patch: str | None  # unified diff text; None for binary/too-large
    is_binary: bool = False


def parse_pr_url(url: str) -> ParsedPR:
    """
    Parse a GitHub PR URL into its components.

    Raises InvalidPRUrlError if the URL is malformed.
    """
    clean = url.strip().split("?")[0].split("#")[0]
    m = PR_URL_RE.match(clean)
    if not m:
        raise InvalidPRUrlError()
    return ParsedPR(
        owner=m.group("owner"),
        repo=m.group("repo"),
        pr_number=int(m.group("number")),
    )


class GitHubService:
    """
    Client for GitHub REST API.

    Handles authentication, rate limiting awareness, and error mapping.
    """

    def __init__(self):
        self._base_url = settings.GITHUB_API_BASE.rstrip("/")
        self._timeout = settings.GITHUB_REQUEST_TIMEOUT
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": settings.APP_NAME,
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
        )

    async def verify_pr_exists(self, owner: str, repo: str, number: int) -> None:
        """Verify that a PR exists; raises PRNotFoundError if not."""
        url = f"/repos/{owner}/{repo}/pulls/{number}"
        resp = await self._client.get(url)
        if resp.status_code == 404:
            raise PRNotFoundError(f"PR {owner}/{repo}#{number} not found on GitHub")
        if resp.status_code != 200:
            raise GitHubAPIError(
                detail=f"GitHub API returned {resp.status_code}",
                status_code=502,
            )

    async def fetch_pr_metadata(self, owner: str, repo: str, number: int) -> PRMetadata:
        """Fetch PR metadata from GitHub API."""
        url = f"/repos/{owner}/{repo}/pulls/{number}"
        resp = await self._client.get(url)
        if resp.status_code == 404:
            raise PRNotFoundError(f"PR {owner}/{repo}#{number} not found")
        if resp.status_code != 200:
            raise GitHubAPIError(
                detail=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
                status_code=502,
            )
        data = resp.json()
        return PRMetadata(
            title=data.get("title", ""),
            author=data.get("user", {}).get("login", "unknown"),
            base_branch=data.get("base", {}).get("ref", ""),
            head_branch=data.get("head", {}).get("ref", ""),
            changed_files_count=data.get("changed_files", 0),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
        )

    async def fetch_pr_diff(self, owner: str, repo: str, number: int) -> list[FileDiff]:
        """Fetch changed files with patch (unified diff) for a PR."""
        url = f"/repos/{owner}/{repo}/pulls/{number}/files"
        resp = await self._client.get(url)
        if resp.status_code == 404:
            raise PRNotFoundError(f"PR {owner}/{repo}#{number} not found")
        if resp.status_code != 200:
            raise GitHubAPIError(
                detail=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
                status_code=502,
            )

        binary_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
            ".woff", ".woff2", ".ttf", ".eot",
            ".pdf", ".zip", ".tar", ".gz",
            ".mp4", ".avi", ".mov",
        }

        diffs: list[FileDiff] = []
        for item in resp.json():
            filename = item.get("filename", "")
            ext = filename[filename.rfind("."):].lower() if "." in filename else ""
            is_binary = ext in binary_extensions or item.get("patch") is None or item.get("status") == "removed"

            patch = item.get("patch") if not is_binary else None
            total_patch_size = len(patch or "")

            # Truncate overly large diffs
            if total_patch_size > settings.MAX_DIFF_SIZE_BYTES:
                patch = patch[: settings.MAX_DIFF_SIZE_BYTES] + "\n... [diff truncated]"

            diffs.append(
                FileDiff(
                    filename=filename,
                    status=item.get("status", "modified"),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    patch=patch,
                    is_binary=is_binary,
                )
            )
        return diffs

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
