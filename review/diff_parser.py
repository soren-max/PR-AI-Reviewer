"""
Diff Analysis Module

Parses unified diff output (``git diff`` / GitHub PR diff) and extracts
structured information: file paths, changed lines, modified functions
and classes, and per-file statistics.

Supports Python, TypeScript/JavaScript, Go, and other common languages
for function/class detection.

Typical usage::

    >>> from diff_analyzer import parse_diff, DiffResult

    >>> diff_text = \"\"\"
    ... diff --git a/src/auth.py b/src/auth.py
    ... --- a/src/auth.py
    ... +++ b/src/auth.py
    ... @@ -1,3 +1,8 @@
    ...  def login():
    ... -    old_password = \"abc\"
    ... +    password = os.getenv(\"PASSWORD\")
    ... +    if not password:
    ... +        raise ValueError(\"PASSWORD not set\")
    ... \"\"\"

    >>> result = parse_diff(diff_text)
    >>> result.files[0].functions[0].name
    'login'
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Generator, Optional

# ===========================================================================
# Constants — regex patterns for function/class detection
# ===========================================================================

#: Patterns to detect function definitions across languages.
#: Each pattern must have a ``name`` capture group.
_FUNCTION_PATTERNS: list[re.Pattern[str]] = [
    # Python: def function_name(...)
    re.compile(r'^\s*(?:async\s+)?def\s+(?P<name>[a-zA-Z_]\w*)\s*\('),
    # TypeScript / JavaScript: function name(...) or const name = (...) =>
    re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(?P<name>[a-zA-Z_$]\w*)\s*\('),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z_$]\w*)\s*=\s*(?:async\s*)?\("),
    # Go: func name(...)
    re.compile(r'^\s*func\s+(?P<name>[a-zA-Z_]\w*)\s*\('),
    # Java / C++ / C#: returnType name(...) {  (simplified)
    re.compile(r'^\s*(?:public|private|protected|static|\w+\s+)*\s*(?P<name>[a-zA-Z_]\w*)\s*\('),
    # Ruby: def name
    re.compile(r'^\s*def\s+(?P<name>[a-zA-Z_]\w*)'),
    # Rust: fn name(...)
    re.compile(r'^\s*fn\s+(?P<name>[a-zA-Z_]\w*)\s*\('),
    # Kotlin: fun name(...)
    re.compile(r'^\s*fun\s+(?P<name>[a-zA-Z_]\w*)\s*\('),
]

#: Patterns to detect class definitions.
_CLASS_PATTERNS: list[re.Pattern[str]] = [
    # Python: class ClassName(...)
    re.compile(r'^\s*class\s+(?P<name>[a-zA-Z_]\w*)'),
    # TypeScript / JavaScript: class Name {...}
    re.compile(r'^\s*(?:export\s+)?(?:abstract\s+)?class\s+(?P<name>[a-zA-Z_$]\w*)'),
    # Java / C++ / C#: class Name
    re.compile(r'^\s*(?:public|private|protected)?\s*(?:abstract|final|static)?\s*class\s+(?P<name>[a-zA-Z_]\w*)'),
    # Go: type Name struct / interface
    re.compile(r'^\s*type\s+(?P<name>[a-zA-Z_]\w*)\s+(struct|interface)\s*'),
]

#: Pattern for hunk header: ``@@ -start,count +start,count @@ [optional context]``
_HUNK_HEADER_RE: re.Pattern[str] = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@\s*(.*)$"
)

#: Pattern for diff --git line
_DIFF_GIT_RE: re.Pattern[str] = re.compile(r"^diff --git a/(.*) b/(.*)$")

#: Pattern for --- / +++ lines
_FILE_OLD_RE: re.Pattern[str] = re.compile(r"^--- (?:a/(.*)|/dev/null)$")
_FILE_NEW_RE: re.Pattern[str] = re.compile(r"^\+\+\+ (?:b/(.*)|/dev/null)$")

#: Pattern for rename/copy
_RENAME_RE: re.Pattern[str] = re.compile(r"^rename (from|to) (.*)$")

#: Pattern for index line
_INDEX_RE: re.Pattern[str] = re.compile(r"^index [a-f0-9]+\.\.[a-f0-9]+ \d+$")

#: Binary file marker
_BINARY_RE: re.Pattern[str] = re.compile(r"^Binary files (.*) and (.*) differ$")

#: New file mode
_NEW_FILE_MODE_RE: re.Pattern[str] = re.compile(r"^new file mode \d+$")
_DELETED_FILE_MODE_RE: re.Pattern[str] = re.compile(r"^deleted file mode \d+")


# ===========================================================================
# Enums
# ===========================================================================


class LineType(str, Enum):
    """Type of a changed line in a diff hunk."""

    ADD = "add"          # Line added (prefixed with ``+``)
    DELETE = "delete"    # Line deleted (prefixed with ``-``)
    CONTEXT = "context"  # Context line (prefixed with `` ``)
    NO_NEWLINE = "no_newline"  # ``\\ No newline at end of file``


class FileStatus(str, Enum):
    """Status of a file in the diff."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    BINARY = "binary"
    UNCHANGED = "unchanged"


