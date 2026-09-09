"""Phase 9A - Benchmark Configuration Models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RetrievalSystemConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    system_id: str
    name: str
    description: str
    retrieval_type: Literal["lexical", "vector", "graph", "hybrid"] = "hybrid"
    use_lexical: bool = False
    use_vector: bool = False
    use_graph: bool = False
    use_fusion: bool = False
    use_reranking: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    experiment_id: str
    description: str
    systems: list[RetrievalSystemConfig] = Field(default_factory=list)
    dataset_version: str = "9A.1"


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    default_k_values: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])
    metrics: list[str] = Field(
        default_factory=lambda: ["Precision@K", "Recall@K", "HitRate@K", "NDCG@K", "MRR"]
    )
    experiments: list[ExperimentConfig] = Field(default_factory=list)

    @classmethod
    def get_phase9_standard_config(cls) -> "BenchmarkConfig":
        return cls(
            experiments=[
                ExperimentConfig(
                    experiment_id="9B-vector-baseline",
                    description="Baseline vector-only retrieval",
                    systems=[
                        RetrievalSystemConfig(
                            system_id="vector-only",
                            name="Vector Only",
                            description="Baseline dense vector retrieval",
                            retrieval_type="vector",
                            use_vector=True,
                        )
                    ],
                ),
                ExperimentConfig(
                    experiment_id="9C-system-comparison",
                    description="Compare components of the retrieval pipeline",
                    systems=[
                        RetrievalSystemConfig(
                            system_id="lexical-only",
                            name="BM25 Only",
                            description="Lexical only baseline",
                            retrieval_type="lexical",
                            use_lexical=True,
                        ),
                        RetrievalSystemConfig(
                            system_id="hybrid-basic",
                            name="BM25 + Vector",
                            description="Standard hybrid",
                            retrieval_type="hybrid",
                            use_lexical=True,
                            use_vector=True,
                            use_fusion=True,
                        ),
                        RetrievalSystemConfig(
                            system_id="hybrid-graph",
                            name="BM25 + Vector + Graph",
                            description="Hybrid with structural graph retrieval",
                            retrieval_type="hybrid",
                            use_lexical=True,
                            use_vector=True,
                            use_graph=True,
                            use_fusion=True,
                        ),
                        RetrievalSystemConfig(
                            system_id="hybrid-graph-rerank",
                            name="Full Hybrid + Reranking",
                            description="Complete pipeline with reranking",
                            retrieval_type="hybrid",
                            use_lexical=True,
                            use_vector=True,
                            use_graph=True,
                            use_fusion=True,
                            use_reranking=True,
                        ),
                    ],
                ),
            ]
        )
