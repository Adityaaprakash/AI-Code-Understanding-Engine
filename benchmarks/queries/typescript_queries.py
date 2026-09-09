"""Phase 9A — TypeScript Benchmark Queries."""

from benchmarks.fixtures.typescript_gateway import CID, SID, TYPESCRIPT_REPO_ID
from benchmarks.schema import (
    BenchmarkQuery,
    DifficultyLevel,
    ExpectedFact,
    GraphGroundTruth,
    GraphRelationship,
    QueryCategory,
    RelevanceGrade,
    RelevanceJudgment,
)

TYPESCRIPT_QUERIES = [
    # ------------------ ARCHITECTURE ------------------
    BenchmarkQuery(
        query_id="q-ts-009",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.ARCHITECTURE,
        difficulty=DifficultyLevel.HARD,
        query_text="How are HTTP requests to the checkout endpoint authenticated before processing the payment?",
        query_variants=["Architecture of checkout authentication and payment processing."],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["jwt_filter_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Explains architecture of JWT middleware on all requests.",
            ),
            RelevanceJudgment(
                chunk_id=CID["authenticate_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Core logic where auth happens before hitting router.",
            ),
            RelevanceJudgment(
                chunk_id=CID["handle_checkout_fn"],
                grade=RelevanceGrade.RELEVANT,
                rationale="The checkout processing part after authentication.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-ts-001",
                claim="JWTAuthenticationFilter authenticates requests using JWT Bearer tokens.",
                supporting_chunk_ids=[CID["jwt_filter_class"], CID["authenticate_method"]],
            ),
            ExpectedFact(
                fact_id="fact-ts-002",
                claim="Authenticated user context is populated via req.user before hitting CheckoutRouter.",
                supporting_chunk_ids=[CID["authenticate_method"]],
            ),
        ],
    ),
    BenchmarkQuery(
        query_id="q-ts-021",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.ARCHITECTURE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="How is Express routing organized for the checkout gateway?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_router_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Express checkout router.",
            ),
            RelevanceJudgment(
                chunk_id=CID["handle_checkout_fn"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Specific route callback.",
            ),
        ],
    ),
    # ------------------ FILE_PATH ------------------
    BenchmarkQuery(
        query_id="q-ts-010",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.FILE_PATH,
        difficulty=DifficultyLevel.EASY,
        query_text="What does src/middleware/JWTAuthenticationFilter.ts do?",
        query_variants=["Contents of JWTAuthenticationFilter.ts file"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["jwt_filter_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Class definition within the target file.",
            ),
            RelevanceJudgment(
                chunk_id=CID["authenticate_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Method within the target file.",
            ),
        ],
        relevant_file_paths=["src/middleware/JWTAuthenticationFilter.ts"],
    ),
    BenchmarkQuery(
        query_id="q-ts-022",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.FILE_PATH,
        difficulty=DifficultyLevel.EASY,
        query_text="Find src/stripe_payment_service_class.ts",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target Class mapping to that filename.",
            ),
        ],
        relevant_file_paths=["src/stripe_payment_service_class.ts"],
    ),
    # ------------------ IDENTIFIER_HEAVY ------------------
    BenchmarkQuery(
        query_id="q-ts-011",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.IDENTIFIER_HEAVY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="Find StripePaymentService and IPaymentService implementation details.",
        query_variants=["StripePaymentService implements IPaymentService"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Identifies StripePaymentService.",
            ),
            RelevanceJudgment(
                chunk_id=CID["ipayment_service_iface"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Identifies IPaymentService.",
            ),
        ],
        relevant_symbol_ids=[SID["StripePaymentService"], SID["IPaymentService"]],
        graph_ground_truth=[
            GraphGroundTruth(
                source_symbol_id=SID["StripePaymentService"],
                relationship=GraphRelationship.IMPLEMENTS,
                target_symbol_id=SID["IPaymentService"],
            )
        ],
    ),
    # ------------------ AMBIGUOUS ------------------
    BenchmarkQuery(
        query_id="q-ts-012",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.AMBIGUOUS,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="How to handle payments?",
        query_variants=["Payment processing approach", "Dealing with payments"],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Core logic describing standard payment processing.",
            ),
            RelevanceJudgment(
                chunk_id=CID["ipayment_service_iface"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Defines the contract for payments.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Main payment service.",
            ),
            RelevanceJudgment(
                chunk_id=CID["checkout_router_class"],
                grade=RelevanceGrade.MARGINAL,
                rationale="Controller for payments (optional consideration).",
            ),
        ],
        hard_negative_chunk_ids=[CID["payment_logger_class"], CID["payment_validator_class"]],
    ),
    # ------------------ SYMBOL DEFINITION ------------------
    BenchmarkQuery(
        query_id="q-ts-023",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.SYMBOL_DEFINITION,
        difficulty=DifficultyLevel.EASY,
        query_text="Find the Stripe Payment Service block.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Definition block.",
            ),
        ],
        relevant_symbol_ids=[SID["StripePaymentService"]],
    ),
    # ------------------ SYMBOL USAGE ------------------
    BenchmarkQuery(
        query_id="q-ts-024",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.SYMBOL_USAGE,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="When is handle_checkout activated?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_router_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Router applies handle_checkout.",
            ),
            RelevanceJudgment(
                chunk_id=CID["handle_checkout_fn"],
                grade=RelevanceGrade.MARGINAL,
                rationale="Definition context.",
            ),
        ],
    ),
    # ------------------ EXPLANATION ------------------
    BenchmarkQuery(
        query_id="q-ts-025",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.EXPLANATION,
        difficulty=DifficultyLevel.HARD,
        query_text="Explain how the Stripe wrapper abstracts IPaymentService.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Implements IPaymentService via Stripe wrapper.",
            ),
            RelevanceJudgment(
                chunk_id=CID["ipayment_service_iface"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Contract being abstracted.",
            ),
        ],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-ts-020",
                claim="Stripe wrapper maps standard abstract IPaymentService methods.",
                supporting_chunk_ids=[CID["stripe_payment_service_class"]],
            )
        ],
    ),
    # ------------------ CALL RELATIONSHIP ------------------
    BenchmarkQuery(
        query_id="q-ts-026",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.CALL_RELATIONSHIP,
        difficulty=DifficultyLevel.HARD,
        query_text="What is called during process_payment in the gateway?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["process_payment_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Call origin context.",
            ),
        ],
    ),
    # ------------------ DEPENDENCY ------------------
    BenchmarkQuery(
        query_id="q-ts-027",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.DEPENDENCY,
        difficulty=DifficultyLevel.MEDIUM,
        query_text="What dependencies does the checkout router rely on?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["checkout_router_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Instantiates and hooks route params.",
            ),
            RelevanceJudgment(
                chunk_id=CID["jwt_filter_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Used as middleware dependency.",
            ),
        ],
    ),
    # ------------------ IMPLEMENTATION ------------------
    BenchmarkQuery(
        query_id="q-ts-028",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.IMPLEMENTATION,
        difficulty=DifficultyLevel.EASY,
        query_text="How is PaymentLogger written?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["payment_logger_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Shows logger writing mechanism.",
            ),
        ],
    ),
    # ------------------ INHERITANCE ------------------
    BenchmarkQuery(
        query_id="q-ts-029",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.INHERITANCE,
        difficulty=DifficultyLevel.EASY,
        query_text="What inherits from payment base class?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Child class.",
            ),
            RelevanceJudgment(
                chunk_id=CID["payment_service_class"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Another child/base depending on modeling.",
            ),
        ],
    ),
    # ------------------ IMPACT ------------------
    BenchmarkQuery(
        query_id="q-ts-030",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.IMPACT,
        difficulty=DifficultyLevel.HARD,
        query_text="If IPaymentService changes, what functions fail in checkout?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["handle_checkout_fn"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Handles checkout calls payment service.",
            ),
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Direct implementation.",
            ),
            RelevanceJudgment(
                chunk_id=CID["ipayment_service_iface"],
                grade=RelevanceGrade.RELEVANT,
                rationale="Changed contract.",
            ),
        ],
        hard_negative_chunk_ids=[CID["payment_validator_class"]],
        expected_facts=[
            ExpectedFact(
                fact_id="fact-ts-030",
                claim="Modifying interface directly impacts all classes resolving via DI.",
                supporting_chunk_ids=[
                    CID["handle_checkout_fn"],
                    CID["stripe_payment_service_class"],
                ],
            )
        ],
    ),
    # ------------------ DEPENDENCY ------------------
    BenchmarkQuery(
        query_id="q-ts-031",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.DEPENDENCY,
        difficulty=DifficultyLevel.EASY,
        query_text="Find the file containing the StripePaymentService dependency.",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["stripe_payment_service_class"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target dependency.",
            ),
        ],
    ),
    # ------------------ SYMBOL USAGE ------------------
    BenchmarkQuery(
        query_id="q-ts-032",
        repository_id=TYPESCRIPT_REPO_ID,
        language="typescript",
        category=QueryCategory.SYMBOL_USAGE,
        difficulty=DifficultyLevel.EASY,
        query_text="Where is authenticate_method used?",
        query_variants=[],
        relevance_judgments=[
            RelevanceJudgment(
                chunk_id=CID["authenticate_method"],
                grade=RelevanceGrade.ESSENTIAL,
                rationale="Target usage footprint.",
            ),
        ],
    ),
]
