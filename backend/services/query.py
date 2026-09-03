# backend/services/query.py
"""Application service coordinating Phase 5 Retrieval and Phase 6 Grounded Answering."""

from llm.answer_config import AnswerGenerationConfig
from llm.answer_generator import AnswerGenerator
from llm.budget_config import ContextBudgetConfig
from llm.context_packer import ContextPacker
from llm.context_pruner import ContextPruner
from llm.context_ranker import ContextRanker
from llm.grounding_engine import GroundingEngine
from llm.query_planner import QueryPlanner
from retrieval.candidate_fusion import CandidateFusionEngine
from retrieval.lexical_index import BM25LexicalIndex
from retrieval.lexical_retriever import LexicalRetriever
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.query_processor import QueryPreprocessor
from retrieval.reranker import DeterministicReranker
from retrieval.vector_index import VectorIndex
from retrieval.vector_retriever import VectorRetriever


class QueryApplicationService:
    """Coordinates the retrieval and answering pipelines across domain components."""

    def __init__(self) -> None:
        # Initialize Phase 5 Retrieval components (in-memory for now)
        self.lexical_index = BM25LexicalIndex()
        self.vector_index = VectorIndex()

        self.preprocessor = QueryPreprocessor()

        self.lexical_retriever = LexicalRetriever(self.lexical_index)

        self.embedding_provider = DeterministicTestEmbeddingProvider()
        self.vector_retriever = VectorRetriever(self.vector_index, self.embedding_provider)

        # We omit GraphRetriever for now unless we have a persistent graph store injected
        self.fusion_engine = CandidateFusionEngine()
        self.reranker = DeterministicReranker()

        # Initialize Phase 6 components
        self.planner = QueryPlanner(self.preprocessor)
        self.ranker = ContextRanker()
        self.pruner = ContextPruner()
        self.packer = ContextPacker()
        self.generator = AnswerGenerator()
        self.grounding = GroundingEngine()

    def process_query(
        self, query: str, repository_id: str, top_k: int, generate_answer: bool = True
    ) -> tuple[list, dict | None]:
        """Run the full retrieval (and optional generation) pipeline."""
        # 1. Plan
        plan = self.planner.plan(query)

        # 2. Retrieve
        lexical_res = self.lexical_retriever.retrieve(
            query=plan.processed_query, repository_id=repository_id, top_k=top_k
        )
        vector_res = self.vector_retriever.retrieve(
            query=plan.processed_query, repository_id=repository_id, top_k=top_k
        )

        # 3. Fuse & Rerank
        fused = self.fusion_engine.fuse(
            lexical_results=lexical_res, vector_results=vector_res, top_k=top_k
        )
        reranked = self.reranker.rerank(query=plan.processed_query, results=fused, top_k=top_k)

        # Collect results for UI
        ui_results = []
        for r in reranked.results:
            ui_results.append(
                {
                    "chunk_id": r.chunk_id,
                    "file_path": r.file_path,
                    "language": r.language.value
                    if hasattr(r.language, "value")
                    else str(r.language),
                    "score": r.rerank_score or r.score,
                    "rank": r.rank,
                    "symbol_name": r.symbol_name,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "content": r.metadata.get("content") if getattr(r, "metadata", None) else None,
                }
            )

        if not generate_answer:
            return ui_results, None

        # 4. Context Assembly
        ranked_context = self.ranker.rank(query_plan=plan, candidates=reranked.results)
        pruned_context = self.pruner.prune(query_plan=plan, candidates=ranked_context)
        packed_context = self.packer.pack(
            query_plan=plan, pruning_result=pruned_context, config=ContextBudgetConfig()
        )

        # 5. Generate & Ground
        gen_answer = self.generator.generate(
            query_plan=plan,
            packed_context=packed_context,
            config=AnswerGenerationConfig(provider_name="test", model_name="test"),
        )
        grounding_result = self.grounding.verify(answer=gen_answer, context=packed_context)

        ui_answer = {
            "answer_text": gen_answer.answer_text,
            "intent": gen_answer.intent.value,
            "overall_status": grounding_result.overall_status.value,
            "supported_claims": grounding_result.metrics.supported_claims,
            "total_claims": grounding_result.metrics.total_claims,
            "generation_latency_ms": gen_answer.generation_latency_ms,
            "metadata": grounding_result.metadata,
        }

        return ui_results, ui_answer


# Global singleton for router usage
query_service = QueryApplicationService()
