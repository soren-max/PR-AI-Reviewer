"""
GitHub Pull Request URL parsing module.

Provides a pure, side-effect-free parser that extracts ``owner``, ``repo``,
and ``pull_number`` from GitHub Pull Request URLs.  All edge cases are
handled deterministically — no HTTP calls, no I/O, no external state.

Typical usage::

    >>> from github_url import parse_pr_url
    >>> result = parse_pr_url("https://github.com/owner/repo/pull/42")
    >>> result.owner, result.repo, result.pull_number
    ('owner', 'repo', 42)

Raises :exc:`PRUrlParseError` (or one of its subclasses) when the input
cannot be parsed as a valid GitHub Pull Request URL.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Final, Pattern

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Regex that matches a canonical GitHub PR URL.
#: Captures owner, repo, and pull number.
#: Matches:
#:   - Standard URL: https://github.com/owner/repo/pull/123
#:   - With www:     https://www.github.com/owner/repo/pull/123
#:   - Trailing /:   https://github.com/owner/repo/pull/123/
#: Does NOT match:
#:   - Non-GitHub hosts (gitlab.com, bitbucket.org, etc.)
#:   - Issues, trees, blobs, or other non-PR paths
_CANONICAL_PR_RE: Final[Pattern[str]] = re.compile(
    r"^https://(?:www\.)?github\.com/"
    r"(?P<owner>[\w.\-]+)/"
    r"(?P<repo>[\w.\-]+)/"
    r"pull/"
    r"(?P<pr_number>\d+)"
    r"/?(?:\?.*)?(?:#.*)?$"
)

#: Fallback regex for URLs with query parameters or fragments that the
#: canonical regex might reject due to extra path segments.
_FALLBACK_PR_RE: Final[Pattern[str]] = re.compile(
    r"^https://(?:www\.)?github\.com/"
    r"(?P<owner>[\w.\-]+)/"
    r"(?P<repo>[\w.\-]+)/"
    r"pull/"
    r"(?P<pr_number>\d+)"
)

#: GitHub owner naming rules:
#:   - Alphanumeric, hyphens, dots, underscores
#:   - Must start and end with alphanumeric
#:   - Max 39 characters
#:   - Single-character names are allowed (e.g. ``a``)
_OWNER_RE: Final[Pattern[str]] = re.compile(r"^[a-zA-Z0-9](?:[\w.\-]{0,37}[a-zA-Z0-9])?$")

#: GitHub repo naming rules:
#:   - Alphanumeric, hyphens, dots, underscores
#:   - Max 100 characters
_REPO_RE: Final[Pattern[str]] = re.compile(r"^[\w.\-]{1,100}$")

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class PRUrlParseError(ValueError):
    """Base exception for all PR URL parsing failures."""

    def __init__(self, message: str, url: str) -> None:
        self.url = url
        super().__init__(message)


class InvalidGitHubURLError(PRUrlParseError):
    """Raised when the URL does not point to github.com."""

    def __init__(self, url: str) -> None:
        super().__init__(
            f"URL is not a valid GitHub.com URL: {url!r}",
            url=url,
        )


class NotAPullRequestURLError(PRUrlParseError):
    """Raised when the URL does not match the /pull/N path pattern."""

    def __init__(self, url: str) -> None:
        super().__init__(
            f"URL does not point to a GitHub Pull Request: {url!r}. "
            f"Expected pattern: https://github.com/{{owner}}/{{repo}}/pull/{{number}}",
            url=url,
        )


class InvalidOwnerError(PRUrlParseError):
    """Raised when the owner segment violates GitHub naming rules."""

    def __init__(self, owner: str, url: str) -> None:
        super().__init__(
            f"Invalid GitHub owner name: {owner!r}. "
            f"Owner must be 1-39 alphanumeric characters, hyphens, dots, "
            f"or underscores, and must start/end with alphanumeric.",
            url=url,
        )


class InvalidRepoError(PRUrlParseError):
    """Raised when the repo segment violates GitHub naming rules."""

    def __init__(self, repo: str, url: str) -> None:
        super().__init__(
            f"Invalid GitHub repository name: {repo!r}. "
            f"Repo must be 1-100 alphanumeric characters, hyphens, dots, "
            f"or underscores.",
            url=url,
        )


class InvalidPullNumberError(PRUrlParseError):
    """Raised when the PR number is not a positive integer."""

    def __init__(self, raw: str, url: str) -> None:
        super().__init__(
            f"Invalid Pull Request number: {raw!r}. "
            f"PR number must be a positive integer.",
            url=url,
        )


# ---------------------------------------------------------------------------
# Value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedPRUrl:
    """Immutable result of a successful PR URL parse.

    Attributes:
        owner: GitHub repository owner (user or organization).
        repo: GitHub repository name.
        pull_number: Pull Request number (positive integer).
        raw_url: The original URL that was parsed (for traceability).
    """

    owner: str
    repo: str
    pull_number: int
    raw_url: str

    def __post_init__(self) -> None:
        """Validate invariants on construction."""
        if self.pull_number < 1:
            raise InvalidPullNumberError(str(self.pull_number), self.raw_url)

    @property
    def api_path(self) -> str:
        """Return the GitHub API v3 path for this PR.

        Example::

            >>> p = ParsedPRUrl("owner", "repo", 42, "https://...")
            >>> p.api_path
            '/repos/owner/repo/pulls/42'
        """
        return f"/repos/{self.owner}/{self.repo}/pulls/{self.pull_number}"

    @property
    def clone_url(self) -> str:
        """Return the HTTPS clone URL for the repository.

        Example::

            >>> p = ParsedPRUrl("owner", "repo", 42, "https://...")
            >>> p.clone_url
            'https://github.com/owner/repo.git'
        """
        return f"https://github.com/{self.owner}/{self.repo}.git"

    def to_dict(self) -> dict[str, str | int]:
        """Serialize to a plain dictionary.

        Example::

            >>> p = ParsedPRUrl("owner", "repo", 42, "https://...")
            >>> p.to_dict()
            {'owner': 'owner', 'repo': 'repo', 'pull_number': 42}
        """
        return {
            "owner": self.owner,
            "repo": self.repo,
            "pull_number": self.pull_number,
        }


# ---------------------------------------------------------------------------
# Primary public API
# ---------------------------------------------------------------------------


def parse_pr_url(url: str, *, strict: bool = True) -> ParsedPRUrl:
    """Parse a GitHub Pull Request URL into its component parts.

    This function is **pure** — it performs no network I/O and has no
    side effects.  All URL normalization and validation is done locally.

    Args:
        url: A GitHub Pull Request URL.
             Examples:
               - ``https://github.com/owner/repo/pull/123``
               - ``https://www.github.com/owner/repo/pull/123/``
               - ``https://github.com/owner/repo/pull/123?diff=unified``
               - ``https://github.com/owner/repo/pull/123#issuecomment-1``

        strict:
            If ``True`` (default), validate that the owner and repository
            names conform to GitHub's naming rules.  Set to ``False`` to
            skip validation — useful when parsing URLs from trusted sources
            or when you only need the raw segments.

    Returns:
        A :class:`ParsedPRUrl` with ``owner``, ``repo``, ``pull_number``,
        and the original ``raw_url``.

    Raises:
        InvalidGitHubURLError: The URL does not point to github.com.
        NotAPullRequestURLError: The URL does not match ``/pull/N``.
        InvalidOwnerError: The owner name is invalid (only in strict mode).
        InvalidRepoError: The repository name is invalid (only in strict mode).
        InvalidPullNumberError: The PR number is not a positive integer.

    Examples:
        **Standard URL** — the most common case::

            >>> result = parse_pr_url("https://github.com/owner/repo/pull/42")
            >>> result.owner
            'owner'
            >>> result.repo
            'repo'
            >>> result.pull_number
            42

        **With trailing slash, query params, and fragments** — all are
        automatically stripped::

            >>> result = parse_pr_url(
            ...     "https://github.com/owner/repo/pull/42?diff=split#top"
            ... )
            >>> result.pull_number
            42

        **Invalid URL** — raises with a descriptive message::

            >>> parse_pr_url("https://gitlab.com/owner/repo/merge_requests/1")
            Traceback (most recent call last):
            ...
            InvalidGitHubURLError: URL is not a valid GitHub.com URL: ...
    """
    url = url.strip()

    # ------------------------------------------------------------------
    # Step 1: Normalise the URL
    # ------------------------------------------------------------------
    # Strip whitespace, query strings, and fragments.  This gives us a
    # clean path we can match against the canonical pattern.
    logger.debug("Parsing PR URL: %r", url)

    # ------------------------------------------------------------------
    # Step 2: Match the canonical pattern
    # ------------------------------------------------------------------
    match = _CANONICAL_PR_RE.match(url)
    if not match:
        # Attempt a more lenient fallback that extracts owner/repo/number
        # even when extra path segments or unusual formatting is present.
        match = _FALLBACK_PR_RE.match(url)

    if not match:
        # Determine whether this is even a github.com URL for a better
        # error message.
        if "github.com" not in url:
            raise InvalidGitHubURLError(url)
        raise NotAPullRequestURLError(url)

    owner: str = match.group("owner")
    repo: str = match.group("repo")
    raw_number: str = match.group("pr_number")

    # ------------------------------------------------------------------
    # Step 3: Validate the pull number
    # ------------------------------------------------------------------
    try:
        pr_number = int(raw_number)
    except ValueError as exc:
        raise InvalidPullNumberError(raw_number, url) from exc

    if pr_number < 1:
        raise InvalidPullNumberError(raw_number, url)

    # ------------------------------------------------------------------
    # Step 4: Optionally validate owner / repo naming rules
    # ------------------------------------------------------------------
    if strict:
        if not _OWNER_RE.match(owner):
            raise InvalidOwnerError(owner, url)
        if not _REPO_RE.match(repo):
            raise InvalidRepoError(repo, url)

    # ------------------------------------------------------------------
    # Step 5: Construct result
    # ------------------------------------------------------------------
    result = ParsedPRUrl(owner=owner, repo=repo, pull_number=pr_number, raw_url=url)

    logger.debug("Parsed PR URL: owner=%r repo=%r pull_number=%d", owner, repo, pr_number)
    return result


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def is_valid_pr_url(url: str) -> bool:
    """Check whether a string is a valid GitHub PR URL (without raising).

    This is a convenience wrapper around :func:`parse_pr_url` that returns
    a boolean instead of raising exceptions.

    Args:
        url: The URL to check.

    Returns:
        ``True`` if the URL can be parsed as a valid GitHub PR URL,
        ``False`` otherwise.

    Example::

        >>> is_valid_pr_url("https://github.com/owner/repo/pull/42")
        True
        >>> is_valid_pr_url("not-a-url")
        False
    """
    try:
        parse_pr_url(url)
        return True
    except PRUrlParseError:
        return False
