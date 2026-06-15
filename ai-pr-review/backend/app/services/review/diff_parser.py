"""
Diff Parser — 将 unified diff 解析为结构化数据。

Clean Architecture 层级: Domain
依赖: 无（纯函数）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LineType(str, Enum):
    ADD = "add"
    DELETE = "delete"
    CONTEXT = "context"
    NO_NEWLINE = "no_newline"


class FileStatus(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    BINARY = "binary"


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


@dataclass(frozen=True)
class HunkRange:
    old_start: int
    old_count: int
    new_start: int
    new_count: int


@dataclass
class ChangedLine:
    line_type: LineType
    content: str
    old_line_no: Optional[int] = None
    new_line_no: Optional[int] = None


@dataclass
class Hunk:
    range: HunkRange
    header: str
    lines: list[ChangedLine] = field(default_factory=list)

    @property
    def additions(self) -> int:
        return sum(1 for l in self.lines if l.line_type == LineType.ADD)

    @property
    def deletions(self) -> int:
        return sum(1 for l in self.lines if l.line_type == LineType.DELETE)


@dataclass
class FunctionChange:
    name: str
    file_path: str
    change_type: ChangeType
    start_line: int


@dataclass
class ClassChange:
    name: str
    file_path: str
    change_type: ChangeType
    start_line: int


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    status: FileStatus = FileStatus.MODIFIED
    hunks: list[Hunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    functions: list[FunctionChange] = field(default_factory=list)
    classes: list[ClassChange] = field(default_factory=list)
    is_binary: bool = False


@dataclass
class DiffResult:
    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    total_files_changed: int = 0
    raw_text: str = ""

    @property
    def changed_paths(self) -> list[str]:
        """Extract all changed file paths (prefer new_path)."""
        paths = []
        for f in self.files:
            paths.append(f.new_path or f.old_path)
        return paths


# Re-export the full parser from the existing diff_analyzer
from review.diff_parser import parse_diff as _parse_diff  # noqa: E402


def parse_diff(diff_text: str) -> DiffResult:
    """Parse unified diff text.  Thin adapter over the core engine."""
    raw = _parse_diff(diff_text)

    files = []
    for rf in raw.files:
        hunks = []
        for rh in rf.hunks:
            lines = [
                ChangedLine(
                    line_type=LineType(rl.line_type.value),
                    content=rl.content,
                    old_line_no=rl.old_line_no,
                    new_line_no=rl.new_line_no,
                )
                for rl in rh.lines
            ]
            hunks.append(Hunk(
                range=HunkRange(
                    old_start=rh.range.old_start,
                    old_count=rh.range.old_count,
                    new_start=rh.range.new_start,
                    new_count=rh.range.new_count,
                ),
                header=rh.header,
                lines=lines,
            ))

        functions = [
            FunctionChange(name=f.name, file_path=f.file_path,
                           change_type=ChangeType(f.change_type.value),
                           start_line=f.start_line)
            for f in rf.functions
        ]
        classes = [
            ClassChange(name=c.name, file_path=c.file_path,
                        change_type=ChangeType(c.change_type.value),
                        start_line=c.start_line)
            for c in rf.classes
        ]

        files.append(FileDiff(
            old_path=rf.old_path,
            new_path=rf.new_path,
            status=FileStatus(rf.status.value),
            hunks=hunks,
            additions=rf.additions,
            deletions=rf.deletions,
            functions=functions,
            classes=classes,
            is_binary=rf.is_binary,
        ))

    return DiffResult(
        files=files,
        total_additions=raw.total_additions,
        total_deletions=raw.total_deletions,
        total_files_changed=raw.total_files_changed,
        raw_text=raw.raw_text,
    )
