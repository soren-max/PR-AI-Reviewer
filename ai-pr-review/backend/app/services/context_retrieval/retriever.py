"""
Context Retrieval Engine.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.symbol_index import CodeSymbolIndexService
from app.services.tree_sitter import TreeSitterService


class ContextRetriever:
    """Build Review Agent-ready context packages for changed files."""

    _README_CANDIDATES = ("README.md", "ai-pr-review/README.md")
    _ARCHITECTURE_CANDIDATES = (
        "ai-pr-review/docs/architecture.md",
        "docs/architecture.md",
        "docs/ARCHITECTURE.md",
        "ARCHITECTURE.md",
    )

    def __init__(
        self,
        symbol_index_service: CodeSymbolIndexService | None = None,
        tree_sitter_service: TreeSitterService | None = None,
        *,
        doc_excerpt_chars: int = 4000,
    ) -> None:
        self._symbol_index_service = symbol_index_service or CodeSymbolIndexService()
        self._tree_sitter_service = tree_sitter_service or TreeSitterService()
        self._doc_excerpt_chars = doc_excerpt_chars

    def retrieve(
        self,
        repository_root: str | Path,
        changed_file: str | Path,
        *,
        symbol_index: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic context package for a changed file."""
        root = Path(repository_root).resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Repository root does not exist: {root}")

        changed_path = self._resolve_changed_file(root, changed_file)
        relative_path = changed_path.relative_to(root).as_posix()
        if changed_path.suffix != ".py":
            raise ValueError("ContextRetriever currently supports Python changed files only")

        index = symbol_index or self._symbol_index_service.build_index(root)
        file_functions = self._items_for_file(index, "functions", relative_path)
        file_classes = self._items_for_file(index, "classes", relative_path)
        file_imports = self._items_for_file(index, "imports", relative_path)

        related_files = self._related_files(
            index,
            changed_file=relative_path,
            file_imports=file_imports,
        )
        source = changed_path.read_text(encoding="utf-8")
        ast = self._tree_sitter_service.parse_source(source, language="python")

        return {
            "version": 1,
            "changed_file": relative_path,
            "language": "python",
            "source": {
                "line_count": len(source.splitlines()),
                "has_parse_error": ast["has_error"],
                "ast_root": ast["ast"]["type"],
            },
            "related_functions": file_functions,
            "related_classes": file_classes,
            "related_imports": file_imports,
            "related_files": related_files,
            "readme": self._document_context(root, self._README_CANDIDATES),
            "architecture": self._document_context(root, self._ARCHITECTURE_CANDIDATES),
        }

    def build_state_update(self, state: dict[str, Any]) -> dict[str, Any]:
        """Return a Review Agent / LangGraph-compatible additive state update."""
        repository_root = state.get("repository_root") or state.get("repo_path")
        changed_file = state.get("changed_file")
        if not repository_root:
            raise ValueError("state must include 'repository_root' or 'repo_path'")
        if not changed_file:
            raise ValueError("state must include 'changed_file'")

        return {
            "context_package": self.retrieve(
                repository_root,
                changed_file,
                symbol_index=state.get("symbol_index"),
            )
        }

    def _resolve_changed_file(self, root: Path, changed_file: str | Path) -> Path:
        path = Path(changed_file)
        resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Changed file does not exist: {changed_file}")
        if not resolved.is_relative_to(root):
            raise ValueError("changed_file must be inside repository_root")
        return resolved

    def _items_for_file(
        self,
        symbol_index: dict[str, Any],
        key: str,
        relative_path: str,
    ) -> list[dict[str, Any]]:
        return [
            item
            for item in symbol_index.get(key, [])
            if item.get("file_path") == relative_path
        ]

    def _related_files(
        self,
        symbol_index: dict[str, Any],
        *,
        changed_file: str,
        file_imports: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        modules_by_name = {
            module["module"]: module
            for module in symbol_index.get("modules", [])
        }
        changed_module = next(
            (
                module
                for module in symbol_index.get("modules", [])
                if module.get("file_path") == changed_file
            ),
            None,
        )
        related: dict[str, dict[str, Any]] = {}

        if changed_module:
            self._add_related_file(related, changed_module, reason="changed_file")
            package_prefix = self._package_prefix(changed_module["module"])
            for module in symbol_index.get("modules", []):
                if (
                    module.get("file_path") != changed_file
                    and package_prefix
                    and module.get("module", "").startswith(package_prefix)
                ):
                    self._add_related_file(related, module, reason="same_package")

        for import_item in file_imports:
            for imported in import_item.get("imports", []):
                for module_name in self._candidate_module_names(imported):
                    module = modules_by_name.get(module_name)
                    if module:
                        self._add_related_file(related, module, reason="import")

        return sorted(related.values(), key=lambda item: (item["file_path"], item["reason"]))

    def _add_related_file(
        self,
        related: dict[str, dict[str, Any]],
        module: dict[str, Any],
        *,
        reason: str,
    ) -> None:
        reason_priority = {"changed_file": 3, "import": 2, "same_package": 1}
        file_path = module["file_path"]
        current = related.get(file_path)
        if current is None:
            related[file_path] = {
                "file_path": file_path,
                "module": module["module"],
                "reason": reason,
            }
            return
        if reason_priority[reason] > reason_priority[current["reason"]]:
            current["reason"] = reason

    def _package_prefix(self, module_name: str) -> str:
        if "." not in module_name:
            return ""
        return module_name.rsplit(".", 1)[0] + "."

    def _candidate_module_names(self, imported: dict[str, str | None]) -> list[str]:
        from_module = imported.get("from")
        name = imported.get("name")
        candidates = []
        if from_module:
            candidates.append(from_module)
            if name:
                candidates.append(f"{from_module}.{name}")
        elif name:
            candidates.append(name)
        return candidates

    def _document_context(
        self,
        root: Path,
        candidates: tuple[str, ...],
    ) -> dict[str, Any]:
        for candidate in candidates:
            path = root / candidate
            if path.exists() and path.is_file():
                text = path.read_text(encoding="utf-8")
                return {
                    "available": True,
                    "file_path": candidate,
                    "excerpt": text[: self._doc_excerpt_chars],
                    "truncated": len(text) > self._doc_excerpt_chars,
                }
        return {
            "available": False,
            "file_path": None,
            "excerpt": "",
            "truncated": False,
        }
