"""Synthetic benchmark dataset builder for Phase 5G Retrieval Evaluation."""

from code_analyzer.parsers.models import Language
from evaluation.models import EvaluationQuery, QueryCategory
from retrieval.enums import ChunkType
from retrieval.retrieval_models import RetrievalResult


def get_synthetic_benchmark_dataset(
    repository_id: str = "benchmark-repo",
) -> tuple[dict[str, RetrievalResult], list[EvaluationQuery]]:
    """Construct a deterministic synthetic codebase index and gold evaluation queries for benchmarking.

    Args:
        repository_id: Identifier for the synthetic benchmark repository.

    Returns:
        Tuple of (chunk_id -> RetrievalResult mapping, list of EvaluationQuery objects).
    """
    chunks: dict[str, RetrievalResult] = {
        "chunk-db-config-class": RetrievalResult(
            chunk_id="chunk-db-config-class",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="config/db_config.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="DatabaseConfig",
            qualified_name="config.db_config.DatabaseConfig",
            start_line=1,
            end_line=25,
            metadata={
                "code_content": "class DatabaseConfig:\n    def get_db_connection(self):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-get-db-conn": RetrievalResult(
            chunk_id="chunk-get-db-conn",
            score=0.9,
            rank=2,
            repository_id=repository_id,
            file_path="config/db_config.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            symbol_name="get_db_connection",
            qualified_name="config.db_config.DatabaseConfig.get_db_connection",
            start_line=10,
            end_line=20,
            metadata={
                "code_content": "def get_db_connection(): return connect(dsn='postgresql://localhost:5432')",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-auth-service-class": RetrievalResult(
            chunk_id="chunk-auth-service-class",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="services/auth_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="AuthService",
            qualified_name="services.auth_service.AuthService",
            start_line=1,
            end_line=50,
            metadata={
                "code_content": "class AuthService:\n    def validate_jwt_token(self, token):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-auth-validate-jwt": RetrievalResult(
            chunk_id="chunk-auth-validate-jwt",
            score=0.95,
            rank=2,
            repository_id=repository_id,
            file_path="services/auth_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            symbol_name="validate_jwt_token",
            qualified_name="services.auth_service.AuthService.validate_jwt_token",
            start_line=15,
            end_line=40,
            metadata={
                "code_content": "def validate_jwt_token(token: str) -> bool:\n    # JWT signature and expiration verification\n    return verify_jwt(token)",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-payment-processor-interface": RetrievalResult(
            chunk_id="chunk-payment-processor-interface",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="interfaces/payment_processor.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="PaymentProcessor",
            qualified_name="interfaces.payment_processor.PaymentProcessor",
            start_line=1,
            end_line=30,
            metadata={
                "code_content": "class PaymentProcessor(ABC):\n    @abstractmethod\n    def process_payment(self, amount):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-stripe-processor-class": RetrievalResult(
            chunk_id="chunk-stripe-processor-class",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="services/stripe_processor.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="StripePaymentProcessor",
            qualified_name="services.stripe_processor.StripePaymentProcessor",
            start_line=1,
            end_line=60,
            metadata={
                "code_content": "class StripePaymentProcessor(PaymentProcessor):\n    def verify_stripe_token(self, token):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-stripe-verify-token": RetrievalResult(
            chunk_id="chunk-stripe-verify-token",
            score=0.9,
            rank=2,
            repository_id=repository_id,
            file_path="services/stripe_processor.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            symbol_name="verify_stripe_token",
            qualified_name="services.stripe_processor.StripePaymentProcessor.verify_stripe_token",
            start_line=20,
            end_line=45,
            metadata={
                "code_content": "def verify_stripe_token(token: str):\n    return stripe.Token.retrieve(token)",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-payment-service-class": RetrievalResult(
            chunk_id="chunk-payment-service-class",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="services/payment_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="PaymentService",
            qualified_name="services.payment_service.PaymentService",
            start_line=1,
            end_line=70,
            metadata={
                "code_content": "class PaymentService:\n    def process_payment(self, amount):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-process-payment-fn": RetrievalResult(
            chunk_id="chunk-process-payment-fn",
            score=0.95,
            rank=2,
            repository_id=repository_id,
            file_path="services/payment_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            symbol_name="process_payment",
            qualified_name="services.payment_service.PaymentService.process_payment",
            start_line=25,
            end_line=50,
            metadata={
                "code_content": "def process_payment(amount: float):\n    auth_service.validate_jwt_token(token)\n    return processor.charge(amount)",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-order-service-class": RetrievalResult(
            chunk_id="chunk-order-service-class",
            score=1.0,
            rank=1,
            repository_id=repository_id,
            file_path="services/order_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.CLASS_CONTEXT,
            symbol_name="OrderService",
            qualified_name="services.order_service.OrderService",
            start_line=1,
            end_line=80,
            metadata={
                "code_content": "class OrderService:\n    def cancel_order(self, order_id):\n        pass",
                "commit_sha": "v1.0.0",
            },
        ),
        "chunk-order-service-cancel": RetrievalResult(
            chunk_id="chunk-order-service-cancel",
            score=0.95,
            rank=2,
            repository_id=repository_id,
            file_path="services/order_service.py",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            symbol_name="cancel_order",
            qualified_name="services.order_service.OrderService.cancel_order",
            start_line=30,
            end_line=60,
            metadata={
                "code_content": "def cancel_order(order_id: str):\n    auth_service.validate_jwt_token(token)\n    payment_service.process_payment(-amount)",
                "commit_sha": "v1.0.0",
            },
        ),
    }

    queries: list[EvaluationQuery] = [
        EvaluationQuery(
            query_id="Q1_CONFIG",
            question="Where is database connection configured?",
            repository_id=repository_id,
            category=QueryCategory.CONFIGURATION,
            relevant_chunk_ids=["chunk-db-config-class", "chunk-get-db-conn"],
            graded_relevance={"chunk-get-db-conn": 2, "chunk-db-config-class": 1},
        ),
        EvaluationQuery(
            query_id="Q2_IDENTIFIER",
            question="PaymentProcessor",
            repository_id=repository_id,
            category=QueryCategory.IDENTIFIER,
            relevant_chunk_ids=["chunk-payment-processor-interface"],
            graded_relevance={"chunk-payment-processor-interface": 2},
        ),
        EvaluationQuery(
            query_id="Q3_RELATIONSHIP",
            question="What calls process_payment?",
            repository_id=repository_id,
            category=QueryCategory.RELATIONSHIP,
            relevant_chunk_ids=["chunk-order-service-cancel"],
            graded_relevance={"chunk-order-service-cancel": 2},
        ),
        EvaluationQuery(
            query_id="Q4_DEPENDENCY",
            question="Which components depend on AuthService?",
            repository_id=repository_id,
            category=QueryCategory.DEPENDENCY,
            relevant_chunk_ids=["chunk-payment-service-class", "chunk-order-service-class"],
            graded_relevance={
                "chunk-payment-service-class": 2,
                "chunk-order-service-class": 2,
            },
        ),
        EvaluationQuery(
            query_id="Q5_IMPLEMENTATION",
            question="Which classes implement PaymentProcessor?",
            repository_id=repository_id,
            category=QueryCategory.IMPLEMENTATION,
            relevant_chunk_ids=["chunk-stripe-processor-class"],
            graded_relevance={"chunk-stripe-processor-class": 2},
        ),
        EvaluationQuery(
            query_id="Q6_SEMANTIC",
            question="How does JWT authentication token validation work?",
            repository_id=repository_id,
            category=QueryCategory.SEMANTIC,
            relevant_chunk_ids=["chunk-auth-validate-jwt", "chunk-auth-service-class"],
            graded_relevance={"chunk-auth-validate-jwt": 2, "chunk-auth-service-class": 1},
        ),
        EvaluationQuery(
            query_id="Q7_MIXED",
            question="Which service handles Stripe payment token verification?",
            repository_id=repository_id,
            category=QueryCategory.MIXED,
            relevant_chunk_ids=["chunk-stripe-verify-token", "chunk-stripe-processor-class"],
            graded_relevance={"chunk-stripe-verify-token": 2, "chunk-stripe-processor-class": 1},
        ),
    ]

    return chunks, queries
