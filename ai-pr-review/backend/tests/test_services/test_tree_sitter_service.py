"""
Unit tests for the Tree-sitter parser service.
"""
import pytest

from app.services.tree_sitter import (
    ParserFactory,
    TreeSitterService,
    UnsupportedLanguageError,
)


def test_parser_factory_creates_python_parser():
    parser = ParserFactory.create("python")

    assert parser is not None
    assert ParserFactory.available_languages() == ("python",)
    assert ParserFactory.reserved_languages() == ("go", "java", "typescript")


def test_tree_sitter_service_returns_python_ast():
    service = TreeSitterService()

    result = service.parse_source(
        "def add(left, right):\n"
        "    return left + right\n",
        language="py",
    )

    assert result["language"] == "python"
    assert result["has_error"] is False
    assert result["ast"]["type"] == "module"
    assert result["ast"]["children"][0]["type"] == "function_definition"
    assert result["ast"]["children"][0]["start_point"] == {"row": 0, "column": 0}


def test_tree_sitter_service_reports_python_syntax_errors():
    service = TreeSitterService()

    result = service.parse_source("def broken(:\n    pass\n")

    assert result["language"] == "python"
    assert result["has_error"] is True
    assert result["ast"]["has_error"] is True


@pytest.mark.parametrize("language", ["java", "go", "typescript"])
def test_parser_factory_rejects_reserved_languages(language):
    with pytest.raises(UnsupportedLanguageError, match="reserved"):
        ParserFactory.create(language)


def test_parser_factory_rejects_unknown_languages():
    with pytest.raises(UnsupportedLanguageError, match="Unsupported"):
        ParserFactory.create("ruby")
