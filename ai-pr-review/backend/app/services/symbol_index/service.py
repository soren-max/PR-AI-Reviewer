"""
Code Symbol Index service.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tree_sitter import Node

from app.services.tree_sitter import ParserFactory


class CodeSymbolIndexService:
    """Build a repository-wide JSON-ready symbol index."""

    _SKIPPED_DIRS = {
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".reasonix",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "htmlcov",
        "node_modules",
        "site-packages",
    }

    def __init__(self, parser_factory: type[ParserFactory] = ParserFactory) -> None:
        self._parser_factory = parser_factory

    def build_index(self, repository_root: str | Path) -> dict[str, Any]:
        """Scan a repository root and return a unified symbol index."""
        root = Path(repository_root).resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Repository root does not exist: {root}")

        index: dict[str, Any] = {
            "version": 1,
            "root": str(root),
            "languages": ["python"],
            "modules": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "errors": [],
        }

        for path in self._iter_python_files(root):
            self._index_python_file(root, path, index)

        for key in ("modules", "functions", "classes", "imports", "errors"):
            index[key].sort(key=self._sort_key)

        index["summary"] = {
            "module_count": len(index["modules"]),
            "function_count": len(index["functions"]),
            "class_count": len(index["classes"]),
            "import_count": len(index["imports"]),
            "error_count": len(index["errors"]),
        }
        return index

    def build_index_json(self, repository_root: str | Path) -> str:
        """Build the symbol index and serialize it as deterministic JSON."""
        return json.dumps(self.build_index(repository_root), ensure_ascii=False, sort_keys=True)

    def build_state_update(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a LangGraph-compatible additive state update."""
        repository_root = state.get("repository_root") or state.get("repo_path")
        if not repository_root:
            raise ValueError("state must include 'repository_root' or 'repo_path'")
        return {"symbol_index": self.build_index(repository_root)}

    def _iter_python_files(self, root: Path) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob("*.py"):
            relative_parts = path.relative_to(root).parts
            if any(part in self._SKIPPED_DIRS for part in relative_parts):
                continue
            files.append(path)
        return sorted(files, key=lambda item: item.relative_to(root).as_posix())

    def _index_python_file(
        self,
        root: Path,
        path: Path,
        index: dict[str, Any],
    ) -> None:
        relative_path = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            index["errors"].append({
                "file_path": relative_path,
                "message": str(exc),
                "type": "decode_error",
            })
            return

        parser = self._parser_factory.create("python")
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        module_name = self._module_name(relative_path)

        index["modules"].append({
            "file_path": relative_path,
            "module": module_name,
            "language": "python",
            "has_error": tree.root_node.has_error,
            "range": self._range(tree.root_node),
        })
        if tree.root_node.has_error:
            index["errors"].append({
                "file_path": relative_path,
                "module": module_name,
                "message": "Tree-sitter reported syntax errors",
                "type": "parse_error",
            })

        self._walk(
            tree.root_node,
            source_bytes,
            relative_path=relative_path,
            module_name=module_name,
            index=index,
            class_stack=[],
            function_stack=[],
        )

    def _walk(
        self,
        node: Node,
        source_bytes: bytes,
        *,
        relative_path: str,
        module_name: str,
        index: dict[str, Any],
        class_stack: list[str],
        function_stack: list[str],
    ) -> None:
        if node.type == "class_definition":
            name = self._node_name(node, source_bytes)
            if name:
                index["classes"].append({
                    "name": name,
                    "qualname": ".".join([*class_stack, name]),
                    "file_path": relative_path,
                    "module": module_name,
                    "range": self._range(node),
                })
                class_stack = [*class_stack, name]

        if node.type == "function_definition":
            name = self._node_name(node, source_bytes)
            if name:
                scope = [*class_stack, *function_stack, name]
                index["functions"].append({
                    "name": name,
                    "qualname": ".".join(scope),
                    "kind": "method" if class_stack else "function",
                    "parent_class": class_stack[-1] if class_stack else None,
                    "file_path": relative_path,
                    "module": module_name,
                    "range": self._range(node),
                })
                function_stack = [*function_stack, name]

        if node.type in {"import_statement", "import_from_statement"}:
            index["imports"].append({
                "statement": self._text(node, source_bytes),
                "imports": self._parse_import_statement(self._text(node, source_bytes)),
                "file_path": relative_path,
                "module": module_name,
                "range": self._range(node),
            })

        for child in node.children:
            if child.is_named:
                self._walk(
                    child,
                    source_bytes,
                    relative_path=relative_path,
                    module_name=module_name,
                    index=index,
                    class_stack=class_stack,
                    function_stack=function_stack,
                )

    def _node_name(self, node: Node, source_bytes: bytes) -> str | None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return None
        return self._text(name_node, source_bytes)

    def _text(self, node: Node, source_bytes: bytes) -> str:
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _range(self, node: Node) -> dict[str, int]:
        return {
            "start_line": node.start_point.row + 1,
            "start_column": node.start_point.column,
            "end_line": node.end_point.row + 1,
            "end_column": node.end_point.column,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
        }

    def _module_name(self, relative_path: str) -> str:
        path = Path(relative_path)
        parts = list(path.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts) if parts else "__init__"

    def _parse_import_statement(self, statement: str) -> list[dict[str, str | None]]:
        if statement.startswith("from "):
            match = re.match(r"from\s+(?P<module>[\w.]+)\s+import\s+(?P<names>.+)$", statement)
            if not match:
                return [{"name": statement, "alias": None, "from": None}]
            from_module = match.group("module")
            return [
                {"name": name, "alias": alias, "from": from_module}
                for name, alias in self._split_import_names(match.group("names"))
            ]

        match = re.match(r"import\s+(?P<names>.+)$", statement)
        if not match:
            return [{"name": statement, "alias": None, "from": None}]
        return [
            {"name": name, "alias": alias, "from": None}
            for name, alias in self._split_import_names(match.group("names"))
        ]

    def _split_import_names(self, names: str) -> list[tuple[str, str | None]]:
        parsed = []
        for raw_name in names.split(","):
            item = raw_name.strip()
            if " as " in item:
                name, alias = item.split(" as ", 1)
                parsed.append((name.strip(), alias.strip()))
            else:
                parsed.append((item, None))
        return parsed

    def _sort_key(self, item: dict[str, Any]) -> tuple[Any, ...]:
        source_range = item.get("range") or {}
        return (
            item.get("file_path", ""),
            source_range.get("start_line", 0),
            source_range.get("start_column", 0),
            item.get("qualname") or item.get("name") or item.get("statement") or "",
        )
