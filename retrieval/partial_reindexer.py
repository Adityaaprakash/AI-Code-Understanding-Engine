"""Partial re-indexing models and execution plans for Phase 8C."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.git.models import ChangedSymbolResult, ChangeType, OpaqueFile
from code_analyzer.normalization import NormalizationResult
from retrieval.contracts import (
    CodeChunkerContract,
    EmbeddingProviderContract,
    LexicalIndexContract,
    VectorIndexContract,
)
from retrieval.embedding_models import EmbeddingResult
from retrieval.models import CodeChunk, CodeChunkCollection


class PartialReindexPlan(BaseModel):
    """Deterministic plan for a partial re-index operation derived from git diffs."""

    model_config = ConfigDict(frozen=True)

    repository_id: str
    base_commit: str
    target_commit: str

    files_added: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    files_deleted: list[str] = Field(default_factory=list)

    chunks_to_remove: list[str] = Field(default_factory=list)  # Stale chunk IDs
    chunks_to_add: list[CodeChunk] = Field(default_factory=list)  # New chunk objects
    embeddings_to_reuse: list[EmbeddingResult] = Field(default_factory=list)  # Matched identity

    opaque_files: list[OpaqueFile] = Field(default_factory=list)

    @property
    def chunks_to_embed(self) -> list[CodeChunk]:
        """Chunks that require net-new embedding generation (not reused)."""
        reused_ids = {e.chunk_id for e in self.embeddings_to_reuse}
        return [c for c in self.chunks_to_add if c.id not in reused_ids]


class PartialReindexPlanner:
    """Side-effect free planner calculating deterministic indexing updates."""

    def __init__(
        self,
        chunker: CodeChunkerContract,
        text_builder_cls: Any = None,
        provider: EmbeddingProviderContract | None = None,
    ):
        self.chunker = chunker
        self.provider = provider
        # Lazy import of EmbeddingTextBuilder to check content identity
        from retrieval.text_builder import EmbeddingTextBuilder

        self.text_builder = text_builder_cls() if text_builder_cls else EmbeddingTextBuilder()

    def plan(
        self,
        changed_result: ChangedSymbolResult,
        old_chunk_collection: CodeChunkCollection,
        old_embeddings: dict[str, EmbeddingResult],
        new_normalization_results: dict[str, NormalizationResult],
        new_source_codes: dict[str, str],
        repository_id: str,
    ) -> PartialReindexPlan:
        """Calculate the precise partial re-index plan for the repository."""
        # Step 1: Identify all affected files
        files_added = []
        files_modified = []
        files_deleted = []
        opaque_files = []

        affected_files_set = set()

        for opaque in changed_result.opaque_files:
            opaque_files.append(opaque)
            if opaque.change_type == ChangeType.DELETED:
                affected_files_set.add(opaque.path)
                files_deleted.append(opaque.path)
            # We purposely do NOT add ADDED or MODIFIED opaque files to affected_files_set
            # to PRESERVE their existing chunks and avoid lossy removal of active knowledge.
            elif opaque.change_type == ChangeType.ADDED:
                files_added.append(opaque.path)
            else:
                files_modified.append(opaque.path)

        for changed in changed_result.changed_symbols:
            if changed.file_path not in affected_files_set:
                affected_files_set.add(changed.file_path)
                # Infer change type from the symbols (simplified file heuristic if not passed explicitly)
                files_modified.append(changed.file_path)

            if changed.previous_file_path and changed.previous_file_path not in affected_files_set:
                affected_files_set.add(changed.previous_file_path)
                files_modified.append(changed.previous_file_path)

        # Re-verify against normalization inputs
        for filepath in new_normalization_results:
            if filepath not in affected_files_set:
                affected_files_set.add(filepath)
                files_modified.append(filepath)

        # Note: Since the real file operations are inferred from ChangedSymbolResult,
        # we will process any file touched in `affected_files_set`.
        # Any file in the set needs to be completely re-chunked if it exists, or deleted if missed.

        chunks_to_remove = []
        chunks_to_add = []
        embeddings_to_reuse = []

        # We need chunk ID to old embedding text to evaluate reuse
        old_chunk_text_map = {}
        for chunk in old_chunk_collection.chunks:
            if chunk.file_path in affected_files_set:
                chunks_to_remove.append(chunk.id)
                old_chunk_text_map[chunk.id] = self.text_builder.build_text(chunk)

        # Build new chunks for affected files that still exist
        for filepath, norm_result in new_normalization_results.items():
            source_code = new_source_codes.get(filepath)
            new_chunks_coll = self.chunker.chunk_normalization_result(
                result=norm_result,
                source_code=source_code,
                commit_id=None,
                commit_sha=changed_result.target_commit,
            )

            # Evaluate embedding reuse for each new chunk
            for new_chunk in new_chunks_coll.chunks:
                chunks_to_add.append(new_chunk)
                new_text = self.text_builder.build_text(new_chunk)

                # Find any old chunk in the SAME FILE with EXACTLY the same semantic text
                # to safely transfer the embedding.
                # Optimization: check old chunks by symbol ID, then by text
                matched_old_chunk_id = None

                # First try to match by exact previous symbol mapping if available
                # (though IDENTITY_ONLY ensures we know exact shifts)
                # (though IDENTITY_ONLY ensures we know exact shifts)
                # also include previous_file_path if it was renamed!
                # We'll just check all removed chunks from the entire repo for safety, but
                # restrict to affected files to bound performance.

                for old_chunk in old_chunk_collection.chunks:
                    if old_chunk.id in chunks_to_remove:
                        old_text = old_chunk_text_map.get(old_chunk.id)
                        if old_text == new_text and old_chunk.chunk_type == new_chunk.chunk_type:
                            if old_chunk.id in old_embeddings:
                                matched_old_chunk_id = old_chunk.id
                                break

                if matched_old_chunk_id:
                    old_emb = old_embeddings[matched_old_chunk_id]

                    if self.provider:
                        # Validate embedding configuration compatibility
                        if (
                            old_emb.provider_name != self.provider.provider_name
                            or old_emb.model_name != self.provider.model_name
                            or old_emb.embedding_version != self.provider.embedding_version
                            or old_emb.dimension != self.provider.dimension
                        ):
                            matched_old_chunk_id = None

                if matched_old_chunk_id:
                    old_emb = old_embeddings[matched_old_chunk_id]
                    # Create new embedding result linked to new chunk_id
                    reused_emb = EmbeddingResult(
                        chunk_id=new_chunk.id,
                        vector=old_emb.vector,
                        dimension=old_emb.dimension,
                        provider_name=old_emb.provider_name,
                        model_name=old_emb.model_name,
                        embedding_version=old_emb.embedding_version,
                        repository_id=repository_id,
                        commit_id=None,
                        commit_sha=changed_result.target_commit,
                    )
                    embeddings_to_reuse.append(reused_emb)

        return PartialReindexPlan(
            repository_id=repository_id,
            base_commit=changed_result.base_commit,
            target_commit=changed_result.target_commit,
            files_added=list(set(files_added)),
            files_modified=list(set(files_modified)),
            files_deleted=list(set(files_deleted)),
            chunks_to_remove=chunks_to_remove,
            chunks_to_add=chunks_to_add,
            embeddings_to_reuse=embeddings_to_reuse,
            opaque_files=list(set(opaque_files)),
        )


class PartialReindexer:
    """Executes a PartialReindexPlan to mutate index state safely."""

    def __init__(
        self,
        lexical_index: LexicalIndexContract,
        vector_index: VectorIndexContract,
        embedding_provider: EmbeddingProviderContract,
    ):
        self.lexical_index = lexical_index
        self.vector_index = vector_index
        self.embedding_provider = embedding_provider

    def execute(self, plan: PartialReindexPlan) -> dict[str, Any]:
        """Apply plan to indices."""

        # 1. PREPARE: Generate new embeddings for non-reused chunks before any mutation
        chunks_to_embed = plan.chunks_to_embed
        final_embs = []
        if chunks_to_embed:
            from retrieval.embedding_models import EmbeddingInput

            inputs = []

            # Use text builder
            from retrieval.text_builder import EmbeddingTextBuilder

            text_builder = EmbeddingTextBuilder()

            for chunk in chunks_to_embed:
                text = text_builder.build_text(chunk)
                inputs.append(
                    EmbeddingInput(
                        chunk_id=chunk.id,
                        text=text,
                        model_name=self.embedding_provider.model_name,
                        embedding_version=self.embedding_provider.embedding_version,
                    )
                )

            # Execution happens here. If provider fails, exception is raised, index remains UNTOUCHED.
            new_embs = self.embedding_provider.embed(inputs)

            # Fix up metadata for indexing
            for em in new_embs:
                final_embs.append(
                    EmbeddingResult(
                        chunk_id=em.chunk_id,
                        vector=em.vector,
                        dimension=em.dimension,
                        provider_name=em.provider_name,
                        model_name=em.model_name,
                        embedding_version=em.embedding_version,
                        repository_id=plan.repository_id,
                        commit_sha=plan.target_commit,
                    )
                )

        # 2. APPLY MUTATIONS: Remove stale chunks from both indices
        for chunk_id in plan.chunks_to_remove:
            self.lexical_index.remove(chunk_id, plan.repository_id)
            self.vector_index.remove(chunk_id, plan.repository_id)

        # 3. Add new chunks to lexical index
        self.lexical_index.add_many(plan.chunks_to_add)

        # 4. Add reused embeddings to vector index
        chunk_map = {c.id: c for c in plan.chunks_to_add}
        self.vector_index.add_many(plan.embeddings_to_reuse, chunks=chunk_map)

        # 5. Add newly generated embeddings to vector index
        if final_embs:
            self.vector_index.add_many(final_embs, chunks=chunk_map)

        return {
            "chunks_removed": len(plan.chunks_to_remove),
            "chunks_added": len(plan.chunks_to_add),
            "embeddings_reused": len(plan.embeddings_to_reuse),
            "embeddings_generated": len(chunks_to_embed),
        }