class ChangeType(str, Enum):
    """Type of change for a function or class."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


# ===========================================================================
# Pydantic-style data models (dataclasses for zero dependencies)
# ===========================================================================


@dataclass(frozen=True)
class HunkRange:
    """Line number range for a hunk.

    Attributes:
        old_start: Starting line number in the old (original) file.
        old_count: Number of lines in the old file hunk.
        new_start: Starting line number in the new (modified) file.
        new_count: Number of lines in the new file hunk.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int


@dataclass
class ChangedLine:
    """A single line within a diff hunk.

    Attributes:
        line_type: Whether the line was added, deleted, or is context.
        content: The raw line content (without the ``+`` / ``-`` / `` `` prefix).
        old_line_no: Line number in the old file (or ``None`` for added lines).
        new_line_no: Line number in the new file (or ``None`` for deleted lines).
    """

    line_type: LineType
    content: str
    old_line_no: Optional[int] = None
    new_line_no: Optional[int] = None


@dataclass
class Hunk:
    """A single hunk (``@@`` block) in a unified diff.

    Attributes:
        range: Line number range for this hunk.
        header: The raw ``@@`` header line including trailing context.
        lines: List of changed lines in this hunk.
    """

    range: HunkRange
    header: str
    lines: list[ChangedLine] = field(default_factory=list)

    @property
    def additions(self) -> int:
        """Number of added lines in this hunk."""
        return sum(1 for line in self.lines if line.line_type == LineType.ADD)

    @property
    def deletions(self) -> int:
        """Number of deleted lines in this hunk."""
        return sum(1 for line in self.lines if line.line_type == LineType.DELETE)

    @property
    def context_lines(self) -> int:
        """Number of context lines in this hunk."""
        return sum(1 for line in self.lines if line.line_type == LineType.CONTEXT)


@dataclass
class FunctionChange:
    """A function that was modified in the diff.

    Attributes:
        name: Function name.
        file_path: Path to the file containing this function.
        change_type: Whether the function was added, removed, or modified.
        start_line: Approximate starting line in the new file.
    """

    name: str
    file_path: str
    change_type: ChangeType
    start_line: int


@dataclass
class ClassChange:
    """A class that was modified in the diff.

    Attributes:
        name: Class name.
        file_path: Path to the file containing this class.
        change_type: Whether the class was added, removed, or modified.
        start_line: Approximate starting line in the new file.
    """

    name: str
    file_path: str
    change_type: ChangeType
    start_line: int


@dataclass
class FileDiff:
    """Analysis of a single file's diff.

    Attributes:
        old_path: Path in the original commit (``a/`` side).
        new_path: Path in the new commit (``b/`` side).
        status: File status (added / modified / deleted / renamed / binary).
        hunks: Parsed hunks in this file.
        additions: Total added lines.
        deletions: Total deleted lines.
        functions: Functions modified in this file.
        classes: Classes modified in this file.
        is_binary: Whether this is a binary file.
    """

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
    """Complete result of parsing a unified diff.

    Attributes:
        files: List of file diffs parsed from the input.
        total_additions: Total added lines across all files.
        total_deletions: Total deleted lines across all files.
        total_files_changed: Number of files that have changes.
        raw_text: The original raw diff text (for reference).
    """

    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    total_files_changed: int = 0
    raw_text: str = ""


# ===========================================================================
# Exceptions
# ===========================================================================


class DiffParseError(ValueError):
    """Raised when the diff text cannot be parsed."""

    def __init__(self, message: str, line: str = "", line_number: int = 0) -> None:
        self.line = line
        self.line_number = line_number
        detail = f"line {line_number}: {line}" if line_number else ""
        super().__init__(f"Diff parse error: {message} [{detail}]".strip())


