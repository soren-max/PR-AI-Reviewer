"""
GitHub integration module.

Modules:
    parser — PR URL parsing (pure function, no I/O)
    client — GitHub REST API v3 client (requests-based, with retry)

Usage:
    from github.parser import parse_pr_url
    from github.client import GitHubClient
"""
from github.parser import parse_pr_url, is_valid_pr_url, ParsedPRUrl
from github.client import GitHubClient, GitHubClientError

__all__ = [
    "parse_pr_url",
    "is_valid_pr_url",
    "ParsedPRUrl",
    "GitHubClient",
    "GitHubClientError",
]
