"""Phase 9A — Python Benchmark Queries."""

from benchmarks.fixtures.python_ecommerce import CID, PYTHON_REPO_ID, SID
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

PYTHON_QUERIES = [
    # ------------------ SYMBOL DEFINITION ------------------
    BenchmarkQuery(
        query_id="q-py-001",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.SYMBOL_DEFINITION,
        difficulty=DifficultyLevel.EASY,
        query_text="Where is PaymentService defined?",
        query_variants=["Find the PaymentService class.", "PaymentService definition"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Exact definition chunk.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_module_file"],
                grade=RelevanceGrade.MARGINAL,
                rationale="File context.",
            ),
        ],
        relevant_symbol_ids=[SID["PaymentService"]],
        hard_negative_chunk_ids=[CID["payment_controller_class"], CID["payment_logger_class"]],
    ),
    BenchmarkQuery(
        query_id="q-py-005",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.SYMBOL_DEFINITION,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Find the notification service class and its logger.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["notification_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="NotificationService definition.",
            ),
        ],
        relevant_symbol_ids=[SID["NotificationService"]],
        hard_negative_chunk_ids=[],
    ),
    # ------------------ SYMBOL USAGE ------------------
    BenchmarkQuery(
        query_id="q-py-002",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.SYMBOL_USAGE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Where is PaymentRepository used to actually save a payment?",
        query_variants=["Uses of PaymentRepository.save_payment", "Who calls save_payment?"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_process"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Calls save_payment.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Imports and injects PaymentRepository.",
            ),
            RelevanceJudgment(
                chunk_id=CID["save_payment"],
                grade=RelevanceGrade.MARGINAL,
                rationale="The definition of the called method.",
            ),
        ],
        relevant_symbol_ids=[SID["process_payment"]],
    ),
    BenchmarkQuery(
        query_id="q-py-006",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.SYMBOL_USAGE,
        difficulty=DifficultyLevel.EASY,
        query_text="Which code references the AuthService?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Injects AuthService in constructor.",
            ),
        ],
        relevant_symbol_ids=[SID["CheckoutService"]],
        hard_negative_chunk_ids=[CID["auth_service_class"]],
    ),
    # ------------------ EXPLANATION ------------------
    BenchmarkQuery(
        query_id="q-py-003",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.EXPLANATION,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="How does the checkout process work and how does it relate to payment?",
        query_variants=["Explain the checkout flow."],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_service_checkout"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Core logic of checkout flow.",
            ),
            RelevanceJudgment(
                chunk_id=CID["checkout_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Constructor defining checkout dependencies.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_process"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The payment logic it delegates to.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-py-001",
                claim="CheckoutService authenticates the user before processing payment.",
                supporting_chunk_ids=[CID["checkout_service_checkout"]],
            ),
            ExpectedFact(
                fact_id="fact-py-002",
                claim="CheckoutService delegates to PaymentService to process the total cart amount.",
                supporting_chunk_ids=[CID["checkout_service_checkout"]],
            ),
        ],
    ),
    BenchmarkQuery(
        query_id="q-py-007",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.EXPLANATION,
        difficulty=DifficultyLevel.HARD,
        query_text="Explain how the authentication token is acquired and validated.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["authenticate_user"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Main auth pipeline.",
            ),
            RelevanceJudgment(
                chunk_id=CID["validate_token"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Validates token logic.",
            ),
            RelevanceJudgment(
                chunk_id=CID["get_user_by_id"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Fetches the user during validation context.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-py-003",
                claim="Token is explicitly validated via validate_token inside AuthService.",
                supporting_chunk_ids=[CID["validate_token"], CID["authenticate_user"]],
            ),
        ],
    ),
    # ------------------ CALL RELATIONSHIP ------------------
    BenchmarkQuery(
        query_id="q-py-004",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.CALL_RELATIONSHIP,
        difficulty=DifficultyLevel.HARD,
        query_text="Find all the callers of validate_token.",
        query_variants=["Who explicitly calls AuthService.validate_token?"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["authenticate_user"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Calls validate_token directly.",
            ),
            RelevanceJudgment(
                chunk_id=CID["validate_token"],
                grade=RelevanceGrade.MARGINAL,
                rationale="The target definition.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["authenticate_user"],
                relationship=GraphRelationship.CALLS,
                target_symbol_id=SID["validate_token"],
                description="authenticate_user calls validate_token to verify the JWT",
            )
        ],
    ),
    BenchmarkQuery(
        query_id="q-py-008",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.CALL_RELATIONSHIP,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What does process_payment call to persist data?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_process"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Contains the call.",
            ),
            RelevanceJudgment(
                chunk_id=CID["save_payment"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The persisted method called.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["process_payment"],
                relationship=GraphRelationship.CALLS,
                target_symbol_id=SID["save_payment"],
            )
        ],
    ),
    # ------------------ DEPENDENCY ------------------
    BenchmarkQuery(
        query_id="q-py-009",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.DEPENDENCY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What are the downstream dependencies of CheckoutService?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Lists PaymentService and AuthService.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Dependency definition.",
            ),
            RelevanceJudgment(
                chunk_id=CID["auth_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Dependency definition.",
            ),
        ],
    ),
    # ------------------ IMPLEMENTATION ------------------
    BenchmarkQuery(
        query_id="q-py-010",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.IMPLEMENTATION,
        difficulty=DifficultyLevel.EASY,
        query_text="What implements PaymentProcessor?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Implements PaymentProcessor directly.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_processor_iface"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The interface.",
            ),
        ],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["PaymentService"],
                relationship=GraphRelationship.IMPLEMENTS,
                target_symbol_id=SID["PaymentProcessor"],
            )
        ],
    ),
    # ------------------ INHERITANCE ------------------
    BenchmarkQuery(
        query_id="q-py-011",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.INHERITANCE,
        difficulty=DifficultyLevel.EASY,
        query_text="List all controllers inheriting from BaseController.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_controller_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Likely inherits BaseController.",
            ),
            RelevanceJudgment(
                chunk_id=CID["base_controller_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Base class.",
            ),
        ],
    ),
    # ------------------ IMPACT ------------------
    BenchmarkQuery(
        query_id="q-py-012",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.IMPACT,
        difficulty=DifficultyLevel.HARD,
        query_text="If get_user_by_id logic changes, which checkout functions might be impacted?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["authenticate_user"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Transitive caller 1.",
            ),
            RelevanceJudgment(
                chunk_id=CID["checkout_service_checkout"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Transitive caller 2.",
            ),
            RelevanceJudgment(
                chunk_id=CID["get_user_by_id"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Changed function.",
            ),
        ],
        multi_hop_paths=[
            MultiHopPath(
                path_id="path-py-001",
                description="checkout -> authenticate_user -> get_user_by_id",
                steps=[
                    MultiHopPathStep(
                        symbol_id=SID["checkout"],
                        relationship=GraphRelationship.CALLS,
                        next_symbol_id=SID["authenticate_user"],
                    ),
                    MultiHopPathStep(
                        symbol_id=SID["authenticate_user"],
                        relationship=GraphRelationship.CALLS,
                        next_symbol_id=SID["get_user_by_id"],
                    ),
                ],
            )
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-py-009",
                claim="Checkout relies on auth which calls get_user_by_id.",
                supporting_chunk_ids=[
                    CID["checkout_service_checkout"],
                    CID["authenticate_user"],
                    CID["get_user_by_id"],
                ],
            )
        ],
    ),
    # ------------------ ARCHITECTURE ------------------
    BenchmarkQuery(
        query_id="q-py-013",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.ARCHITECTURE,
        difficulty=DifficultyLevel.HARD,
        query_text="Explain the order cancellation flow architecture.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["order_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Top level order service defines how it works.",
            ),
            RelevanceJudgment(
                chunk_id=CID["cancel_order"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Cancellation logic execution.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-py-008",
                claim="Cancel order is handled primarily within OrderService.",
                supporting_chunk_ids=[CID["cancel_order"]],
            )
        ],
    ),
    # ------------------ FILE_PATH ------------------
    BenchmarkQuery(
        query_id="q-py-014",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.FILE_PATH,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What code resides in utils/payment_logger.py and utils/payment_validator.py?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_logger_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Resides in logger utils.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_validator_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Resides in validator utils.",
            ),
        ],
    ),
    # ------------------ IDENTIFIER_HEAVY ------------------
    BenchmarkQuery(
        query_id="q-py-015",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.IDENTIFIER_HEAVY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Look at PaymentService, PaymentRepository, PaymentValidator and StripePaymentService.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target symbol.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_repository_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target symbol.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_validator_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target symbol.",
            ),
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target symbol.",
            ),
        ],
        hard_negative_chunk_ids=[CID["payment_logger_class"], CID["payment_controller_class"]],
    ),
    # ------------------ AMBIGUOUS ------------------
    BenchmarkQuery(
        query_id="q-py-016",
        repository_id=PYTHON_REPO_ID,
        language="python",
        category=QueryCategory.AMBIGUOUS,
        difficulty=DifficultyLevel.HARD,
        query_text="How is payment handled?",
        query_variants=["Payments info"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_service_process"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Core payment logic.",
            ),
            RelevanceJudgment(
                chunk_id=CID["checkout_service_checkout"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Starting point of payments payment flow in cart context.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_repository_class"],
                grade=RelevanceGrade.MARGINAL,
                rationale="Data persistence.",
            ),
        ],
        hard_negative_chunk_ids=[
            CID["payment_validator_class"],
            CID["payment_logger_class"],
            CID["payment_controller_class"],
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-py-015",
                claim="Main payment logic goes through PaymentService.",
                supporting_chunk_ids=[CID["payment_service_process"]],
            )
        ],
    ),
]