# ===========================================================================
# Core parser
# ===========================================================================


def parse_diff(diff_text: str) -> DiffResult:
    """Parse a unified diff string into a structured :class:`DiffResult`.

    Args:
        diff_text: Raw unified diff output (e.g. from ``git diff`` or
                   GitHub PR diff API).

    Returns:
        A :class:`DiffResult` containing per-file analysis, statistics,
        and detected functions / classes.

    Raises:
        DiffParseError: If the diff format is invalid.

    Example:
        >>> result = parse_diff(SAMPLE_DIFF)
        >>> result.total_files_changed
        2
        >>> result.total_additions
        50
        >>> result.files[0].functions[0].name
        'login'
    """
    result = DiffResult(raw_text=diff_text)

    # Split into file sections (separated by ``diff --git``)
    for file_diff in _split_file_sections(diff_text):
        parsed = _parse_file_diff(file_diff)
        if parsed is not None:
            result.files.append(parsed)

    # Aggregate totals
    result.total_files_changed = len(result.files)
    result.total_additions = sum(f.additions for f in result.files)
    result.total_deletions = sum(f.deletions for f in result.files)

    return result


# ===========================================================================
# Internal: file-level parsing
# ===========================================================================


def _split_file_sections(diff_text: str) -> list[str]:
    """Split a multi-file diff into individual file sections.

    Each section starts with ``diff --git``.
    """
    if not diff_text.strip():
        return []

    lines = diff_text.splitlines(keepends=True)
    sections: list[str] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("diff --git") and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append("".join(current))

    return sections


def _parse_file_diff(section: str) -> Optional[FileDiff]:
    """Parse a single file's diff section into a :class:`FileDiff`.

    Returns ``None`` for sections that are empty or unparseable.
    """
    lines = section.splitlines()
    if not lines:
        return None

    file_diff = FileDiff(old_path="", new_path="")
    i = 0
    hunks: list[Hunk] = []
    seen_paths = False

    while i < len(lines):
        line = lines[i]

        # --- diff --git ---
        git_match = _DIFF_GIT_RE.match(line)
        if git_match:
            file_diff.old_path = git_match.group(1)
            file_diff.new_path = git_match.group(2)
            seen_paths = True
            i += 1
            continue

        # --- new/deleted file mode ---
        if _NEW_FILE_MODE_RE.match(line):
            file_diff.status = FileStatus.ADDED
            i += 1
            continue
        if _DELETED_FILE_MODE_RE.match(line):
            file_diff.status = FileStatus.DELETED
            i += 1
            continue

        # --- rename from/to ---
        rename_match = _RENAME_RE.match(line)
        if rename_match:
            file_diff.status = FileStatus.RENAMED
            i += 1
            continue

        # --- index line ---
        if _INDEX_RE.match(line):
            i += 1
            continue

        # --- binary ---
        if _BINARY_RE.match(line):
            file_diff.is_binary = True
            file_diff.status = FileStatus.BINARY
            i += 1
            continue

        # --- --- a/... ---
        old_match = _FILE_OLD_RE.match(line)
        if old_match:
            old_path = old_match.group(1)
            if old_path:
                file_diff.old_path = old_path
            i += 1
            continue

        # --- +++ b/... ---
        new_match = _FILE_NEW_RE.match(line)
        if new_match:
            new_path = new_match.group(1)
            if new_path:
                file_diff.new_path = new_path
            i += 1
            continue

        # --- hunk header @@ ---
        hunk_match = _HUNK_HEADER_RE.match(line)
        if hunk_match:
            hunk, hunk_lines_consumed = _parse_hunk(lines, i)
            if hunk is not None:
                hunks.append(hunk)
                _detect_changes_in_hunk(hunk, file_diff)
                i += hunk_lines_consumed
                continue
            i += 1
            continue

        # --- empty line / unknown ---
        # Skip lines that aren't part of the diff structure
        i += 1

    # If we never saw a 'diff --git' line, this is not a valid diff section
    if not seen_paths and not file_diff.old_path and not file_diff.new_path:
        return None

    file_diff.hunks = hunks

    # Compute per-file statistics
    for hunk in hunks:
        file_diff.additions += hunk.additions
        file_diff.deletions += hunk.deletions

    # Determine file status if not already set
    if not hunks and file_diff.status == FileStatus.MODIFIED:
        if file_diff.old_path == "/dev/null" or (file_diff.old_path and not file_diff.new_path):
            file_diff.status = FileStatus.DELETED

    return file_diff


