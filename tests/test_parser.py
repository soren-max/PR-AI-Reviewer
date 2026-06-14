"""
Tests for ``github_url.py`` — PR URL parser.

Covers 100% of the module's public API:
  - :func:`parse_pr_url` — success paths, error paths, strict/lenient modes
  - :func:`is_valid_pr_url` — boolean helper
  - :class:`ParsedPRUrl` — properties, immutability, serialization
  - All custom exception types
"""
from __future__ import annotations

import pytest
from github_url import (
    ParsedPRUrl,
    InvalidGitHubURLError,
    NotAPullRequestURLError,
    InvalidOwnerError,
    InvalidRepoError,
    InvalidPullNumberError,
    PRUrlParseError,
    parse_pr_url,
    is_valid_pr_url,
)


# ===========================================================================
# Success paths — parse_pr_url()
# ===========================================================================


class TestParseSuccess:
    """All valid URL forms should parse correctly."""

    @pytest.mark.parametrize(
        ("url", "owner", "repo", "pr_number"),
        [
            ("https://github.com/owner/repo/pull/42", "owner", "repo", 42),
            ("https://www.github.com/my-org/my-repo/pull/1", "my-org", "my-repo", 1),
            ("https://github.com/a/b/pull/1", "a", "b", 1),
        ],
    )
    def test_standard_urls(self, url: str, owner: str, repo: str, pr_number: int) -> None:
        result = parse_pr_url(url)
        assert result.owner == owner
        assert result.repo == repo
        assert result.pull_number == pr_number
        assert result.raw_url == url

    def test_trailing_slash(self) -> None:
        result = parse_pr_url("https://github.com/owner/repo/pull/42/")
        assert result.pull_number == 42

    def test_query_params(self) -> None:
        result = parse_pr_url("https://github.com/owner/repo/pull/42?diff=unified")
        assert result.pull_number == 42

    def test_fragment(self) -> None:
        result = parse_pr_url("https://github.com/owner/repo/pull/42#top")
        assert result.pull_number == 42

    def test_query_and_fragment(self) -> None:
        result = parse_pr_url("https://github.com/owner/repo/pull/42?w=1#top")
        assert result.pull_number == 42

    def test_whitespace_stripping(self) -> None:
        result = parse_pr_url("  https://github.com/a/b/pull/99  ")
        assert result.pull_number == 99

    def test_edge_pull_numbers(self) -> None:
        assert parse_pr_url("https://github.com/a/b/pull/1").pull_number == 1
        assert parse_pr_url("https://github.com/a/b/pull/99999").pull_number == 99999

    def test_special_chars_in_names(self) -> None:
        assert parse_pr_url("https://github.com/my.org/repo/pull/1").owner == "my.org"
        assert parse_pr_url("https://github.com/my-org/repo/pull/1").owner == "my-org"
        assert parse_pr_url("https://github.com/my_org/repo/pull/1").owner == "my_org"
        assert parse_pr_url("https://github.com/owner/my.repo/pull/1").repo == "my.repo"


# ===========================================================================
# Error paths — parse_pr_url()
# ===========================================================================


