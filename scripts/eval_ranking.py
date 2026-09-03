import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retrieval.retrieval_models import RetrievalResult
from llm.context_ranker import ContextRanker
from llm.ranking_config import ContextRankingConfig
from llm.planner_models import QueryPlan
from llm.enums import QueryIntent, QueryScope, AnswerStyle, RelationshipType

from code_analyzer.parsers.models import Language
from retrieval.enums import ChunkType

from retrieval.query_models import ProcessedQuery

def evaluate_ranking_normalization():
    print("--- 6C FUSED SCORE NORMALIZATION EVALUATION ---")
    
    candidates = []
    
    for i in range(1, 150):
        fused = (1.0 / (60 + i)) * 2.0
        c = RetrievalResult(
            chunk_id=f"c_{i}",
            file_path="foo.py",
            repository_id="repo1",
            language=Language.PYTHON,
            chunk_type=ChunkType.FUNCTION,
            score=0.0,
            rank=i,
            fused_score=fused
        )
        candidates.append(c)
        
    ranker = ContextRanker()
    pq = ProcessedQuery(
        original_query="test",
        normalized_query="test",
        tokens=[],
        identifier_tokens=[],
        natural_language_tokens=[],
        qualified_name_candidates=[],
    )
    plan = QueryPlan(
        query="test",
        normalized_query="test",
        processed_query=pq,
        primary_intent=QueryIntent.EXPLANATION,
        target_entities=["foo"],
        scope=QueryScope.FILE,
        answer_style=AnswerStyle.CODE_LOCATION,
    )
    
    # Just normal rank
    res = ranker.rank(plan, candidates)
    
    # See how many are saturated (norm_ret_score == 1.0)
    saturated = 0
    scores = []
    for cand in res.ranked_candidates:
        ret_relevance = cand.score_breakdown.retrieval_relevance
        scores.append((cand.candidate_id, cand.retrieval_score, ret_relevance))
        if ret_relevance >= 0.99999:
            saturated += 1
            
    print(f"Total simulated candidates: {len(candidates)}")
    print(f"Saturated candidates (norm_ret_score >= 0.999): {saturated}")
    print(f"Top 5 norm_ret_scores:")
    for cid, raw, norm in scores[:5]:
        print(f"  {cid}: raw={raw:.5f} -> norm={norm:.5f}")
    
    # What about rank 61 in both?
    f61 = (1.0 / (60 + 61)) * 2.0
    print(f"Candidate at rank 61 in both (raw={f61:.5f}) -> {min(1.0, f61 * 61.0):.5f}")

if __name__ == "__main__":
    evaluate_ranking_normalization()
