import math
import pytest

from retrieval.contracts import EmbeddingProviderContract
from retrieval.embedding_models import EmbeddingInput
from retrieval.providers import LocalSentenceTransformerProvider

def test_local_provider_contract_and_properties():
    provider = LocalSentenceTransformerProvider()
    assert isinstance(provider, EmbeddingProviderContract)
    assert provider.provider_name == "LocalSentenceTransformerProvider"
    assert provider.model_name == "all-MiniLM-L6-v2"
    assert provider.dimension == 384
    assert provider.embedding_version == "local-minilm-semantic-v1"

def test_local_provider_empty_input():
    provider = LocalSentenceTransformerProvider()
    assert provider.embed([]) == []

def test_local_provider_single_input():
    provider = LocalSentenceTransformerProvider()
    inp = EmbeddingInput(
        chunk_id="c1",
        text="def foo(): pass",
        model_name="test",
        embedding_version="v1",
        metadata={"repository_id": "repo1", "commit_sha": "abc"}
    )
    res = provider.embed([inp])
    
    assert len(res) == 1
    out = res[0]
    assert out.chunk_id == "c1"
    assert out.dimension == 384
    assert len(out.vector) == 384
    assert out.repository_id == "repo1"
    assert out.commit_sha == "abc"
    
    # Check L2 normalization within reasonable numeric tolerance
    norm = math.sqrt(sum(v*v for v in out.vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-5)

def test_local_provider_multiple_inputs_preserve_order_and_batch_behavior():
    provider = LocalSentenceTransformerProvider()
    # Batch size is 32, create > 32 elements
    inputs = [
        EmbeddingInput(chunk_id=f"c{i}", text=f"Text sequence {i}", model_name="test", embedding_version="v1")
        for i in range(40)
    ]
    res = provider.embed(inputs)
    assert len(res) == 40
    for i in range(40):
        assert res[i].chunk_id == f"c{i}"
        
def test_local_provider_semantic_differences():
    provider = LocalSentenceTransformerProvider()
    inp1 = EmbeddingInput(chunk_id="1", text="The quick brown fox jumps over the lazy dog.", model_name="x", embedding_version="1")
    inp2 = EmbeddingInput(chunk_id="2", text="A fast dark-colored canine leaps above an inactive hound.", model_name="x", embedding_version="1")
    inp3 = EmbeddingInput(chunk_id="3", text="Database connection configuration settings logic.", model_name="x", embedding_version="1")
    
    res = provider.embed([inp1, inp2, inp3])
    
    def cosine(v1: list[float], v2: list[float]) -> float:
        return sum(x*y for x, y in zip(v1, v2))
        
    sim_1_2 = cosine(res[0].vector, res[1].vector)
    sim_1_3 = cosine(res[0].vector, res[2].vector)
    
    assert sim_1_2 > sim_1_3, "Semantic similarity failed: related sentences should be closer than unrelated ones."
