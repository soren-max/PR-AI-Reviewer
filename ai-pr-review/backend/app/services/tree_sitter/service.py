"""
Tree-sitter AST service.
"""
from typing import Any

from tree_sitter import Node

from app.services.tree_sitter.parser_factory import ParserFactory


class TreeSitterService:
    """Parse source text and expose a serializable AST."""

    def __init__(self, parser_factory: type[ParserFactory] = ParserFactory) -> None:
        self._parser_factory = parser_factory

    def parse_source(
        self,
        source: str,
        language: str = "python",
        *,
        include_anonymous_nodes: bool = False,
    ) -> dict[str, Any]:
        """Parse source code and return a deterministic AST dictionary."""
        normalized_language = self._parser_factory.normalize_language(language)
        parser = self._parser_factory.create(normalized_language)
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        root = tree.root_node

        return {
            "language": normalized_language.value,
            "has_error": root.has_error,
            "ast": self._node_to_dict(
                root,
                include_anonymous_nodes=include_anonymous_nodes,
            ),
        }

    def _node_to_dict(
        self,
        node: Node,
        *,
        include_anonymous_nodes: bool,
    ) -> dict[str, Any]:
        children = [
            self._node_to_dict(child, include_anonymous_nodes=include_anonymous_nodes)
            for child in node.children
            if include_anonymous_nodes or child.is_named
        ]
        return {
            "type": node.type,
            "named": node.is_named,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "start_point": {
                "row": node.start_point.row,
                "column": node.start_point.column,
            },
            "end_point": {
                "row": node.end_point.row,
                "column": node.end_point.column,
            },
            "has_error": node.has_error,
            "children": children,
        }
