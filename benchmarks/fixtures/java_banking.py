"""Phase 9A — Synthetic Java benchmark repository fixture."""

from benchmarks.schema import (
    BenchmarkRepository,
    CodeChunkFixture,
    GraphEdgeFixture,
    GraphRelationship,
    SymbolFixture,
)

JAVA_REPO_ID = "repo-java-banking-001"

SID = {
    "PaymentService": "sym-jv-001",
    "processPayment": "sym-jv-002",
    "PaymentRepository": "sym-jv-003",
    "savePayment": "sym-jv-004",
    "CheckoutController": "sym-jv-005",
    "initiateCheckout": "sym-jv-006",
    "OrderService": "sym-jv-014",
    "BaseController": "sym-jv-016",
    "PaymentServiceImpl": "sym-jv-017",
}

CID = {
    "payment_service_class": "chk-jv-002",
    "process_payment_method": "chk-jv-003",
    "payment_repository_iface": "chk-jv-004",
    "save_payment_method": "chk-jv-005",
    "checkout_controller_class": "chk-jv-006",
    "initiate_checkout_method": "chk-jv-007",
    "order_service_class": "chk-jv-014",
    "base_controller_class": "chk-jv-016",
    "payment_service_impl_class": "chk-jv-017",
}

_SYMBOLS = [
    SymbolFixture(
        symbol_id=v,
        name=k,
        qualified_name=f"com.bank.{k}",
        kind="class",
        file_path=f"src/{k}.java",
        start_line=1,
        end_line=10,
        language="java",
    )
    for k, v in SID.items()
]
_CHUNKS = [
    CodeChunkFixture(
        chunk_id=v,
        repository_id=JAVA_REPO_ID,
        file_path=f"src/{k}.java",
        language="java",
        chunk_type="class",
        start_line=1,
        end_line=10,
        content="code",
    )
    for k, v in CID.items()
]

_GRAPH_EDGES = [
    GraphEdgeFixture(
        source_symbol_id=SID["CheckoutController"],
        relationship=GraphRelationship.USES,
        target_symbol_id=SID["PaymentService"],
    ),
    GraphEdgeFixture(
        source_symbol_id=SID["CheckoutController"],
        relationship=GraphRelationship.USES,
        target_symbol_id=SID["OrderService"],
    ),
    GraphEdgeFixture(
        source_symbol_id=SID["PaymentServiceImpl"],
        relationship=GraphRelationship.IMPLEMENTS,
        target_symbol_id=SID["PaymentService"],
    ),
    GraphEdgeFixture(
        source_symbol_id=SID["CheckoutController"],
        relationship=GraphRelationship.EXTENDS,
        target_symbol_id=SID["BaseController"],
    ),
]


def build_java_repository() -> BenchmarkRepository:
    return BenchmarkRepository(
        repository_id=JAVA_REPO_ID,
        name="java-banking-payment",
        language="java",
        description="Java Spring Boot banking API.",
        file_count=14,
        approximate_loc=640,
        symbol_count=len(_SYMBOLS),
        chunk_count=len(_CHUNKS),
        symbols=_SYMBOLS,
        chunks=_CHUNKS,
        graph_edges=_GRAPH_EDGES,
    )
