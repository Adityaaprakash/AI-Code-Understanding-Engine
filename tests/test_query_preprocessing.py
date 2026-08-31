"""Unit tests for search query preprocessing, normalization, identifier detection, and classification."""

import pytest
from pydantic import ValidationError

from retrieval.exceptions import LexicalQueryError
from retrieval.query_models import ProcessedQuery, QueryKind
from retrieval.query_processor import QueryPreprocessor


def test_query_preprocessor_initialization() -> None:
    """Verify preprocessor initializes with default tokenizer."""
    preprocessor = QueryPreprocessor()
    assert preprocessor.tokenizer is not None


def test_query_normalization_whitespace_and_unicode() -> None:
    """Verify whitespace collapsing, stripping, unicode NFC normalization, and case preservation."""
    preprocessor = QueryPreprocessor()
    raw = "  How   does   PaymentService\t\nprocessPayment?  "
    processed = preprocessor.process(raw)

    assert processed.original_query == raw
    assert processed.normalized_query == "How does PaymentService processPayment?"
    assert "PaymentService" in processed.identifier_tokens
    assert "processPayment" in processed.identifier_tokens


def test_empty_query_raises_lexical_query_error() -> None:
    """Verify empty or whitespace-only queries raise LexicalQueryError."""
    preprocessor = QueryPreprocessor()

    with pytest.raises(LexicalQueryError, match="cannot be empty or whitespace"):
        preprocessor.process("")

    with pytest.raises(LexicalQueryError, match="cannot be empty or whitespace"):
        preprocessor.process("   ")

    with pytest.raises(LexicalQueryError, match="cannot be empty or whitespace"):
        preprocessor.process("\n\t  ")

    with pytest.raises(LexicalQueryError, match="must be a string"):
        preprocessor.process(123)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("query", "expected_kind", "expected_identifiers"),
    [
        # Identifiers
        ("PaymentService", QueryKind.IDENTIFIER, ["PaymentService"]),
        ("AuthService", QueryKind.IDENTIFIER, ["AuthService"]),
        ("processPayment", QueryKind.IDENTIFIER, ["processPayment"]),
        ("get_user_by_id", QueryKind.IDENTIFIER, ["get_user_by_id"]),
        ("payment_service", QueryKind.IDENTIFIER, ["payment_service"]),
        ("JWTAuthenticationFilter", QueryKind.IDENTIFIER, ["JWTAuthenticationFilter"]),
        ("HTTPClient", QueryKind.IDENTIFIER, ["HTTPClient"]),
        # Qualified Identifiers
        (
            "PaymentService.processPayment",
            QueryKind.QUALIFIED_IDENTIFIER,
            ["PaymentService.processPayment"],
        ),
        (
            "com.example.payment.PaymentService",
            QueryKind.QUALIFIED_IDENTIFIER,
            ["com.example.payment.PaymentService"],
        ),
        # Paths / Files
        ("src/auth/AuthService.java", QueryKind.PATH_OR_FILE, ["AuthService.java"]),
        ("AuthService.java", QueryKind.PATH_OR_FILE, ["AuthService.java"]),
        # Natural Language
        ("How does authentication work?", QueryKind.NATURAL_LANGUAGE, []),
        ("How are payments processed?", QueryKind.NATURAL_LANGUAGE, []),
        ("Where is authentication implemented?", QueryKind.NATURAL_LANGUAGE, []),
        ("Which service handles payments?", QueryKind.NATURAL_LANGUAGE, []),
        # Relationship
        ("Who calls PaymentService?", QueryKind.RELATIONSHIP, ["PaymentService"]),
        ("Which classes depend on AuthService?", QueryKind.RELATIONSHIP, ["AuthService"]),
        # Mixed
        ("How does PaymentService process payments?", QueryKind.MIXED, ["PaymentService"]),
        ("Where does AuthService validate JWT?", QueryKind.MIXED, ["AuthService", "JWT"]),
    ],
)
def test_query_test_matrix_classification(
    query: str, expected_kind: QueryKind, expected_identifiers: list[str]
) -> None:
    """Golden matrix test verifying deterministic QueryKind classification and identifier detection."""
    preprocessor = QueryPreprocessor()
    processed = preprocessor.process(query)

    assert processed.query_kind == expected_kind
    for ident in expected_identifiers:
        assert ident in processed.identifier_tokens or ident in processed.qualified_name_candidates


def test_processed_query_immutability() -> None:
    """Verify ProcessedQuery is frozen and immutable."""
    preprocessor = QueryPreprocessor()
    processed = preprocessor.process("How does PaymentService work?")

    with pytest.raises(ValidationError):
        processed.original_query = "modified"

    with pytest.raises(ValidationError):
        processed.query_kind = QueryKind.UNKNOWN


def test_processed_query_json_serialization() -> None:
    """Verify ProcessedQuery object -> JSON -> object round-trip lossless serialization."""
    preprocessor = QueryPreprocessor()
    processed = preprocessor.process("PaymentService.processPayment")

    json_str = processed.model_dump_json()
    deserialized = ProcessedQuery.model_validate_json(json_str)

    assert deserialized == processed
    assert deserialized.original_query == processed.original_query
    assert deserialized.query_kind == QueryKind.QUALIFIED_IDENTIFIER
    assert deserialized.tokens == processed.tokens
