"""Phase 9A — Java Benchmark Queries."""

from benchmarks.fixtures.java_banking import CID, JAVA_REPO_ID, SID
from benchmarks.schema import (
    BenchmarkQuery,
    DifficultyLevel,
    ExpectedFact,
    GraphGroundTruth,
    GraphRelationship,
    MultiHopPath,
    MultiHopPathStep,
    QueryCategory,
    RelevanceGrade,
    RelevanceJudgment,
)

JAVA_QUERIES = [
    # ------------------ DEPENDENCY ------------------
    BenchmarkQuery(
        query_id="q-jv-005",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.DEPENDENCY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What components depend on PaymentService?",
        query_variants=["Where is PaymentService injected?", "Dependencies on PaymentService"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="CheckoutController injects PaymentService.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_impl_class"],
                grade=RelevanceGrade.MARGINAL,
                rationale="The implementation itself.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.USES,
                target_symbol_id=SID["PaymentService"],
            ),
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.USES,
                target_symbol_id=SID["OrderService"],
            ),
        ],
    ),
    BenchmarkQuery(
        query_id="q-jv-009",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.DEPENDENCY,
        difficulty=DifficultyLevel.EASY,
        query_text="What does CheckoutController use?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Checkout controller class definitions.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.USES,
                target_symbol_id=SID["PaymentService"],
            ),
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.USES,
                target_symbol_id=SID["OrderService"],
            ),
        ],
    ),
    # ------------------ IMPLEMENTATION ------------------
    BenchmarkQuery(
        query_id="q-jv-006",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.IMPLEMENTATION,
        difficulty=DifficultyLevel.HARD,
        query_text="Which classes provide concrete implementations for PaymentService?",
        query_variants=["Implementations of PaymentService interface"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_impl_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="The concrete implementation class.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The interface being implemented.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["PaymentServiceImpl"],
                relationship=GraphRelationship.IMPLEMENTS,
                target_symbol_id=SID["PaymentService"],
            )
        ],
    ),
    BenchmarkQuery(
        query_id="q-jv-010",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.IMPLEMENTATION,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Find implementation for Data access interfaces.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_repository_iface"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Data access interface.",
            ),
        ],
    ),
    # ------------------ INHERITANCE ------------------
    BenchmarkQuery(
        query_id="q-jv-007",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.INHERITANCE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What classes inherit from BaseController?",
        query_variants=["Subclasses of BaseController", "Extends BaseController"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Extends BaseController.",
            ),
            RelevanceJudgment(
                chunk_id=CID["base_controller_class"],
                grade=RelevanceGrade.MARGINAL,
                rationale="The base class definition.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.EXTENDS,
                target_symbol_id=SID["BaseController"],
            )
        ],
    ),
    BenchmarkQuery(
        query_id="q-jv-011",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.INHERITANCE,
        difficulty=DifficultyLevel.EASY,
        query_text="Find children of BaseController class.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Extends BaseController.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["CheckoutController"],
                relationship=GraphRelationship.EXTENDS,
                target_symbol_id=SID["BaseController"],
            )
        ],
    ),
    # ------------------ IMPACT ------------------
    BenchmarkQuery(
        query_id="q-jv-008",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.IMPACT,
        difficulty=DifficultyLevel.HARD,
        query_text="If PaymentRepository.savePayment was changed, which controllers would ultimately be impacted?",
        query_variants=["Transitive impact of savePayment on controllers"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["initiate_checkout_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Controller method transitively calling savePayment.",
            ),
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Intermediate service method.",
            ),
            RelevanceJudgment(
                chunk_id=CID["save_payment_method"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The changed method.",
            ),
        ],
        multi_hop_paths=[
            MultiHopPath(
                path_id="path-jv-001",
                description="CheckoutController -> PaymentService -> PaymentRepository",
                steps=[
                    MultiHopPathStep(
                        symbol_id=SID["initiateCheckout"],
                        relationship=GraphRelationship.CALLS,
                        next_symbol_id=SID["processPayment"],
                    ),
                    MultiHopPathStep(
                        symbol_id=SID["processPayment"],
                        relationship=GraphRelationship.CALLS,
                        next_symbol_id=SID["savePayment"],
                    ),
                ],
            )
        ],
    ),
    BenchmarkQuery(
        query_id="q-jv-012",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.IMPACT,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What would be affected if OrderService gets a breaking change?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Uses OrderService.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-jv-001",
                claim="Checkout controller depends on order service to complete process.",
                supporting_chunk_ids=[CID["checkout_controller_class"]],
            )
        ],
    ),
    # ------------------ SYMBOL DEFINITION ------------------
    BenchmarkQuery(
        query_id="q-jv-013",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.SYMBOL_DEFINITION,
        difficulty=DifficultyLevel.EASY,
        query_text="Where is PaymentServiceImpl?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_impl_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Definition.",
            ),
        ],
        hard_negative_chunk_ids=[CID["payment_service_class"]],
    ),
    # ------------------ SYMBOL USAGE ------------------
    BenchmarkQuery(
        query_id="q-jv-014",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.SYMBOL_USAGE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Who calls processPayment?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["initiate_checkout_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Calls processPayment.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["initiateCheckout"],
                relationship=GraphRelationship.CALLS,
                target_symbol_id=SID["processPayment"],
            )
        ],
    ),
    # ------------------ EXPLANATION ------------------
    BenchmarkQuery(
        query_id="q-jv-015",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.EXPLANATION,
        difficulty=DifficultyLevel.HARD,
        query_text="Explain how initiateCheckout functions and what down-stream services it hits.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["initiate_checkout_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Main method logic.",
            ),
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Service method logic.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-jv-015",
                claim="initiateCheckout calls processPayment which eventually goes to savePayment.",
                supporting_chunk_ids=[
                    CID["initiate_checkout_method"],
                    CID["process_payment_method"],
                ],
            )
        ],
    ),
    # ------------------ CALL RELATIONSHIP ------------------
    BenchmarkQuery(
        query_id="q-jv-016",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.CALL_RELATIONSHIP,
        difficulty=DifficultyLevel.HARD,
        query_text="What does processPayment call internally?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Source of calls.",
            ),
            RelevanceJudgment(
                chunk_id=CID["save_payment_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Called target.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["processPayment"],
                relationship=GraphRelationship.CALLS,
                target_symbol_id=SID["savePayment"],
            )
        ],
    ),
    # ------------------ ARCHITECTURE ------------------
    BenchmarkQuery(
        query_id="q-jv-017",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.ARCHITECTURE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What is the architecture for Spring Java payment saving?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_repository_iface"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="JPA/DB repository interface.",
            ),
            RelevanceJudgment(
                chunk_id=CID["save_payment_method"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Persistence method.",
            ),
        ],
    ),
    # ------------------ FILE_PATH ------------------
    BenchmarkQuery(
        query_id="q-jv-018",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.FILE_PATH,
        difficulty=DifficultyLevel.EASY,
        query_text="Show me the Java PaymentServiceImpl source.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_impl_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Source file context match.",
            ),
        ],
    ),
    # ------------------ IDENTIFIER_HEAVY ------------------
    BenchmarkQuery(
        query_id="q-jv-019",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.IDENTIFIER_HEAVY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Look at PaymentService, PaymentServiceImpl, OrderService and BaseController.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_impl_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target.",
            ),
            RelevanceJudgment(
                chunk_id=CID["order_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target.",
            ),
            RelevanceJudgment(
                chunk_id=CID["base_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target.",
            ),
        ],
    ),
    # ------------------ AMBIGUOUS ------------------
    BenchmarkQuery(
        query_id="q-jv-020",
        repository_id=JAVA_REPO_ID,
        language="java",
        category=QueryCategory.AMBIGUOUS,
        difficulty=DifficultyLevel.HARD,
        query_text="Process it.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.MARGINAL,
                rationale="The text likely maps to processPayment.",
            ),
        ],
        hard_negative_chunk_ids=[CID["checkout_controller_class"], CID["order_service_class"]],
    ),
]
