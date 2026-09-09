"""Phase 9A - Benchmark Dataset Validator."""

from benchmarks.schema import BenchmarkDataset


class BenchmarkValidationError(Exception):
    pass


class BenchmarkValidator:
    @staticmethod
    def validate(dataset: BenchmarkDataset) -> None:
        repo_ids = set()
        for repo in dataset.repositories:
            if repo.repository_id in repo_ids:
                raise BenchmarkValidationError(f"Duplicate repository ID: {repo.repository_id}")
            repo_ids.add(repo.repository_id)

            sym_ids = set()
            for sym in repo.symbols:
                if sym.symbol_id in sym_ids:
                    raise BenchmarkValidationError(f"Duplicate symbol ID {sym.symbol_id}")
                sym_ids.add(sym.symbol_id)

            chunk_ids = set()
            for chunk in repo.chunks:
                if chunk.chunk_id in chunk_ids:
                    raise BenchmarkValidationError(f"Duplicate chunk ID {chunk.chunk_id}")
                chunk_ids.add(chunk.chunk_id)

        query_ids = set()
        for query in dataset.queries:
            if query.query_id in query_ids:
                raise BenchmarkValidationError(f"Duplicate query ID: {query.query_id}")
            query_ids.add(query.query_id)

            found_repo = dataset.get_repository(query.repository_id)
            if not found_repo:
                raise BenchmarkValidationError(f"Unknown repo {query.repository_id}")

            seen_chunks = set()
            for j in query.relevance_judgments:
                if j.chunk_id in seen_chunks:
                    raise BenchmarkValidationError(f"Duplicate judgment {j.chunk_id}")
                seen_chunks.add(j.chunk_id)
                if not dataset.get_chunk(query.repository_id, j.chunk_id):
                    raise BenchmarkValidationError(f"Unknown chunk {j.chunk_id}")

            for sid in query.relevant_symbol_ids:
                if not dataset.get_symbol(query.repository_id, sid):
                    raise BenchmarkValidationError(f"Unknown symbol {sid}")

            for ggt in query.graph_ground_truth:
                if not dataset.get_symbol(query.repository_id, ggt.source_symbol_id):
                    raise BenchmarkValidationError(f"Unknown graph source: {ggt.source_symbol_id}")
                if not dataset.get_symbol(query.repository_id, ggt.target_symbol_id):
                    raise BenchmarkValidationError(f"Unknown graph target: {ggt.target_symbol_id}")

            for fact in query.expected_facts:
                for chunk_id in fact.supporting_chunk_ids:
                    if not dataset.get_chunk(query.repository_id, chunk_id):
                        raise BenchmarkValidationError(f"Fact missing chunk {chunk_id}")

            for chunk_id in query.hard_negative_chunk_ids:
                if not dataset.get_chunk(query.repository_id, chunk_id):
                    raise BenchmarkValidationError(f"HN missing chunk {chunk_id}")
