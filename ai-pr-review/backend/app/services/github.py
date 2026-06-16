"""
GitHub API client — fetches PR metadata and unified diffs.
"""
import re
import inspect
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import GitHubAPIError, InvalidPRUrlError, PRNotFoundError
from app.core.logging import setup_logging

logger = setup_logging(__name__)

PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)/pull/(?P<number>\d+)/?$"
)


@dataclass(frozen=True)
class ParsedPR:
    """Result of parsing a GitHub PR URL."""

    owner: str
    repo: str
    pr_number: int


@dataclass(init=False)
class PRMetadata:
    """PR metadata from GitHub API."""

    title: str = ""
    description: str = ""
    author: str = ""
    base_branch: str = ""
    head_branch: str = ""
    changed_files_count: int = 0
    additions: int = 0
    deletions: int = 0

    def __init__(
        self,
        title: str = "",
        description: str = "",
        author: str = "",
        base_branch: str = "",
        head_branch: str = "",
        changed_files_count: int = 0,
        additions: int = 0,
        deletions: int = 0,
        changed_files: int | None = None,
    ) -> None:
        self.title = title
        self.description = description
        self.author = author
        self.base_branch = base_branch
        self.head_branch = head_branch
        self.changed_files_count = changed_files_count if changed_files is None else changed_files
        self.additions = additions
        self.deletions = deletions


@dataclass
class FileDiff:
    """A single file's change information."""

    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    patch: str | None  # unified diff text; None for binary/too-large
    is_binary: bool = False


def _normalize_file_status(status: str) -> str:
    """Normalize GitHub file status names to the app's domain names."""
    if status == "removed":
        return "deleted"
    return status or "modified"


async def _json_from_response(resp: httpx.Response) -> object:
    """Return response JSON, tolerating AsyncMock-based test doubles."""
    data = resp.json()
    if inspect.isawaitable(data):
        return await data
    return data


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
                detail=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
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
        data = await _json_from_response(resp)
        if not isinstance(data, dict):
            raise GitHubAPIError("GitHub API returned malformed PR metadata", status_code=502)

        return PRMetadata(
            title=data.get("title", ""),
            description=data.get("body") or "",
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
        binary_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
            ".woff", ".woff2", ".ttf", ".eot",
            ".pdf", ".zip", ".tar", ".gz",
            ".mp4", ".avi", ".mov",
        }

        diffs: list[FileDiff] = []
        page = 1
        per_page = 100

        while True:
            resp = await self._client.get(
                url,
                params={"per_page": per_page, "page": page},
            )
            if resp.status_code == 404:
                raise PRNotFoundError(f"PR {owner}/{repo}#{number} not found")
            if resp.status_code != 200:
                raise GitHubAPIError(
                    detail=f"GitHub API returned {resp.status_code}: {resp.text[:200]}",
                    status_code=502,
                )

            page_items = await _json_from_response(resp)
            if not isinstance(page_items, list):
                raise GitHubAPIError("GitHub API returned malformed PR file list", status_code=502)

            for item in page_items:
                if not isinstance(item, dict):
                    continue
                diffs.append(self._to_file_diff(item, binary_extensions))

            if len(page_items) < per_page:
                break
            page += 1

        logger.info(
            "Fetched %d changed files from GitHub PR %s/%s#%d",
            len(diffs), owner, repo, number,
        )
        return diffs

    def _to_file_diff(self, item: dict, binary_extensions: set[str]) -> FileDiff:
        """Convert one GitHub file payload into a FileDiff."""
        filename = item.get("filename", "")
        ext = filename[filename.rfind("."):].lower() if "." in filename else ""
        status = _normalize_file_status(str(item.get("status", "modified")))
        patch = item.get("patch")
        is_binary = ext in binary_extensions or patch is None

        if is_binary:
            patch = None
        elif len(patch) > settings.MAX_DIFF_SIZE_BYTES:
            patch = patch[: settings.MAX_DIFF_SIZE_BYTES] + "\n... [diff truncated]"

        return FileDiff(
            filename=filename,
            status=status,
            additions=item.get("additions", 0),
            deletions=item.get("deletions", 0),
            patch=patch,
            is_binary=is_binary,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
