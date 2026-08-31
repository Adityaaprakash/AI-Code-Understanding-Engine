"""Production-quality deterministic BM25 lexical index implementation."""

import math
from collections import defaultdict
from collections.abc import Iterable

from code_analyzer.parsers.models import Language
from retrieval.contracts import LexicalIndexContract
from retrieval.enums import ChunkType
from retrieval.exceptions import LexicalConfigurationError, LexicalQueryError
from retrieval.lexical_models import LexicalDocument, LexicalSearchResult
from retrieval.lexical_text_builder import LexicalTextBuilder
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.tokenizer import CodeTokenizer, tokenize_query


class RepositoryBM25Index:
    """Isolated BM25 index for a single repository."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 < 0:
            raise LexicalConfigurationError(f"k1 parameter must be >= 0, got {k1}")
        if not (0.0 <= b <= 1.0):
            raise LexicalConfigurationError(f"b parameter must be between 0.0 and 1.0, got {b}")

        self.k1 = k1
        self.b = b

        self.documents: dict[str, LexicalDocument] = {}
        # postings[term][chunk_id] = term_frequency
        self.postings: dict[str, dict[str, int]] = defaultdict(dict)
        self.doc_frequencies: dict[str, int] = defaultdict(int)
        self.total_documents: int = 0
        self.sum_doc_length: int = 0

    def add(self, doc: LexicalDocument) -> None:
        """Add or replace a LexicalDocument in the repository index.

        Enforces deterministic replacement if chunk_id already exists.
        """
        if doc.chunk_id in self.documents:
            self.remove(doc.chunk_id)

        # Count term frequencies for the document
        tf_counts: dict[str, int] = defaultdict(int)
        for token in doc.all_tokens:
            tf_counts[token] += 1

        self.documents[doc.chunk_id] = doc
        self.total_documents += 1
        self.sum_doc_length += doc.doc_len

        for token, tf in tf_counts.items():
            self.postings[token][doc.chunk_id] = tf
            self.doc_frequencies[token] += 1

    def remove(self, chunk_id: str) -> bool:
        """Remove a LexicalDocument by chunk_id."""
        if chunk_id not in self.documents:
            return False

        doc = self.documents.pop(chunk_id)
        self.total_documents -= 1
        self.sum_doc_length -= doc.doc_len

        tf_counts: set[str] = set()
        for token in doc.all_tokens:
            tf_counts.add(token)

        for token in tf_counts:
            if token in self.postings and chunk_id in self.postings[token]:
                del self.postings[token][chunk_id]
                if not self.postings[token]:
                    del self.postings[token]
                self.doc_frequencies[token] -= 1
                if self.doc_frequencies[token] <= 0:
                    del self.doc_frequencies[token]

        return True

    def clear(self) -> None:
        """Clear all documents and postings from the repository index."""
        self.documents.clear()
        self.postings.clear()
        self.doc_frequencies.clear()
        self.total_documents = 0
        self.sum_doc_length = 0

    def search(
        self,
        query_tokens: list[str],
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list[LexicalSearchResult]:
        """Execute BM25 search over the repository index with optional filters."""
        if not query_tokens or self.total_documents == 0:
            return []

        avg_dl = (
            self.sum_doc_length / float(self.total_documents) if self.total_documents > 0 else 1.0
        )
        if avg_dl <= 0:
            avg_dl = 1.0

        n_docs = float(self.total_documents)
        scores: dict[str, float] = defaultdict(float)

        for token in query_tokens:
            df = self.doc_frequencies.get(token, 0)
            if df == 0:
                continue

            # Standard Robertson-Spärck Jones BM25 IDF formula with +1 smoothing
            idf = math.log(((n_docs - float(df) + 0.5) / (float(df) + 0.5)) + 1.0)
            if idf <= 0:
                idf = 1e-6

            postings_map = self.postings.get(token, {})
            for chunk_id, tf in postings_map.items():
                doc = self.documents[chunk_id]

                # Optional metadata filters
                if language is not None and doc.language != language:
                    continue
                if chunk_type is not None and doc.chunk_type != chunk_type:
                    continue
                if (
                    file_path is not None
                    and doc.file_path != file_path
                    and not doc.file_path.endswith(file_path)
                ):
                    continue
                if commit_sha is not None and doc.commit_sha != commit_sha:
                    continue

                doc_len = float(doc.doc_len)
                num = float(tf) * (self.k1 + 1.0)
                denom = float(tf) + self.k1 * (1.0 - self.b + self.b * (doc_len / avg_dl))

                scores[chunk_id] += idf * (num / denom)

        # Filter out non-positive scores
        candidates = [(cid, sc) for cid, sc in scores.items() if sc > 0 and math.isfinite(sc)]
        if not candidates:
            return []

        # Sort deterministically: primary = score descending, secondary = chunk_id ascending
        candidates.sort(key=lambda item: (-item[1], item[0]))

        top_candidates = candidates[:top_k]
        results: list[LexicalSearchResult] = []

        for idx, (cid, sc) in enumerate(top_candidates, start=1):
            doc = self.documents[cid]
            results.append(
                LexicalSearchResult(
                    chunk_id=doc.chunk_id,
                    score=sc,
                    rank=idx,
                    repository_id=doc.repository_id,
                    commit_id=doc.commit_id,
                    commit_sha=doc.commit_sha,
                    file_path=doc.file_path,
                    symbol_name=doc.symbol_name,
                    qualified_name=doc.qualified_name,
                    chunk_type=doc.chunk_type,
                    language=doc.language,
                    start_line=doc.start_line,
                    end_line=doc.end_line,
                    metadata=doc.metadata,
                )
            )

        return results


class BM25LexicalIndex(LexicalIndexContract):
    """Production-quality, code-aware BM25 lexical index managing isolated repository indexes."""

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        tokenizer: CodeTokenizer | None = None,
        text_builder: LexicalTextBuilder | None = None,
    ) -> None:
        if k1 < 0:
            raise LexicalConfigurationError(f"k1 must be >= 0, got {k1}")
        if not (0.0 <= b <= 1.0):
            raise LexicalConfigurationError(f"b must be between 0.0 and 1.0, got {b}")

        self.k1 = k1
        self.b = b
        self.tokenizer = tokenizer if tokenizer is not None else CodeTokenizer()
        self.text_builder = (
            text_builder
            if text_builder is not None
            else LexicalTextBuilder(tokenizer=self.tokenizer)
        )
        self._repo_indexes: dict[str, RepositoryBM25Index] = {}

    def _get_repo_index(
        self, repository_id: str, create: bool = True
    ) -> RepositoryBM25Index | None:
        if repository_id not in self._repo_indexes:
            if not create:
                return None
            self._repo_indexes[repository_id] = RepositoryBM25Index(k1=self.k1, b=self.b)
        return self._repo_indexes[repository_id]

    def add(self, chunk: CodeChunk) -> None:
        """Add or replace a CodeChunk in the lexical index."""
        doc = self.text_builder.build_document(chunk)
        repo_idx = self._get_repo_index(chunk.repository_id, create=True)
        assert repo_idx is not None
        repo_idx.add(doc)

    def add_many(self, chunks: CodeChunkCollection | Iterable[CodeChunk]) -> None:
        """Batch add a collection or iterable of CodeChunks."""
        chunk_list = chunks.chunks if isinstance(chunks, CodeChunkCollection) else list(chunks)
        for chunk in chunk_list:
            self.add(chunk)

    def remove(self, chunk_id: str, repository_id: str) -> bool:
        """Remove a chunk from a specific repository index."""
        repo_idx = self._get_repo_index(repository_id, create=False)
        if repo_idx is None:
            return False
        return repo_idx.remove(chunk_id)

    def clear(self, repository_id: str | None = None) -> None:
        """Clear a specific repository index, or all repository indexes if repository_id is None."""
        if repository_id is None:
            self._repo_indexes.clear()
        elif repository_id in self._repo_indexes:
            self._repo_indexes[repository_id].clear()

    def search(
        self,
        query: str,
        repository_id: str,
        top_k: int = 10,
        language: Language | None = None,
        chunk_type: ChunkType | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
    ) -> list[LexicalSearchResult]:
        """Execute BM25 lexical search for a repository with optional filters."""
        if top_k <= 0:
            raise LexicalQueryError(f"top_k must be > 0, got {top_k}")
        if not query or not query.strip():
            return []

        repo_idx = self._get_repo_index(repository_id, create=False)
        if repo_idx is None:
            return []

        query_tokens = tokenize_query(query)
        return repo_idx.search(
            query_tokens=query_tokens,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
            file_path=file_path,
            commit_sha=commit_sha,
        )

    def document_count(self, repository_id: str | None = None) -> int:
        """Return the number of indexed documents in a repository, or across all repositories."""
        if repository_id is not None:
            repo_idx = self._get_repo_index(repository_id, create=False)
            return repo_idx.total_documents if repo_idx is not None else 0
        return sum(repo.total_documents for repo in self._repo_indexes.values())
