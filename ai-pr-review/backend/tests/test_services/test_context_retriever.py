"""
Unit tests for the Context Retrieval Engine.
"""
import json

import pytest

from app.services.context_retrieval import ContextRetriever


def _write_project(root):
    (root / "README.md").write_text("# Project\n\nUsage notes\n", encoding="utf-8")
    docs = root / "ai-pr-review" / "docs"
    docs.mkdir(parents=True)
    (docs / "architecture.md").write_text("# Architecture\n\nService boundaries\n", encoding="utf-8")
    package = root / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "class Helper:\n"
        "    pass\n",
        encoding="utf-8",
    )
    (package / "changed.py").write_text(
        "from pkg.helpers import Helper\n"
        "\n"
        "class Changed:\n"
        "    def run(self):\n"
        "        return Helper()\n"
        "\n"
        "def top_level():\n"
        "    return Changed()\n",
        encoding="utf-8",
    )


def test_context_retriever_builds_context_package(tmp_path):
    _write_project(tmp_path)

    package = ContextRetriever().retrieve(tmp_path, "pkg/changed.py")

    assert package["changed_file"] == "pkg/changed.py"
    assert package["source"] == {
        "line_count": 8,
        "has_parse_error": False,
        "ast_root": "module",
    }
    assert [item["qualname"] for item in package["related_functions"]] == [
        "Changed.run",
        "top_level",
    ]
    assert [item["qualname"] for item in package["related_classes"]] == ["Changed"]
    assert package["related_imports"][0]["imports"] == [
        {"name": "Helper", "alias": None, "from": "pkg.helpers"}
    ]
    assert package["related_files"] == [
        {"file_path": "pkg/changed.py", "module": "pkg.changed", "reason": "changed_file"},
        {"file_path": "pkg/helpers.py", "module": "pkg.helpers", "reason": "import"},
    ]
    assert package["readme"]["available"] is True
    assert package["architecture"]["available"] is True
    json.dumps(package)


def test_context_retriever_uses_existing_symbol_index(tmp_path):
    _write_project(tmp_path)
    retriever = ContextRetriever()
    symbol_index = retriever._symbol_index_service.build_index(tmp_path)

    package = retriever.retrieve(tmp_path, "pkg/changed.py", symbol_index=symbol_index)

    assert package["related_classes"][0]["name"] == "Changed"


def test_context_retriever_builds_review_agent_state_update(tmp_path):
    _write_project(tmp_path)

    update = ContextRetriever().build_state_update({
        "repository_root": tmp_path,
        "changed_file": "pkg/changed.py",
    })

    assert list(update) == ["context_package"]
    assert update["context_package"]["changed_file"] == "pkg/changed.py"


def test_context_retriever_handles_missing_docs(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "changed.py").write_text("def only():\n    pass\n", encoding="utf-8")

    context = ContextRetriever().retrieve(tmp_path, "pkg/changed.py")

    assert context["readme"] == {
        "available": False,
        "file_path": None,
        "excerpt": "",
        "truncated": False,
    }
    assert context["architecture"]["available"] is False


def test_context_retriever_rejects_missing_changed_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ContextRetriever().retrieve(tmp_path, "missing.py")


def test_context_retriever_rejects_changed_file_outside_repo(tmp_path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("def nope():\n    pass\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inside repository_root"):
        ContextRetriever().retrieve(tmp_path, outside)


def test_context_retriever_state_update_requires_changed_file(tmp_path):
    with pytest.raises(ValueError, match="changed_file"):
        ContextRetriever().build_state_update({"repository_root": tmp_path})
