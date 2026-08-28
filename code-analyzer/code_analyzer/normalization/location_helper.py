"""Helper function to convert parser-level SourceLocation to canonical IR SourceLocation."""

from typing import Any

from code_analyzer.ir import SourceLocation as IRSourceLocation


def to_ir_source_location(parser_loc: Any, file_path: str | None = None) -> IRSourceLocation | None:
    """Convert a parser-specific SourceLocation model to a canonical IR SourceLocation.

    Args:
        parser_loc: Language parser SourceLocation instance containing start_line,
          start_column, end_line, end_column.
        file_path: Optional relative source file path.

    Returns:
        Canonical IR SourceLocation object or None if parser_loc is invalid/absent.
    """
    if not parser_loc:
        return None

    return IRSourceLocation(
        file_path=file_path,
        start_line=parser_loc.start_line,
        start_column=parser_loc.start_column,
        end_line=parser_loc.end_line,
        end_column=parser_loc.end_column,
    )
