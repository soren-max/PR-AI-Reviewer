"""
Parser factory for Tree-sitter language parsers.
"""
from enum import StrEnum

from tree_sitter import Language, Parser
import tree_sitter_python


class UnsupportedLanguageError(ValueError):
    """Raised when no Tree-sitter parser is available for a language."""


class SupportedLanguage(StrEnum):
    """Languages known by the parser boundary.

    Only Python is enabled in Sprint4 PR1. The remaining values reserve stable
    extension points for follow-up parser grammar packages.
    """

    PYTHON = "python"
    JAVA = "java"
    GO = "go"
    TYPESCRIPT = "typescript"


class ParserFactory:
    """Create Tree-sitter parsers for supported languages."""

    _AVAILABLE_LANGUAGES = {SupportedLanguage.PYTHON}
    _RESERVED_LANGUAGES = {
        SupportedLanguage.JAVA,
        SupportedLanguage.GO,
        SupportedLanguage.TYPESCRIPT,
    }

    @classmethod
    def create(cls, language: str | SupportedLanguage) -> Parser:
        """Return a configured Tree-sitter parser for a language."""
        normalized_language = cls.normalize_language(language)
        if normalized_language == SupportedLanguage.PYTHON:
            return Parser(Language(tree_sitter_python.language()))

        if normalized_language in cls._RESERVED_LANGUAGES:
            raise UnsupportedLanguageError(
                f"Tree-sitter parser for {normalized_language.value!r} is reserved "
                "but not enabled in this release."
            )

        raise UnsupportedLanguageError(
            f"Unsupported Tree-sitter language: {str(language)!r}."
        )

    @classmethod
    def normalize_language(
        cls,
        language: str | SupportedLanguage,
    ) -> SupportedLanguage:
        """Normalize aliases and validate that a language is known."""
        value = str(language).strip().lower()
        aliases = {
            "py": SupportedLanguage.PYTHON,
            "python": SupportedLanguage.PYTHON,
            "java": SupportedLanguage.JAVA,
            "golang": SupportedLanguage.GO,
            "go": SupportedLanguage.GO,
            "ts": SupportedLanguage.TYPESCRIPT,
            "typescript": SupportedLanguage.TYPESCRIPT,
        }
        try:
            return aliases[value]
        except KeyError as exc:
            raise UnsupportedLanguageError(
                f"Unsupported Tree-sitter language: {value!r}."
            ) from exc

    @classmethod
    def available_languages(cls) -> tuple[str, ...]:
        """Return languages that can parse source in this release."""
        return tuple(language.value for language in sorted(cls._AVAILABLE_LANGUAGES))

    @classmethod
    def reserved_languages(cls) -> tuple[str, ...]:
        """Return languages reserved for future parser grammar support."""
        return tuple(language.value for language in sorted(cls._RESERVED_LANGUAGES))
