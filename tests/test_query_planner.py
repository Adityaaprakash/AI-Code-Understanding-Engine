"""Unit and integration test suite for Phase 6A Query Intent & Query Planning."""

import time

import pytest
from pydantic import ValidationError

from llm.enums import (
    AnswerStyle,
    GraphStrategy,
    QueryIntent,
    QueryScope,
    RelationshipType,
    RetrievalStrategy,
)
from llm.exceptions import InvalidQueryError
from llm.planner_models import QueryPlan
from llm.query_planner import QueryPlanner
from retrieval.query_processor import QueryPreprocessor


@pytest.fixture
def planner() -> QueryPlanner:
    """Fixture providing a fresh QueryPlanner instance."""
    return QueryPlanner()


@pytest.fixture
def preprocessor() -> QueryPreprocessor:
    """Fixture providing a fresh QueryPreprocessor instance."""
    return QueryPreprocessor()


class TestQueryPlannerScenarios:
    """Tests covering the 12 primary query scenarios (A-L)."""

    def test_scenario_a_callers(self, planner: QueryPlanner) -> None:
        """Scenario A: Who calls PaymentService?"""
        plan = planner.plan("Who calls PaymentService?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.CALLERS
        assert plan.graph_strategy == GraphStrategy.CALLERS
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "PaymentService" in plan.target_entities
        assert "EXPLICIT_CALLER_PHRASE" in plan.reason_codes
        assert plan.confidence >= 0.85

    def test_scenario_b_callees(self, planner: QueryPlanner) -> None:
        """Scenario B: What functions does PaymentService call?"""
        plan = planner.plan("What functions does PaymentService call?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.CALLS
        assert plan.graph_strategy == GraphStrategy.CALLEES
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "PaymentService" in plan.target_entities
        assert "EXPLICIT_CALLEE_PHRASE" in plan.reason_codes

    def test_scenario_c_dependents(self, planner: QueryPlanner) -> None:
        """Scenario C: Which components depend on AuthService?"""
        plan = planner.plan("Which components depend on AuthService?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.DEPENDENTS
        assert plan.graph_strategy == GraphStrategy.DEPENDENTS
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "AuthService" in plan.target_entities
        assert "EXPLICIT_DEPENDENCY_PHRASE" in plan.reason_codes

    def test_scenario_d_dependencies(self, planner: QueryPlanner) -> None:
        """Scenario D: What does OrderService depend on?"""
        plan = planner.plan("What does OrderService depend on?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.DEPENDENCIES
        assert plan.graph_strategy == GraphStrategy.DEPENDENCIES
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "OrderService" in plan.target_entities

    def test_scenario_e_implementations(self, planner: QueryPlanner) -> None:
        """Scenario E: Which classes implement PaymentProcessor?"""
        plan = planner.plan("Which classes implement PaymentProcessor?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.IMPLEMENTS
        assert plan.graph_strategy == GraphStrategy.IMPLEMENTATIONS
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "PaymentProcessor" in plan.target_entities
        assert "EXPLICIT_IMPLEMENTS_PHRASE" in plan.reason_codes

    def test_scenario_f_inheritance(self, planner: QueryPlanner) -> None:
        """Scenario F: Which classes extend BaseController?"""
        plan = planner.plan("Which classes extend BaseController?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.EXTENDS
        assert plan.graph_strategy == GraphStrategy.INHERITANCE
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "BaseController" in plan.target_entities
        assert "EXPLICIT_EXTENDS_PHRASE" in plan.reason_codes

    def test_scenario_g_imports(self, planner: QueryPlanner) -> None:
        """Scenario G: Which modules import utils.py?"""
        plan = planner.plan("Which modules import utils.py?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.IMPORTS
        assert plan.graph_strategy == GraphStrategy.IMPORTS
        assert plan.scope == QueryScope.FILE
        assert "utils.py" in plan.target_entities

    def test_scenario_h_uses(self, planner: QueryPlanner) -> None:
        """Scenario H: Where is validate_token used?"""
        plan = planner.plan("Where is validate_token used?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.USES
        assert plan.graph_strategy == GraphStrategy.USAGES
        assert plan.answer_style == AnswerStyle.RELATIONSHIP
        assert "validate_token" in plan.target_entities
        assert "EXPLICIT_USES_PHRASE" in plan.reason_codes

    def test_scenario_i_impact(self, planner: QueryPlanner) -> None:
        """Scenario I: What would break if AuthService changed?"""
        plan = planner.plan("What would break if AuthService changed?")
        assert plan.primary_intent == QueryIntent.IMPACT
        assert plan.relationship_type == RelationshipType.IMPACT
        assert plan.graph_strategy == GraphStrategy.IMPACT_RADIUS
        assert plan.answer_style == AnswerStyle.IMPACT_ANALYSIS
        assert "AuthService" in plan.target_entities
        assert "EXPLICIT_IMPACT_PHRASE" in plan.reason_codes

    def test_scenario_j_symbol(self, planner: QueryPlanner) -> None:
        """Scenario J: Pure symbol or definition lookup."""
        plan_pure = planner.plan("PaymentService")
        assert plan_pure.primary_intent == QueryIntent.SYMBOL
        assert plan_pure.scope == QueryScope.SYMBOL
        assert plan_pure.answer_style == AnswerStyle.CODE_LOCATION
        assert plan_pure.retrieval_strategy == RetrievalStrategy.LEXICAL
        assert "PaymentService" in plan_pure.target_entities

        plan_def = planner.plan("Where is PaymentService defined?")
        assert plan_def.primary_intent == QueryIntent.SYMBOL
        assert plan_def.answer_style == AnswerStyle.CODE_LOCATION
        assert "PaymentService" in plan_def.target_entities

    def test_scenario_k_architecture(self, planner: QueryPlanner) -> None:
        """Scenario K: Explain the authentication system architecture."""
        plan = planner.plan("Explain the authentication system architecture")
        assert plan.primary_intent == QueryIntent.ARCHITECTURE
        assert plan.graph_strategy == GraphStrategy.ARCHITECTURAL_EXPANSION
        assert plan.scope == QueryScope.REPOSITORY
        assert plan.answer_style == AnswerStyle.ARCHITECTURE

    def test_scenario_l_debugging(self, planner: QueryPlanner) -> None:
        """Scenario L: Why is processPayment failing?"""
        plan = planner.plan("Why is processPayment failing?")
        assert plan.primary_intent == QueryIntent.DEBUGGING
        assert plan.answer_style == AnswerStyle.DEBUGGING_ANALYSIS
        assert "processPayment" in plan.target_entities
        assert "EXPLICIT_DEBUGGING_PHRASE" in plan.reason_codes


class TestTargetEntityExtraction:
    """Tests verifying accurate target entity and symbol extraction."""

    def test_qualified_name_extraction(self, planner: QueryPlanner) -> None:
        """Test dot-separated qualified names."""
        plan = planner.plan("Who calls com.example.payment.PaymentService.processPayment?")
        assert any("PaymentService" in e or "processPayment" in e for e in plan.target_entities)

    def test_pascal_camel_snake_case_entities(self, planner: QueryPlanner) -> None:
        """Test PascalCase, camelCase, and snake_case identifiers."""
        plan = planner.plan("How does payment_processor processOrder using UserSession?")
        assert "payment_processor" in plan.target_entities
        assert "processOrder" in plan.target_entities
        assert "UserSession" in plan.target_entities

    def test_file_path_entities(self, planner: QueryPlanner) -> None:
        """Test extraction of file paths."""
        plan = planner.plan("What depends on src/auth/AuthService.java?")
        assert any("AuthService.java" in e for e in plan.target_entities)
        assert plan.scope == QueryScope.FILE


class TestScopeDetermination:
    """Tests verifying granular code scope assignment."""

    def test_file_scope(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Show contents of src/controllers/user.py")
        assert plan.scope == QueryScope.FILE

    def test_class_scope(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Which class implements UserDetailsService?")
        assert plan.scope in (QueryScope.CLASS, QueryScope.SYMBOL)

    def test_repository_scope(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Give an overview of the codebase architecture")
        assert plan.scope == QueryScope.REPOSITORY

    def test_package_scope(self, planner: QueryPlanner) -> None:
        plan = planner.plan("What modules are in the com.example.auth package?")
        assert plan.scope == QueryScope.PACKAGE


class TestCompoundQueriesAndPrecedence:
    """Tests for multi-part/compound queries and secondary intent classification."""

    def test_compound_query_callers_and_explanation(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Who calls PaymentService and explain how it processes payments?")
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.CALLERS
        assert QueryIntent.EXPLANATION in plan.secondary_intents
        assert len(plan.operations) >= 1

    def test_compound_query_explanation_and_impact(self, planner: QueryPlanner) -> None:
        plan = planner.plan(
            "How does authentication work and what would break if AuthService changed?"
        )
        assert plan.primary_intent in (QueryIntent.EXPLANATION, QueryIntent.IMPACT)
        assert len(plan.reason_codes) >= 2


class TestNegationDetection:
    """Tests for detecting negation in queries."""

    def test_negation_detected(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Which modules do not depend on AuthService?")
        assert plan.has_negation is True
        assert "NEGATION_DETECTED" in plan.reason_codes

    def test_no_negation(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Which modules depend on AuthService?")
        assert plan.has_negation is False
        assert "NEGATION_DETECTED" not in plan.reason_codes


class TestErrorAndValidationHandling:
    """Tests for input validation and error raising."""

    def test_empty_string_raises_invalid_query_error(self, planner: QueryPlanner) -> None:
        with pytest.raises(InvalidQueryError, match="cannot be empty"):
            planner.plan("")

    def test_whitespace_string_raises_invalid_query_error(self, planner: QueryPlanner) -> None:
        with pytest.raises(InvalidQueryError, match="cannot be empty"):
            planner.plan("   \n\t  ")

    def test_none_input_raises_invalid_query_error(self, planner: QueryPlanner) -> None:
        with pytest.raises(InvalidQueryError):
            planner.plan(None)  # type: ignore[arg-type]


class TestImmutabilityAndSerialization:
    """Tests verifying model immutability and lossless JSON serialization."""

    def test_query_plan_is_frozen(self, planner: QueryPlanner) -> None:
        plan = planner.plan("Who calls PaymentService?")
        with pytest.raises(ValidationError):
            plan.primary_intent = QueryIntent.EXPLANATION

    def test_json_roundtrip_lossless(self, planner: QueryPlanner) -> None:
        plan = planner.plan("What would break if AuthService changed?")
        json_str = plan.model_dump_json()
        deserialized = QueryPlan.model_validate_json(json_str)

        assert deserialized.query == plan.query
        assert deserialized.normalized_query == plan.normalized_query
        assert deserialized.primary_intent == plan.primary_intent
        assert deserialized.relationship_type == plan.relationship_type
        assert deserialized.graph_strategy == plan.graph_strategy
        assert deserialized.target_entities == plan.target_entities
        assert deserialized.reason_codes == plan.reason_codes
        assert deserialized.has_negation == plan.has_negation


class TestDeterminismAndPerformance:
    """Tests verifying 100% determinism and sub-millisecond execution time."""

    def test_100_percent_determinism(self, planner: QueryPlanner) -> None:
        query = "Who calls PaymentService and what would break if it changed?"
        base_json = planner.plan(query).model_dump_json()

        for _ in range(100):
            run_json = planner.plan(query).model_dump_json()
            assert run_json == base_json

    def test_sub_millisecond_latency(self, planner: QueryPlanner) -> None:
        query = "Which classes implement PaymentProcessor and what depends on AuthService?"
        start = time.perf_counter()
        for _ in range(100):
            planner.plan(query)
        elapsed_ms = ((time.perf_counter() - start) * 1000.0) / 100.0

        # Average latency must be < 1.0 ms
        assert elapsed_ms < 1.0, (
            f"Average planning latency was {elapsed_ms:.4f} ms (expected < 1.0 ms)"
        )


class TestProcessedQueryIntegration:
    """Test using preprocessed ProcessedQuery directly as input."""

    def test_plan_with_processed_query(
        self, planner: QueryPlanner, preprocessor: QueryPreprocessor
    ) -> None:
        processed = preprocessor.process("Who calls PaymentService?")
        plan = planner.plan(processed)
        assert plan.query == "Who calls PaymentService?"
        assert plan.primary_intent == QueryIntent.DEPENDENCY
        assert plan.relationship_type == RelationshipType.CALLERS