# ===========================================================================
# Internal: hunk-level parsing
# ===========================================================================


def _parse_hunk(lines: list[str], start: int) -> tuple[Optional[Hunk], int]:
    """Parse a hunk starting at ``lines[start]``.

    Returns:
        Tuple of ``(hunk, lines_consumed)``.  ``hunk`` is ``None`` if
        the hunk header is malformed.
    """
    header_match = _HUNK_HEADER_RE.match(lines[start])
    if not header_match:
        return None, 1

    old_start = int(header_match.group(1))
    old_count = int(header_match.group(2) or 1)
    new_start = int(header_match.group(3))
    new_count = int(header_match.group(4) or 1)
    header_text = header_match.group(5).strip()

    hunk = Hunk(
        range=HunkRange(
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
        ),
        header=header_text,
    )

    # Parse hunk body lines
    old_line = old_start
    new_line = new_start
    consumed = 1  # the header line itself

    for i in range(start + 1, len(lines)):
        line = lines[i]
        consumed += 1

        if line.startswith("\\ "):  # No newline at end of file
            hunk.lines.append(ChangedLine(
                line_type=LineType.NO_NEWLINE,
                content=line[1:],
            ))
            continue

        if line.startswith("+"):
            hunk.lines.append(ChangedLine(
                line_type=LineType.ADD,
                content=line[1:],
                new_line_no=new_line,
            ))
            new_line += 1
        elif line.startswith("-"):
            hunk.lines.append(ChangedLine(
                line_type=LineType.DELETE,
                content=line[1:],
                old_line_no=old_line,
            ))
            old_line += 1
        elif line.startswith(" ") or line == "":
            hunk.lines.append(ChangedLine(
                line_type=LineType.CONTEXT,
                content=line[1:] if line.startswith(" ") else line,
                old_line_no=old_line,
                new_line_no=new_line,
            ))
            old_line += 1
            new_line += 1
        elif line.startswith("@"):
            # Next hunk starts — stop here
            consumed -= 1
            break
        else:
            # Unknown line — treat as context
            hunk.lines.append(ChangedLine(
                line_type=LineType.CONTEXT,
                content=line,
                old_line_no=old_line,
                new_line_no=new_line,
            ))
            old_line += 1
            new_line += 1

    return hunk, consumed


# ===========================================================================
# Internal: function and class detection
# ===========================================================================


def _detect_changes_in_hunk(hunk: Hunk, file_diff: FileDiff) -> None:
    """Scan ALL lines for function and class definitions.

    Scans context, add, AND delete lines because function definitions
    often appear on context lines (pre-existing functions being modified).
    """
    file_path = file_diff.new_path or file_diff.old_path
    seen_funcs: set[str] = set()
    seen_classes: set[str] = set()

    for line in hunk.lines:
        line_no = line.new_line_no if line.new_line_no is not None else line.old_line_no or 0

        # Check for function definitions
        func_name = _extract_function_name(line.content)
        if func_name and func_name not in seen_funcs:
            seen_funcs.add(func_name)
            change_type = _classify_change(hunk, func_name)
            file_diff.functions.append(FunctionChange(
                name=func_name,
                file_path=file_path,
                change_type=change_type,
                start_line=line_no,
            ))

        # Check for class definitions
        class_name = _extract_class_name(line.content)
        if class_name and class_name not in seen_classes:
            seen_classes.add(class_name)
            change_type = _classify_change(hunk, class_name)
            file_diff.classes.append(ClassChange(
                name=class_name,
                file_path=file_path,
                change_type=change_type,
                start_line=line_no,
            ))


def _classify_change(hunk: Hunk, symbol: str) -> ChangeType:
    """Classify a symbol as ADDED, REMOVED, or MODIFIED.

    Looks at both + and - lines in the hunk.  If the symbol appears in
    both types, it's MODIFIED.  If only in + lines (or context+add), it's
    ADDED.  If only in - lines (or context+delete), it's REMOVED.
    """
    name_lower = symbol.lower()
    has_add = any(
        line.line_type == LineType.ADD and name_lower in line.content.lower()
        for line in hunk.lines
    )
    has_delete = any(
        line.line_type == LineType.DELETE and name_lower in line.content.lower()
        for line in hunk.lines
    )

    if has_add and has_delete:
        return ChangeType.MODIFIED
    if has_add:
        return ChangeType.ADDED
    if has_delete:
        return ChangeType.REMOVED
    return ChangeType.MODIFIED  # context-only = modified


