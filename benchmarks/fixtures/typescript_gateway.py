"""Phase 9A — Synthetic TypeScript benchmark repository fixture."""

from benchmarks.schema import BenchmarkRepository, CodeChunkFixture, GraphEdgeFixture, SymbolFixture

TYPESCRIPT_REPO_ID = "repo-ts-gateway-001"

SID = {"StripePaymentService": "sym-ts-001", "IPaymentService": "sym-ts-002"}

CID = {
    "jwt_filter_class": "chk-ts-001",
    "authenticate_method": "chk-ts-002",
    "handle_checkout_fn": "chk-ts-003",
    "stripe_payment_service_class": "chk-ts-004",
    "ipayment_service_iface": "chk-ts-005",
    "process_payment_method": "chk-ts-006",
    "payment_service_class": "chk-ts-007",
    "checkout_router_class": "chk-ts-008",
    "payment_logger_class": "chk-ts-009",
    "payment_validator_class": "chk-ts-010",
}

_SYMBOLS = [
    SymbolFixture(
        symbol_id=v,
        name=k,
        qualified_name=f"src.{k}",
        kind="class",
        file_path=f"src/{k}.ts",
        start_line=1,
        end_line=10,
        language="typescript",
    )
    for k, v in SID.items()
]
_CHUNKS = [
    CodeChunkFixture(
        chunk_id=v,
        repository_id=TYPESCRIPT_REPO_ID,
        file_path=f"src/{k}.ts",
        language="typescript",
        chunk_type="class",
        start_line=1,
        end_line=10,
        content="code",
    )
    for k, v in CID.items()
]

_GRAPH_EDGES: list[GraphEdgeFixture] = []


def build_typescript_repository() -> BenchmarkRepository:
    return BenchmarkRepository(
        repository_id=TYPESCRIPT_REPO_ID,
        name="ts-checkout-gateway",
        language="typescript",
        description="TypeScript node API.",
        file_count=10,
        approximate_loc=500,
        symbol_count=len(_SYMBOLS),
        chunk_count=len(_CHUNKS),
        symbols=_SYMBOLS,
        chunks=_CHUNKS,
        graph_edges=_GRAPH_EDGES,
    )
