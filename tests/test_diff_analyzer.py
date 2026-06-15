"""
Tests for ``diff_analyzer.py`` — unified diff parsing and analysis.

Uses only ``unittest`` from the standard library (no external dependencies).
Covers:
  - Python function / class detection
  - JS/TS function detection
  - Multi-file diffs
  - Hunks with add / delete / context lines
  - Binary files, renames, new files, deleted files
  - Edge cases: empty diff, single line, malformed hunks
  - ``summarize_diff()`` and ``get_added_lines()`` helpers
"""
from __future__ import annotations

import unittest

from diff_analyzer import (
    parse_diff,
    summarize_diff,
    get_added_lines,
    DiffResult,
    FileStatus,
    ChangeType,
    LineType,
)


# ===========================================================================
# Sample diffs
# ===========================================================================

SINGLE_FILE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
index abc..def 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,8 @@
 def login():
-    old_password = "abc123"
+    password = os.getenv("PASSWORD")
+    if not password:
+        raise ValueError("PASSWORD not set")
     return authenticate(request, password)
+
+
+def logout():
+    session.clear()
"""

MULTI_FILE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
index abc..def 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,3 +1,4 @@
 def login():
-    pass
+    return authenticate()
+
+class UserManager:
+    def create_user(self):
+        pass
diff --git a/src/config.py b/src/config.py
new file mode 100644
index 000..xyz
--- /dev/null
+++ b/src/config.py
@@ -0,0 +1,5 @@
+DEBUG = True
+DATABASE_URL = "sqlite:///test.db"
+
+class Config:
+    pass
"""

BINARY_DIFF = """\
diff --git a/image.png b/image.png
index abc..def 100644
Binary files a/image.png and b/image.png differ
"""

RENAME_DIFF = """\
diff --git a/src/old.py b/src/new.py
similarity index 100%
rename from src/old.py
rename to src/new.py
"""

DELETED_FILE_DIFF = """\
diff --git a/src/old.py b/src/old.py
deleted file mode 100644
index abc..def
--- a/src/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-def old_function():
-    print("goodbye")
-    return None
"""

TYPESCRIPT_DIFF = """\
diff --git a/src/app.ts b/src/app.ts
index abc..def 100644
--- a/src/app.ts
+++ b/src/app.ts
@@ -1,3 +1,10 @@
 function greet(name: string) {
-    return "Hello, " + name;
+    return `Hello, ${name}`;
 }
+
+const fetchData = async (url: string) => {
+    const response = await fetch(url);
+    return response.json();
+};
+
+export class ApiClient {
+    async get<T>(path: string): Promise<T> {
+        return fetchData(path);
+    }
+}
"""


# ===========================================================================
# Basic parsing
# ===========================================================================