class TestParseErrors:
    """All invalid inputs should raise appropriate exceptions."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://gitlab.com/owner/repo/issues/1",
            "https://bitbucket.org/owner/repo/pull-requests/1",
            "not-a-url",
            "",
            "   ",
        ],
    )
    def test_invalid_github_url(self, url: str) -> None:
        with pytest.raises(InvalidGitHubURLError):
            parse_pr_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/owner/repo/issues/1",
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo/",
            "https://github.com/owner/pull/1",
        ],
    )
    def test_not_a_pr(self, url: str) -> None:
        with pytest.raises(NotAPullRequestURLError):
            parse_pr_url(url)

    @pytest.mark.parametrize("url", ["https://github.com/a/b/pull/abc", "https://github.com/a/b/pull/1a2b"])
    def test_non_numeric_pr_number(self, url: str) -> None:
        with pytest.raises(NotAPullRequestURLError):
            parse_pr_url(url)

    def test_zero_pr_number(self) -> None:
        with pytest.raises(InvalidPullNumberError):
            parse_pr_url("https://github.com/a/b/pull/0")


# ===========================================================================
# Strict vs lenient mode
# ===========================================================================


class TestStrictMode:
    def test_strict_rejects_hyphen_prefix(self) -> None:
        with pytest.raises(InvalidOwnerError):
            parse_pr_url("https://github.com/-owner/repo/pull/1", strict=True)

    def test_strict_rejects_hyphen_suffix(self) -> None:
        with pytest.raises(InvalidOwnerError):
            parse_pr_url("https://github.com/owner-/repo/pull/1", strict=True)

    def test_strict_rejects_long_owner(self) -> None:
        long_owner = "a" * 40
        with pytest.raises(InvalidOwnerError):
            parse_pr_url(f"https://github.com/{long_owner}/repo/pull/1", strict=True)

    def test_strict_rejects_long_repo(self) -> None:
        long_repo = "b" * 101
        with pytest.raises(InvalidRepoError):
            parse_pr_url(f"https://github.com/a/{long_repo}/pull/1", strict=True)

    def test_lenient_accepts_hyphen_prefix(self) -> None:
        result = parse_pr_url("https://github.com/-my-org/repo/pull/1", strict=False)
        assert result.owner == "-my-org"

    def test_lenient_accepts_long_names(self) -> None:
        result = parse_pr_url(
            f"https://github.com/{'a'*50}/{'b'*50}/pull/1", strict=False
        )
        assert len(result.owner) == 50
        assert len(result.repo) == 50

    def test_default_is_strict(self) -> None:
        with pytest.raises(InvalidOwnerError):
            parse_pr_url("https://github.com/-owner/repo/pull/1")


# ===========================================================================
# is_valid_pr_url()
# ===========================================================================


class TestIsValid:
    def test_valid_urls(self) -> None:
        assert is_valid_pr_url("https://github.com/a/b/pull/1") is True
        assert is_valid_pr_url("https://github.com/a/b/pull/42/") is True

    def test_invalid_urls(self) -> None:
        assert is_valid_pr_url("not-a-url") is False
        assert is_valid_pr_url("https://gitlab.com/a/b") is False
        assert is_valid_pr_url("") is False

    def test_never_raises(self) -> None:
        """Should return bool, never raise exception."""
        bad_inputs = ["", "invalid", "https://github.com/a/b/pull/abc"]
        for inp in bad_inputs:
            result = is_valid_pr_url(inp)
            assert isinstance(result, bool)
            assert result is False


# ===========================================================================
# ParsedPRUrl dataclass
# ===========================================================================


class TestParsedPRUrl:
    def test_frozen(self) -> None:
        p = ParsedPRUrl("a", "b", 1, "https://github.com/a/b/pull/1")
        with pytest.raises(AttributeError):
            p.owner = "new"  # type: ignore[misc]

    def test_equality(self) -> None:
        p1 = ParsedPRUrl("a", "b", 1, "url")
        p2 = ParsedPRUrl("a", "b", 1, "url")
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_post_init_rejects_zero(self) -> None:
        with pytest.raises(InvalidPullNumberError):
            ParsedPRUrl("a", "b", 0, "url")

    def test_post_init_rejects_negative(self) -> None:
        with pytest.raises(InvalidPullNumberError):
            ParsedPRUrl("a", "b", -1, "url")

    def test_api_path(self) -> None:
        p = ParsedPRUrl("my-org", "my-repo", 42, "url")
        assert p.api_path == "/repos/my-org/my-repo/pulls/42"

    def test_clone_url(self) -> None:
        p = ParsedPRUrl("my-org", "my-repo", 42, "url")
        assert p.clone_url == "https://github.com/my-org/my-repo.git"

    def test_to_dict(self) -> None:
        p = ParsedPRUrl("owner", "repo", 123, "url")
        assert p.to_dict() == {"owner": "owner", "repo": "repo", "pull_number": 123}


# ===========================================================================
# Exception hierarchy
# ===========================================================================


class TestExceptions:
    def test_all_are_value_errors(self) -> None:
        assert issubclass(InvalidGitHubURLError, ValueError)
        assert issubclass(NotAPullRequestURLError, ValueError)
        assert issubclass(InvalidOwnerError, ValueError)
        assert issubclass(InvalidRepoError, ValueError)
        assert issubclass(InvalidPullNumberError, ValueError)

    def test_error_carries_url(self) -> None:
        try:
            parse_pr_url("https://github.com/owner/-repo/pull/1")
        except InvalidRepoError as exc:
            assert exc.url == "https://github.com/owner/-repo/pull/1"
        else:
            pytest.fail("Expected InvalidRepoError")

    def test_error_message_includes_context(self) -> None:
        try:
            parse_pr_url("https://gitlab.com/a/b")
        except InvalidGitHubURLError as exc:
            assert "gitlab" in str(exc).lower()


# ===========================================================================
# Integration: parse → dict (matches user specification)
# ===========================================================================


class TestIntegration:
    def test_parse_to_dict(self) -> None:
        url = "https://github.com/langchain-ai/langgraph/pull/123"
        result = parse_pr_url(url)
        output = result.to_dict()
        assert output == {"owner": "langchain-ai", "repo": "langgraph", "pull_number": 123}
