"""Canonical Code IR normalization layer.

Translates language-specific AST models (Java, Python, TypeScript) into language-independent
Canonical Code IR entities.
"""

from code_analyzer.ir import EntityKind, File, generate_entity_id
from code_analyzer.normalization.base import ASTNormalizer
from code_analyzer.normalization.java import JavaNormalizer
from code_analyzer.normalization.python import PythonNormalizer
from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.normalization.typescript import TypeScriptNormalizer
from code_analyzer.parsers.models import Language, ParseResult


def normalize_parse_result(
    parse_result: ParseResult,
    repository_id: str,
    file_path: str | None = None,
    content_hash: str | None = None,
    loc: int = 0,
) -> NormalizationResult:
    """Normalize a LanguageParser ParseResult into Canonical Code IR.

    Args:
        parse_result: Output from a LanguageParser parse() call.
        repository_id: Stable identifier for the parent repository.
        file_path: Optional relative source file path (defaults to parse_result.file_path).
        content_hash: Optional SHA-256 content hash of the source file.
        loc: Optional total lines of code count.

    Returns:
        NormalizationResult containing canonical File, Module, Class, Function, Method,
        Variable, Parameter, Reference, and Symbol entities.

    Raises:
        ValueError: If an unsupported language parser result is provided.
    """
    resolved_path = file_path or parse_result.source_path or "unknown"

    if not parse_result.success or parse_result.ast is None:
        file_id = generate_entity_id(
            EntityKind.FILE, resolved_path, resolved_path, parent_id=repository_id
        )
        file_entity = File(
            id=file_id,
            repository_id=repository_id,
            path=resolved_path,
            language=parse_result.language,
            content_hash=content_hash,
            loc=loc,
        )
        return NormalizationResult(
            file=file_entity,
            diagnostics=list(parse_result.diagnostics),
        )

    if parse_result.language == Language.JAVA:
        normalizer = JavaNormalizer()
        res = normalizer.normalize(
            parse_result.ast,
            repository_id=repository_id,
            file_path=resolved_path,
            language=Language.JAVA,
            content_hash=content_hash,
            loc=loc,
        )
    elif parse_result.language == Language.PYTHON:
        normalizer = PythonNormalizer()
        res = normalizer.normalize(
            parse_result.ast,
            repository_id=repository_id,
            file_path=resolved_path,
            language=Language.PYTHON,
            content_hash=content_hash,
            loc=loc,
        )
    elif parse_result.language == Language.TYPESCRIPT:
        normalizer = TypeScriptNormalizer()
        res = normalizer.normalize(
            parse_result.ast,
            repository_id=repository_id,
            file_path=resolved_path,
            language=Language.TYPESCRIPT,
            content_hash=content_hash,
            loc=loc,
        )
    else:
        raise ValueError(f"Unsupported language for IR normalization: {parse_result.language}")

    if parse_result.diagnostics:
        merged_diags = list(res.diagnostics) + list(parse_result.diagnostics)
        return NormalizationResult(
            file=res.file,
            modules=res.modules,
            classes=res.classes,
            interfaces=res.interfaces,
            functions=res.functions,
            methods=res.methods,
            variables=res.variables,
            parameters=res.parameters,
            references=res.references,
            symbols=res.symbols,
            diagnostics=merged_diags,
        )

    return res


__all__ = [
    "ASTNormalizer",
    "JavaNormalizer",
    "NormalizationResult",
    "PythonNormalizer",
    "TypeScriptNormalizer",
    "normalize_parse_result",
]