class TestParseBasic(unittest.TestCase):
    def test_single_file(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        self.assertIsInstance(result, DiffResult)
        self.assertEqual(result.total_files_changed, 1)
        self.assertEqual(result.files[0].old_path, "src/auth.py")
        self.assertEqual(result.files[0].new_path, "src/auth.py")

    def test_file_status_modified(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        self.assertEqual(result.files[0].status, FileStatus.MODIFIED)

    def test_multi_file(self) -> None:
        result = parse_diff(MULTI_FILE_DIFF)
        self.assertEqual(result.total_files_changed, 2)
        self.assertEqual(result.files[0].new_path, "src/auth.py")
        self.assertEqual(result.files[1].new_path, "src/config.py")

    def test_empty_diff(self) -> None:
        result = parse_diff("")
        self.assertEqual(result.total_files_changed, 0)
        self.assertEqual(result.total_additions, 0)

    def test_raw_text_preserved(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        self.assertEqual(result.raw_text, SINGLE_FILE_DIFF)


# ===========================================================================
# Hunk parsing
# ===========================================================================

class TestHunkParsing(unittest.TestCase):
    def test_hunk_count(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        self.assertEqual(len(result.files[0].hunks), 1)

    def test_hunk_range(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        hunk = result.files[0].hunks[0]
        self.assertEqual(hunk.range.old_start, 1)
        self.assertEqual(hunk.range.old_count, 5)
        self.assertEqual(hunk.range.new_start, 1)
        self.assertEqual(hunk.range.new_count, 8)

    def test_hunk_header_context(self) -> None:
        """GitHub diff output usually doesn't include context in the @@ header."""
        result = parse_diff(SINGLE_FILE_DIFF)
        # The header text after @@ is typically empty in GitHub diffs
        self.assertEqual(result.files[0].hunks[0].header, "")

    def test_changed_line_types(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        types = {line.line_type for line in result.files[0].hunks[0].lines}
        self.assertIn(LineType.CONTEXT, types)
        self.assertIn(LineType.DELETE, types)
        self.assertIn(LineType.ADD, types)

    def test_changed_line_numbers(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        hunk = result.files[0].hunks[0]
        for line in hunk.lines:
            if line.line_type == LineType.DELETE:
                self.assertIsNotNone(line.old_line_no)
                self.assertIsNone(line.new_line_no)
            elif line.line_type == LineType.ADD:
                self.assertIsNotNone(line.new_line_no)
                self.assertIsNone(line.old_line_no)

    def test_hunk_additions_deletions(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        hunk = result.files[0].hunks[0]
        # 7 added lines: password, if not, raise, blank line, blank line, def logout, session.clear
        self.assertEqual(hunk.additions, 7)
        self.assertEqual(hunk.deletions, 1)

    def test_multiple_hunks(self) -> None:
        diff = """\
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,3 +1,4 @@
 def a():
-    x
+    y
@@ -10,3 +10,4 @@
 def b():
-    p
+    q
"""
        result = parse_diff(diff)
        self.assertEqual(len(result.files[0].hunks), 2)


# ===========================================================================
# Function detection
# ===========================================================================

class TestFunctionDetection(unittest.TestCase):
    def test_detects_python_function(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        names = [f.name for f in result.files[0].functions]
        self.assertIn("login", names)
        self.assertIn("logout", names)

    def test_function_change_type_added(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        logout = [f for f in result.files[0].functions if f.name == "logout"]
        self.assertEqual(len(logout), 1)
        self.assertEqual(logout[0].change_type, ChangeType.ADDED)

    def test_function_change_type_modified(self) -> None:
        diff = """\
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,3 +1,4 @@
 def login():
-    pass
+    return True
"""
        result = parse_diff(diff)
        login = [f for f in result.files[0].functions if f.name == "login"]
        self.assertEqual(login[0].change_type, ChangeType.MODIFIED)

    def test_function_change_type_removed(self) -> None:
        result = parse_diff(DELETED_FILE_DIFF)
        old_func = [f for f in result.files[0].functions if f.name == "old_function"]
        self.assertEqual(old_func[0].change_type, ChangeType.REMOVED)

    def test_function_file_path(self) -> None:
        result = parse_diff(SINGLE_FILE_DIFF)
        for func in result.files[0].functions:
            self.assertEqual(func.file_path, "src/auth.py")

    def test_ts_function_detection(self) -> None:
        result = parse_diff(TYPESCRIPT_DIFF)
        names = [f.name for f in result.files[0].functions]
        self.assertIn("greet", names)
        self.assertIn("fetchData", names)


# ===========================================================================
# Class detection
# ===========================================================================

class TestClassDetection(unittest.TestCase):
    def test_detects_python_class(self) -> None:
        result = parse_diff(MULTI_FILE_DIFF)
        names = [c.name for c in result.files[0].classes]
        self.assertIn("UserManager", names)

    def test_new_file_class(self) -> None:
        result = parse_diff(MULTI_FILE_DIFF)
        names = [c.name for c in result.files[1].classes]
        self.assertIn("Config", names)

    def test_ts_class_detection(self) -> None:
        result = parse_diff(TYPESCRIPT_DIFF)
        names = [c.name for c in result.files[0].classes]
        self.assertIn("ApiClient", names)


# ===========================================================================
# File status
# ===========================================================================

class TestFileStatus(unittest.TestCase):
    def test_binary_file(self) -> None:
        result = parse_diff(BINARY_DIFF)
        self.assertTrue(result.files[0].is_binary)
        self.assertEqual(result.files[0].status, FileStatus.BINARY)

    def test_renamed_file(self) -> None:
        result = parse_diff(RENAME_DIFF)
        self.assertEqual(result.files[0].status, FileStatus.RENAMED)
        self.assertEqual(result.files[0].old_path, "src/old.py")
        self.assertEqual(result.files[0].new_path, "src/new.py")

    def test_new_file(self) -> None:
        result = parse_diff(MULTI_FILE_DIFF)
        self.assertEqual(result.files[1].status, FileStatus.ADDED)

    def test_deleted_file(self) -> None:
        result = parse_diff(DELETED_FILE_DIFF)
        self.assertEqual(result.files[0].status, FileStatus.DELETED)


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases(unittest.TestCase):
    def test_no_newline_at_eof(self) -> None:
        diff = """\
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,3 +1,4 @@
 def foo():
-    pass
+    return True
\\ No newline at end of file
"""
        result = parse_diff(diff)
        self.assertEqual(len(result.files), 1)

    def test_single_line_change(self) -> None:
        diff = """\
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-old
+new
"""
        result = parse_diff(diff)
        self.assertEqual(result.total_additions, 1)
        self.assertEqual(result.total_deletions, 1)

    def test_no_changes_parses(self) -> None:
        diff = """\
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1,3 +1,3 @@
  unchanged
  unchanged
  unchanged
"""
        result = parse_diff(diff)
        self.assertEqual(result.total_additions, 0)
        self.assertEqual(result.total_deletions, 0)

    def test_rename_with_changes(self) -> None:
        diff = """\
diff --git a/src/old.py b/src/new.py
similarity index 80%
rename from src/old.py
rename to src/new.py
--- a/src/old.py
+++ b/src/new.py
@@ -1,3 +1,4 @@
 def existing():
-    pass
+    return 42
"""
        result = parse_diff(diff)
        self.assertEqual(result.files[0].status, FileStatus.RENAMED)
        self.assertEqual(result.files[0].additions, 1)
        self.assertEqual(result.files[0].deletions, 1)


# ===========================================================================
# Convenience helpers
# ===========================================================================

class TestSummarizeDiff(unittest.TestCase):
    def test_summary_format(self) -> None:
        summary = summarize_diff(MULTI_FILE_DIFF)
        self.assertIsInstance(summary, str)
        self.assertIn("files changed", summary)
        self.assertIn("additions", summary)
        self.assertIn("deletions", summary)

    def test_summary_counts(self) -> None:
        summary = summarize_diff(SINGLE_FILE_DIFF)
        self.assertIn("additions", summary)
        self.assertIn("deletions", summary)

    def test_summary_empty(self) -> None:
        summary = summarize_diff("")
        self.assertIn("0 additions", summary)


class TestGetAddedLines(unittest.TestCase):
    def test_returns_added_lines(self) -> None:
        lines = get_added_lines(SINGLE_FILE_DIFF)
        self.assertEqual(len(lines), 7)  # 5 code lines + 2 blank + lines

    def test_filter_by_file(self) -> None:
        lines = get_added_lines(MULTI_FILE_DIFF, file_path="src/config.py")
        self.assertGreater(len(lines), 0)
        self.assertIn("DEBUG", lines[0])

    def test_empty_diff(self) -> None:
        self.assertEqual(get_added_lines(""), [])


# ===========================================================================
# Integration
# ===========================================================================

class TestIntegration(unittest.TestCase):
    def test_full_flow(self) -> None:
        """parse → summarize → get_added_lines"""
        result = parse_diff(SINGLE_FILE_DIFF)

        self.assertEqual(result.files[0].new_path, "src/auth.py")
        self.assertEqual(result.files[0].additions, 7)
        self.assertEqual(result.files[0].deletions, 1)

        funcs = {f.name: f for f in result.files[0].functions}
        self.assertIn("login", funcs)
        self.assertIn("logout", funcs)
        self.assertEqual(funcs["logout"].change_type, ChangeType.ADDED)

        summary = summarize_diff(SINGLE_FILE_DIFF)
        self.assertIn("1 files changed", summary)
        self.assertIn("4 functions", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
