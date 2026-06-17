"""
Unit tests for the Code Symbol Index service.
"""
import json

import pytest

from app.services.symbol_index import CodeSymbolIndexService


def test_symbol_index_scans_repository_python_symbols(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "sample.py").write_text(
        "import os\n"
        "from pathlib import Path as P\n"
        "\n"
        "class Greeter:\n"
        "    def hello(self):\n"
        "        return P.cwd()\n"
        "\n"
        "def top_level():\n"
        "    return os.getcwd()\n",
        encoding="utf-8",
    )

    index = CodeSymbolIndexService().build_index(tmp_path)

    assert index["summary"] == {
        "module_count": 2,
        "function_count": 2,
        "class_count": 1,
        "import_count": 2,
        "error_count": 0,
    }
    assert [module["module"] for module in index["modules"]] == ["pkg", "pkg.sample"]
    assert [item["qualname"] for item in index["classes"]] == ["Greeter"]
    assert [item["qualname"] for item in index["functions"]] == [
        "Greeter.hello",
        "top_level",
    ]
    assert index["functions"][0]["kind"] == "method"
    assert index["functions"][0]["parent_class"] == "Greeter"
    assert index["functions"][1]["range"]["start_line"] == 8
    assert index["imports"][1]["imports"] == [
        {"name": "Path", "alias": "P", "from": "pathlib"}
    ]


def test_symbol_index_outputs_deterministic_json(tmp_path):
    (tmp_path / "b.py").write_text("def beta():\n    pass\n", encoding="utf-8")
    (tmp_path / "a.py").write_text("def alpha():\n    pass\n", encoding="utf-8")

    payload = CodeSymbolIndexService().build_index_json(tmp_path)
    decoded = json.loads(payload)

    assert [item["name"] for item in decoded["functions"]] == ["alpha", "beta"]
    assert payload == CodeSymbolIndexService().build_index_json(tmp_path)


def test_symbol_index_builds_langgraph_state_update(tmp_path):
    (tmp_path / "module.py").write_text("class Thing:\n    pass\n", encoding="utf-8")

    update = CodeSymbolIndexService().build_state_update({"repository_root": tmp_path})

    assert list(update) == ["symbol_index"]
    assert update["symbol_index"]["summary"]["class_count"] == 1


def test_symbol_index_skips_cache_and_vendor_directories(tmp_path):
    (tmp_path / "src.py").write_text("def included():\n    pass\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "ignored.py").write_text("def ignored():\n    pass\n", encoding="utf-8")
    vendor = tmp_path / "node_modules"
    vendor.mkdir()
    (vendor / "ignored.py").write_text("def ignored_too():\n    pass\n", encoding="utf-8")
    local_state = tmp_path / ".reasonix"
    local_state.mkdir()
    (local_state / "ignored.py").write_text("def ignored_local_state():\n    pass\n", encoding="utf-8")

    index = CodeSymbolIndexService().build_index(tmp_path)

    assert [item["name"] for item in index["functions"]] == ["included"]
    assert index["summary"]["module_count"] == 1


def test_symbol_index_reports_parse_errors(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

    index = CodeSymbolIndexService().build_index(tmp_path)

    assert index["modules"][0]["has_error"] is True
    assert index["summary"]["error_count"] == 1
    assert index["errors"][0]["type"] == "parse_error"


def test_symbol_index_rejects_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        CodeSymbolIndexService().build_index(tmp_path / "missing")


def test_symbol_index_state_update_requires_repository_root():
    with pytest.raises(ValueError, match="repository_root"):
        CodeSymbolIndexService().build_state_update({})
