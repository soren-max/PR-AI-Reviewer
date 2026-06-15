"""
GitHub API client for Pull Request data retrieval.

Fetches PR metadata, changed files, and unified diffs from the GitHub
REST API v3.  Built on the ``requests`` library with automatic retry,
rate-limit awareness, and a comprehensive error hierarchy.

Typical usage::

    >>> from github_client import GitHubClient
    >>> client = GitHubClient(token="ghp_...")

    >>> pr = client.get_pr("owner", "repo", 42)
    >>> pr.title
    'Fix login redirect'
    >>> pr.description
    'Updated the callback URL to use HTTPS...'

    >>> files = client.get_pr_files("owner", "repo", 42)
    >>> files[0].filename
    'src/auth.py'

    >>> diff = client.get_pr_diff("owner", "repo", 42)
    >>> len(diff)  # unified diff string
    2400

    >>> data = client.review_pr("owner", "repo", 42)
    >>> data.pr.title, data.files[0].filename, len(data.diff)
    ('Fix login redirect', 'src/auth.py', 2400)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar, Final, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GITHUB_API_BASE: Final[str] = "https://api.github.com"
_DEFAULT_TIMEOUT: Final[int] = 30
_MAX_RETRIES: Final[int] = 4
_RETRY_STATUSES: Final[tuple[int, ...]] = (429, 502, 503, 504)
_RETRY_BACKOFF: Final[list[float]] = [1.0, 2.0, 4.0, 8.0]

#: User-Agent sent with every request.  GitHub API requires a User-Agent.
_USER_AGENT: Final[str] = "ai-pr-review/0.1.0"

#: Accept header to request the raw unified diff (instead of JSON).
_ACCEPT_DIFF: Final[str] = "application/vnd.github.v3.diff"

#: Accept header for regular API responses.
_ACCEPT_JSON: Final[str] = "application/vnd.github.v3+json"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PRDetail:
    """Metadata about a single Pull Request.

    Attributes:
        title: PR title.
        description: PR body text (Markdown).
        author: GitHub login of the PR author.
        state: PR state (``"open"``, ``"closed"``, ``"merged"``).
        base_branch: Target branch (e.g. ``"main"``).
        head_branch: Source branch (e.g. ``"feat/login"``).
        base_sha: SHA of the base branch tip.
        head_sha: SHA of the head branch tip.
        mergeable: Whether the PR can be merged (``True`` / ``False`` / ``None``).
        changed_files: Number of files modified.
        additions: Lines added.
        deletions: Lines deleted.
        html_url: GitHub web URL for this PR.
        created_at: ISO-8601 timestamp.
        updated_at: ISO-8601 timestamp.
    """

    title: str
    description: str
    author: str
    state: str
    base_branch: str
    head_branch: str
    base_sha: str
    head_sha: str
    mergeable: bool | None
    changed_files: int
    additions: int
    deletions: int
    html_url: str
    created_at: str
    updated_at: str


@dataclass
class FileChange:
    """A single file modified in a Pull Request.

    Attributes:
        filename: Path relative to repo root (e.g. ``"src/auth.py"``).
        status: Change type (``"added"``, ``"modified"``, ``"deleted"``,
                ``"renamed"``, ``"copied"``, ``"changed"``, ``"unchanged"``).
        additions: Lines added.
        deletions: Lines deleted.
        changes: Total changed lines.
        patch: Unified diff string.  ``None`` for binary files or when the
               diff is too large.
        previous_filename: Previous filename (only for renames).
        raw_url: GitHub raw content URL for this version of the file.
        blob_url: GitHub blob URL for this version.
        contents_url: GitHub API URL for the file contents.
    """

    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None
    previous_filename: str | None = None
    raw_url: str | None = None
    blob_url: str | None = None
    contents_url: str | None = None

    @property
    def is_binary(self) -> bool:
        """``True`` when the file is binary (no patch available)."""
        return self.patch is None


@dataclass
class PRReviewData:
    """Aggregated data needed for an AI code review.

    This is the primary return type of
    :meth:`GitHubClient.review_pr` and bundles everything a review
    engine needs in one object.

    Attributes:
        pr: Pull Request metadata.
        files: List of changed files with patches.
        diff: Raw unified diff string for the entire PR.
    """

    pr: PRDetail
    files: list[FileChange]
    diff: str


@dataclass
class RateLimit:
    """Current GitHub API rate-limit status.

    Attributes:
        remaining: Requests remaining in the current window.
        limit: Maximum requests per window.
        reset_time: Unix timestamp when the window resets.
        used: Requests used in the current window.
    """

    remaining: int
    limit: int
    reset_time: int
    used: int

    @property
    def is_exhausted(self) -> bool:
        """``True`` if no requests remain in the current window."""
        return self.remaining <= 0

    @property
    def reset_in_seconds(self) -> float:
        """Seconds until the rate-limit window resets."""
        return max(0.0, float(self.reset_time - time.time()))


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class GitHubClientError(Exception):
    """Base exception for all GitHub API client errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code if applicable, else ``None``.
        response: The raw :class:`requests.Response` object if available,
                  else ``None``.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: requests.Response | None = None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class GitHubNotFoundError(GitHubClientError):
    """Resource not found (HTTP 404)."""

    def __init__(self, resource: str, response: requests.Response) -> None:
        self.resource = resource
        super().__init__(
            message=f"GitHub resource not found: {resource}",
            status_code=404,
            response=response,
        )