def _extract_function_name(line_content: str) -> Optional[str]:
    """Try to extract a function name from a changed line.

    Uses language-specific regex patterns to detect function definitions.
    """
    for pattern in _FUNCTION_PATTERNS:
        match = pattern.match(line_content)
        if match:
            return match.group("name")
    return None


def _extract_class_name(line_content: str) -> Optional[str]:
    """Try to extract a class name from a changed line."""
    for pattern in _CLASS_PATTERNS:
        match = pattern.match(line_content)
        if match:
            return match.group("name")
    return None


def _resolve_change_type(hunk: Hunk, symbol: str, default: ChangeType) -> ChangeType:
    """Determine whether a symbol is truly 'modified' (not just added or removed).

    A symbol is "modified" when it appears in both added and deleted lines
    within the same hunk.  This distinguishes:

    - ``+def foo():`` + ``-def foo():``  →  modified (renamed or changed body)
    - ``+def foo():`` without removal    →  added (new function)
    - ``-def foo():`` without addition   →  removed (deleted function)
    """
    has_add = False
    has_delete = False
    name_lower = symbol.lower()

    for line in hunk.lines:
        if line.line_type == LineType.ADD:
            # Check if the added line contains this symbol
            if _line_refers_to(line.content, name_lower):
                has_add = True
        elif line.line_type == LineType.DELETE:
            if _line_refers_to(line.content, name_lower):
                has_delete = True

    if has_add and has_delete:
        return ChangeType.MODIFIED
    return default


def _line_refers_to(line_content: str, name_lower: str) -> bool:
    """Check if a line of code refers to a given symbol name."""
    stripped = line_content.strip().lower()
    # Check for exact match or as a word boundary
    return name_lower in stripped


# ===========================================================================
# Convenience helpers
# ===========================================================================


def summarize_diff(diff_text: str, max_files: int = 5) -> str:
    """Generate a human-readable summary of a diff.

    Args:
        diff_text: Raw unified diff text.
        max_files: Maximum number of files to include in the summary.

    Returns:
        A short Markdown summary string.

    Example:
        >>> summarize_diff(diff_text)
        '3 files changed: 2 Python files, 1 config file. 120 additions, 45 deletions.'
    """
    result = parse_diff(diff_text)
    parts: list[str] = []

    # Count files by type
    py_count = sum(1 for f in result.files if f.new_path.endswith(".py") or f.old_path.endswith(".py"))
    js_count = sum(1 for f in result.files if f.new_path.endswith((".js", ".ts", ".tsx", ".jsx")) or f.old_path.endswith((".js", ".ts", ".tsx", ".jsx")))
    other_count = result.total_files_changed - py_count - js_count

    type_parts = []
    if py_count:
        type_parts.append(f"{py_count} Python file{'s' if py_count > 1 else ''}")
    if js_count:
        type_parts.append(f"{js_count} JS/TS file{'s' if js_count > 1 else ''}")
    if other_count:
        type_parts.append(f"{other_count} other file{'s' if other_count > 1 else ''}")

    if type_parts:
        parts.append(f"{result.total_files_changed} files changed: {', '.join(type_parts)}.")

    parts.append(f"{result.total_additions} additions, {result.total_deletions} deletions.")

    # Count functions
    total_funcs = sum(len(f.functions) for f in result.files)
    total_classes = sum(len(f.classes) for f in result.files)
    if total_funcs:
        parts.append(f"{total_funcs} function{'s' if total_funcs > 1 else ''} modified.")
    if total_classes:
        parts.append(f"{total_classes} class{'es' if total_classes > 1 else ''} modified.")

    return " ".join(parts)


def get_added_lines(diff_text: str, file_path: Optional[str] = None) -> list[str]:
    """Extract only the added lines from a diff.

    Args:
        diff_text: Raw unified diff text.
        file_path: If provided, only return lines from this file.

    Returns:
        List of added line contents.
    """
    result = parse_diff(diff_text)
    added: list[str] = []

    for file_diff in result.files:
        if file_path and file_diff.new_path != file_path and file_diff.old_path != file_path:
            continue
        for hunk in file_diff.hunks:
            for line in hunk.lines:
                if line.line_type == LineType.ADD:
                    added.append(line.content)

    return added
