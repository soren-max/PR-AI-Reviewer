"""
Review module — core code review engine.

Modules:
    diff_parser — Unified diff parsing and analysis

Usage:
    from review.diff_parser import parse_diff, DiffResult
"""
from review.diff_parser import parse_diff, DiffResult, FileDiff, Hunk

__all__ = [
    "parse_diff",
    "DiffResult",
    "FileDiff",
    "Hunk",
]
