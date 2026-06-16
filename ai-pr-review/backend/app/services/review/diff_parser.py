"""
Diff Parser — 将 unified diff 解析为结构化数据。

Clean Architecture 层级: Domain
依赖: 无（纯函数）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
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
        return sum(1 for line in self.lines if line.line_type == LineType.ADD)

    @property
    def deletions(self) -> int:
        return sum(1 for line in self.lines if line.line_type == LineType.DELETE)


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


_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")
_OLD_FILE_RE = re.compile(r"^--- (?:a/(.*)|/dev/null)$")
_NEW_FILE_RE = re.compile(r"^\+\+\+ (?:b/(.*)|/dev/null)$")
_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@\s*(.*)$")
_PY_FUNCTION_RE = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(")
_PY_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)")


def parse_diff(diff_text: str) -> DiffResult:
    """Parse unified diff text into the backend's self-contained model."""
    result = DiffResult(raw_text=diff_text)
    current_file: FileDiff | None = None
    current_hunk: Hunk | None = None
    old_line_no = 0
    new_line_no = 0

    for raw_line in diff_text.splitlines():
        git_match = _DIFF_GIT_RE.match(raw_line)
        if git_match:
            current_file = FileDiff(
                old_path=git_match.group(1),
                new_path=git_match.group(2),
            )
            result.files.append(current_file)
            current_hunk = None
            continue

        if current_file is None:
            continue

        if raw_line.startswith("new file mode"):
            current_file.status = FileStatus.ADDED
            continue
        if raw_line.startswith("deleted file mode"):
            current_file.status = FileStatus.DELETED
            continue
        if raw_line.startswith("Binary files"):
            current_file.status = FileStatus.BINARY
            current_file.is_binary = True
            continue

        old_match = _OLD_FILE_RE.match(raw_line)
        if old_match:
            current_file.old_path = old_match.group(1) or ""
            if not current_file.old_path:
                current_file.status = FileStatus.ADDED
            continue

        new_match = _NEW_FILE_RE.match(raw_line)
        if new_match:
            current_file.new_path = new_match.group(1) or ""
            if not current_file.new_path:
                current_file.status = FileStatus.DELETED
            continue

        hunk_match = _HUNK_RE.match(raw_line)
        if hunk_match:
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2) or "1")
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4) or "1")
            old_line_no = old_start
            new_line_no = new_start
            current_hunk = Hunk(
                range=HunkRange(old_start, old_count, new_start, new_count),
                header=hunk_match.group(5),
            )
            current_file.hunks.append(current_hunk)
            continue

        if current_hunk is None:
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            content = raw_line[1:]
            line = ChangedLine(LineType.ADD, content, new_line_no=new_line_no)
            current_hunk.lines.append(line)
            current_file.additions += 1
            _record_symbol_change(current_file, content, ChangeType.ADDED, new_line_no)
            new_line_no += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            content = raw_line[1:]
            line = ChangedLine(LineType.DELETE, content, old_line_no=old_line_no)
            current_hunk.lines.append(line)
            current_file.deletions += 1
            _record_symbol_change(current_file, content, ChangeType.REMOVED, old_line_no)
            old_line_no += 1
        elif raw_line.startswith("\\"):
            current_hunk.lines.append(ChangedLine(LineType.NO_NEWLINE, raw_line))
        else:
            content = raw_line[1:] if raw_line.startswith(" ") else raw_line
            current_hunk.lines.append(
                ChangedLine(LineType.CONTEXT, content, old_line_no=old_line_no, new_line_no=new_line_no)
            )
            _record_symbol_change(current_file, content, ChangeType.MODIFIED, new_line_no)
            old_line_no += 1
            new_line_no += 1

    result.total_files_changed = len(result.files)
    result.total_additions = sum(file.additions for file in result.files)
    result.total_deletions = sum(file.deletions for file in result.files)
    return result


def _record_symbol_change(
    file_diff: FileDiff,
    content: str,
    change_type: ChangeType,
    line_no: int,
) -> None:
    """Record simple Python symbols to provide useful report context."""
    function_match = _PY_FUNCTION_RE.match(content)
    if function_match:
        name = function_match.group(1)
        if not any(f.name == name and f.start_line == line_no for f in file_diff.functions):
            file_diff.functions.append(FunctionChange(name, file_diff.new_path, change_type, line_no))
        return

    class_match = _PY_CLASS_RE.match(content)
    if class_match:
        name = class_match.group(1)
        if not any(c.name == name and c.start_line == line_no for c in file_diff.classes):
            file_diff.classes.append(ClassChange(name, file_diff.new_path, change_type, line_no))