class GitHubAuthError(GitHubClientError):
    """Authentication failure (HTTP 401)."""

    def __init__(self, response: requests.Response) -> None:
        super().__init__(
            message="GitHub API authentication failed.  Check your token.",
            status_code=401,
            response=response,
        )


class GitHubRateLimitError(GitHubClientError):
    """Rate limit exceeded (HTTP 403 or 429).

    Attributes:
        rate_limit: The :class:`RateLimit` status at the time of failure.
        retry_after: Seconds to wait before retrying, if provided by the
                     server.
    """

    def __init__(
        self,
        response: requests.Response,
        rate_limit: RateLimit,
        retry_after: float | None = None,
    ) -> None:
        self.rate_limit = rate_limit
        self.retry_after = retry_after
        super().__init__(
            message=(
                f"GitHub API rate limit exceeded.  "
                f"{rate_limit.remaining}/{rate_limit.limit} remaining, "
                f"resets in {rate_limit.reset_in_seconds:.0f}s"
            ),
            status_code=response.status_code,
            response=response,
        )


class GitHubConflictError(GitHubClientError):
    """Conflict, typically merge conflicts (HTTP 409)."""

    def __init__(self, message: str, response: requests.Response) -> None:
        super().__init__(
            message=message,
            status_code=409,
            response=response,
        )


class GitHubServerError(GitHubClientError):
    """Server-side error (HTTP 5xx)."""

    def __init__(self, response: requests.Response) -> None:
        super().__init__(
            message=f"GitHub API server error: HTTP {response.status_code}",
            status_code=response.status_code,
            response=response,
        )


