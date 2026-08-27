"""Tests for TASK-2A Parser Abstraction contract, models, and language stubs."""

import pytest

from code_analyzer.parsers import (
    DiagnosticSeverity,
    JavaParser,
    Language,
    LanguageParser,
    ParseDiagnostic,
    ParseResult,
    PythonParser,
    TypeScriptParser,
)


@pytest.mark.unit
def test_java_language_representation() -> None:
    """Verify Java language representation in Language enum."""
    assert Language.JAVA == "java"
    assert isinstance(Language.JAVA, str)
    assert Language("java") == Language.JAVA


@pytest.mark.unit
def test_python_language_representation() -> None:
    """Verify Python language representation in Language enum."""
    assert Language.PYTHON == "python"
    assert isinstance(Language.PYTHON, str)
    assert Language("python") == Language.PYTHON


@pytest.mark.unit
def test_typescript_language_representation() -> None:
    """Verify TypeScript language representation in Language enum."""
    assert Language.TYPESCRIPT == "typescript"
    assert isinstance(Language.TYPESCRIPT, str)
    assert Language("typescript") == Language.TYPESCRIPT


@pytest.mark.unit
def test_parser_interface_contract() -> None:
    """Verify LanguageParser interface contract enforcement."""
    # Attempting to instantiate abstract class without implementing abstract members must fail
    with pytest.raises(TypeError):
        LanguageParser()  # type: ignore[abstract]

    class IncompleteParser(LanguageParser):
        pass

    with pytest.raises(TypeError):
        IncompleteParser()  # type: ignore[abstract]


@pytest.mark.unit
def test_parser_result_success_representation() -> None:
    """Verify success state representation in ParseResult."""
    result = ParseResult.create_success(
        language=Language.PYTHON,
        ast={"type": "Module", "body": []},
        source_path="main.py",
    )

    assert result.success is True
    assert result.language == Language.PYTHON
    assert result.source_path == "main.py"
    assert result.ast == {"type": "Module", "body": []}
    assert result.diagnostics == []
    assert result.has_errors is False


@pytest.mark.unit
def test_parser_failure_diagnostic_representation() -> None:
    """Verify failure state and diagnostic representation in ParseResult."""
    diag1 = ParseDiagnostic(
        message="SyntaxError: invalid syntax",
        line=12,
        column=4,
        severity=DiagnosticSeverity.ERROR,
        kind="syntax_error",
    )
    diag2 = ParseDiagnostic(
        message="Unexpected token",
        line=15,
        severity=DiagnosticSeverity.FATAL,
        kind="parser_failure",
    )

    result = ParseResult.create_failure(
        language=Language.JAVA,
        diagnostics=[diag1, diag2],
        source_path="App.java",
    )

    assert result.success is False
    assert result.language == Language.JAVA
    assert result.source_path == "App.java"
    assert result.ast is None
    assert len(result.diagnostics) == 2
    assert result.diagnostics[0].line == 12
    assert result.diagnostics[0].column == 4
    assert result.diagnostics[0].kind == "syntax_error"
    assert result.has_errors is True


@pytest.mark.unit
def test_language_parser_stubs() -> None:
    """Verify concrete language parser stubs adhere to contract."""
    parsers: list[LanguageParser] = [
        JavaParser(),
        PythonParser(),
        TypeScriptParser(),
    ]

    expected_languages = [Language.JAVA, Language.PYTHON, Language.TYPESCRIPT]

    for parser, expected_lang in zip(parsers, expected_languages, strict=True):
        assert isinstance(parser, LanguageParser)
        assert parser.language == expected_lang

        # Test stub parse call preserves contract
        res = parser.parse("class Test {}", source_path=f"test.{expected_lang}")
        assert isinstance(res, ParseResult)
        assert res.language == expected_lang
        assert res.source_path == f"test.{expected_lang}"
        assert res.success is True