class GitHubConnectionError(GitHubClientError):
    """Network-level error (DNS, timeout, connection refused)."""

    def __init__(self, message: str, cause: Exception) -> None:
        self.__cause__ = cause
        super().__init__(message)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GitHubClient:
    """Synchronous client for the GitHub REST API v3.

    Handles authentication, automatic retry with exponential backoff,
    rate-limit tracking, and error mapping.

    Args:
        token: GitHub Personal Access Token.  Without a token, you are
               limited to 60 requests/hour.  With a token, 5000/hour.
        base_url: GitHub API base URL.  Override for GitHub Enterprise.
        timeout: Default request timeout in seconds.
        max_retries: Maximum number of retries for transient failures.
        retry_backoff: List of sleep durations (seconds) for each retry.
                       Must be the same length as ``max_retries``.

    Usage::

        >>> client = GitHubClient(token="ghp_...")
        >>> pr = client.get_pr("octocat", "Hello-World", 1)
        >>> pr.title
        'Updated README'
    """

    def __init__(
        self,
        token: str = "",
        *,
        base_url: str = _GITHUB_API_BASE,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        retry_backoff: list[float] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff or _RETRY_BACKOFF[:max_retries]

        # Build session with default headers
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": _ACCEPT_JSON,
                "User-Agent": _USER_AGENT,
                "Time-Zone": "UTC",
            }
        )
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

        # Internal rate-limit cache (updated on every response)
        self._rate_limit: RateLimit | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pr(self, owner: str, repo: str, pull_number: int) -> PRDetail:
        """Fetch Pull Request metadata.

        Calls ``GET /repos/{owner}/{repo}/pulls/{pull_number}``.

        Args:
            owner: Repository owner (user or organization).
            repo: Repository name.
            pull_number: Pull Request number.

        Returns:
            A :class:`PRDetail` with title, description, author, branches,
            and change statistics.

        Raises:
            GitHubNotFoundError: PR does not exist.
            GitHubAuthError: Invalid or missing token.
            GitHubRateLimitError: Rate limit exceeded.
            GitHubClientError: Other API or network errors.
        """
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        data = self._request("GET", path)

        # Map mergeable status (tri-state: True / False / None)
        mergeable = data.get("mergeable")
        if mergeable is not None:
            mergeable = bool(mergeable)

        return PRDetail(
            title=data.get("title", ""),
            description=data.get("body", "") or "",
            author=data.get("user", {}).get("login", "unknown"),
            state=data.get("state", "unknown"),
            base_branch=data.get("base", {}).get("ref", ""),
            head_branch=data.get("head", {}).get("ref", ""),
            base_sha=data.get("base", {}).get("sha", ""),
            head_sha=data.get("head", {}).get("sha", ""),
            mergeable=mergeable,
            changed_files=data.get("changed_files", 0),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            html_url=data.get("html_url", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def get_pr_files(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        *,
        page: int = 1,
        per_page: int = 100,
    ) -> list[FileChange]:
        """Fetch the list of files changed in a Pull Request.

        Calls ``GET /repos/{owner}/{repo}/pulls/{pull_number}/files``.
        Handles pagination automatically — if the PR has more files than
        ``per_page``, subsequent pages are fetched transparently.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull Request number.
            page: Page number to start from (default 1).
            per_page: Items per page (max 100, default 100).

        Returns:
            List of :class:`FileChange` objects.
        """
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        all_files: list[FileChange] = []
        current_page = page

        while True:
            data = self._request("GET", path, params={"page": current_page, "per_page": per_page})

            if not data:
                break  # No more pages

            for item in data:
                all_files.append(
                    FileChange(
                        filename=item.get("filename", ""),
                        status=item.get("status", "modified"),
                        additions=item.get("additions", 0),
                        deletions=item.get("deletions", 0),
                        changes=item.get("changes", 0),
                        patch=item.get("patch"),
                        previous_filename=item.get("previous_filename"),
                        raw_url=item.get("raw_url"),
                        blob_url=item.get("blob_url"),
                        contents_url=item.get("contents_url"),
                    )
                )

            # Check if there are more pages
            if len(data) < per_page:
                break
            current_page += 1

        return all_files

    def get_pr_diff(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> str:
        """Fetch the raw unified diff for a Pull Request.

        Calls ``GET /repos/{owner}/{repo}/pulls/{pull_number}`` with
        the ``application/vnd.github.v3.diff`` accept header, which
        returns the raw diff text instead of JSON.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull Request number.

        Returns:
            Raw unified diff as a string.  Empty string for PRs with
            no changes (should not happen in practice).

        Raises:
            Same as :meth:`get_pr`.
        """
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        return self._request_raw("GET", path, accept=_ACCEPT_DIFF)

    def review_pr(
        self,
        owner: str,
        repo: str,
        pull_number: int,
    ) -> PRReviewData:
        """Fetch all data needed for a code review in one call.

        This is a convenience method that calls :meth:`get_pr`,
        :meth:`get_pr_files`, and :meth:`get_pr_diff` sequentially
        and bundles the results.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pull_number: Pull Request number.

        Returns:
            A :class:`PRReviewData` with metadata, file changes, and
            the unified diff.
        """
        pr = self.get_pr(owner, repo, pull_number)
        files = self.get_pr_files(owner, repo, pull_number)
        diff = self.get_pr_diff(owner, repo, pull_number)
        return PRReviewData(pr=pr, files=files, diff=diff)

    @property
    def rate_limit(self) -> RateLimit | None:
        """The most recently observed rate-limit status.

        Returns ``None`` until the first API call is made.
        """
        return self._rate_limit

    # ------------------------------------------------------------------
    # Internal: request machinery
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Make a JSON-expecting API request with retry logic.

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, etc.).
            path: API path (e.g. ``"/repos/owner/repo/pulls/42"``).
            **kwargs: Extra arguments passed to ``requests.Session.request``.

        Returns:
            Parsed JSON response body (dict or list).
        """
        response = self._send_with_retry(method, path, **kwargs)
        return response.json()

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        accept: str = _ACCEPT_JSON,
        **kwargs: Any,
    ) -> str:
        """Make an API request and return the raw text response body.

        Args:
            method: HTTP method.
            path: API path.
            accept: Custom ``Accept`` header value.
            **kwargs: Extra arguments for the request.

        Returns:
            Raw response text.
        """
        headers = kwargs.pop("headers", {})
        headers["Accept"] = accept
        response = self._send_with_retry(method, path, headers=headers, **kwargs)
        return response.text

    def _send_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Send an HTTP request with automatic retry on transient failures.

        Retryable statuses: 429, 502, 503, 504 (configured in
        ``_RETRY_STATUSES``).  Network-level errors (timeout, DNS) are
        also retried.

        Args:
            method: HTTP method.
            path: API path.
            **kwargs: Extra arguments forwarded to ``requests.Session.request``.

        Returns:
            The final :class:`requests.Response` on success.

        Raises:
            GitHubClientError: Subclass depending on the error type.
        """
        url = urljoin(self._base_url, path)

        # Merge in our defaults, then let kwargs override
        request_kwargs: dict[str, Any] = {
            "timeout": self._timeout,
        }
        request_kwargs.update(kwargs)

        last_exception: Exception | None = None

        for attempt in range(1 + self._max_retries):
            try:
                response = self._session.request(method, url, **request_kwargs)

                # Always track rate-limit headers
                self._update_rate_limit(response)

                # Success (2xx)
                if response.status_code < 300:
                    return response

                # Map error statuses
                self._raise_for_status(response)

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exception = exc
                logger.warning(
                    "Network error on %s %s (attempt %d/%d): %s",
                    method, url, attempt + 1, 1 + self._max_retries, exc,
                )
                # For network errors, we only retry if we have attempts left.
                if attempt < self._max_retries:
                    self._sleep(attempt, f"Network error on {path}")
                    continue
                raise GitHubConnectionError(
                    f"Request failed after {self._max_retries} retries: {exc}",
                    cause=exc,
                ) from exc

            except GitHubRateLimitError as exc:
                # Rate limit: wait for reset if we can, then retry
                last_exception = exc
                if attempt < self._max_retries:
                    wait = max(exc.rate_limit.reset_in_seconds, self._retry_backoff[attempt])
                    logger.warning(
                        "Rate limited on %s, waiting %.0fs (attempt %d/%d)",
                        path, wait, attempt + 1, 1 + self._max_retries,
                    )
                    time.sleep(min(wait, 60))  # Cap wait at 60s
                    continue
                raise

            except (GitHubServerError, GitHubConflictError) as exc:
                # Transient server errors — retry
                last_exception = exc
                if attempt < self._max_retries:
                    logger.warning(
                        "Server error on %s %s (attempt %d/%d): HTTP %d",
                        method, path, attempt + 1, 1 + self._max_retries,
                        exc.status_code,
                    )
                    self._sleep(attempt, f"Server error on {path}")
                    continue
                raise

        # Should not reach here, but just in case
        raise GitHubClientError(
            f"Request failed after {self._max_retries} retries",
            response=getattr(last_exception, "response", None) if isinstance(last_exception, GitHubClientError) else None,
        )

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _update_rate_limit(self, response: requests.Response) -> None:
        """Parse rate-limit headers from the response and cache them."""
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        reset = response.headers.get("X-RateLimit-Reset")
        used = response.headers.get("X-RateLimit-Used")

        if remaining is not None and limit is not None and reset is not None:
            self._rate_limit = RateLimit(
                remaining=int(remaining),
                limit=int(limit),
                reset_time=int(reset),
                used=int(used) if used else 0,
            )

    def _raise_for_status(self, response: requests.Response) -> None:
        """Map an HTTP status code to the appropriate exception.

        Only called for non-2xx responses.  Raises immediately for
        non-retryable errors; returns for retryable errors so the caller
        can decide.
        """
        status = response.status_code

        if status == 401:
            raise GitHubAuthError(response)
        if status == 404:
            resource = response.request.path_url if response.request else "unknown"
            raise GitHubNotFoundError(resource, response)
        if status in (403, 429):
            retry_after = response.headers.get("Retry-After")
            retry_after_secs = float(retry_after) if retry_after else None
            rate_limit = self._rate_limit or RateLimit(remaining=0, limit=5000, reset_time=0, used=0)
            raise GitHubRateLimitError(
                response,
                rate_limit=rate_limit,
                retry_after=retry_after_secs,
            )
        if status == 409:
            body = response.json() if response.text else {}
            message = body.get("message", "Merge conflict")
            raise GitHubConflictError(message, response)
        if 500 <= status < 600:
            raise GitHubServerError(response)

        # Fallback for other statuses
        response.raise_for_status()

    def _sleep(self, attempt: int, reason: str) -> None:
        """Sleep with exponential backoff, capped at the configured value."""
        delay = self._retry_backoff[attempt] if attempt < len(self._retry_backoff) else 8.0
        logger.debug("Retry %d/%d: %s — sleeping %.1fs", attempt + 1, self._max_retries, reason, delay)
        time.sleep(delay)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session and release connections."""
        self._session.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
