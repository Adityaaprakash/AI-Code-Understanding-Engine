"""High-level EmbeddingPipeline orchestrator service."""

import logging
from collections.abc import Iterable

from retrieval.contracts import EmbeddingProviderContract
from retrieval.embedding_models import (
    EmbeddingBatchResult,
    EmbeddingFailure,
    EmbeddingInput,
    EmbeddingResult,
)
from retrieval.exceptions import (
    EmbeddingBatchError,
    EmbeddingConfigurationError,
    EmbeddingDimensionError,
    EmbeddingInputError,
    EmbeddingProviderError,
)
from retrieval.models import CodeChunk, CodeChunkCollection
from retrieval.providers import DeterministicTestEmbeddingProvider
from retrieval.text_builder import EmbeddingTextBuilder

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Production-quality, provider-agnostic embedding pipeline service.

    Transforms CodeChunks into validated dense vector embeddings using an abstract provider.
    Handles chunk validation, text construction, batching, vector dimension verification,
    identity mapping, and retry policies.
    """

    def __init__(
        self,
        provider: EmbeddingProviderContract | None = None,
        text_builder: EmbeddingTextBuilder | None = None,
        batch_size: int = 32,
        max_retries: int = 3,
        raise_on_failure: bool = True,
    ) -> None:
        if batch_size <= 0:
            raise EmbeddingConfigurationError(f"batch_size must be > 0, got {batch_size}")
        if max_retries < 0:
            raise EmbeddingConfigurationError(f"max_retries must be >= 0, got {max_retries}")

        self.provider = provider if provider is not None else DeterministicTestEmbeddingProvider()
        self.text_builder = text_builder if text_builder is not None else EmbeddingTextBuilder()
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.raise_on_failure = raise_on_failure

    def embed_chunks(
        self,
        chunks: CodeChunkCollection | Iterable[CodeChunk],
    ) -> EmbeddingBatchResult:
        """Embed a collection or iterable of CodeChunks into dense vector results.

        Args:
            chunks: CodeChunkCollection or iterable of CodeChunk instances.

        Returns:
            Immutable EmbeddingBatchResult containing results and failure records.
        """
        chunk_list: list[CodeChunk]
        if isinstance(chunks, CodeChunkCollection):
            chunk_list = chunks.chunks
        else:
            chunk_list = list(chunks)

        # 1. Empty collection handling
        if not chunk_list:
            return EmbeddingBatchResult(
                results=[],
                failures=[],
                provider_name=self.provider.provider_name,
                model_name=self.provider.model_name,
                dimension=self.provider.dimension,
                embedding_version=self.provider.embedding_version,
            )

        # 2. Duplicate chunk ID detection
        seen_ids: set[str] = set()
        for chunk in chunk_list:
            if chunk.id in seen_ids:
                raise EmbeddingInputError(
                    f"Duplicate chunk ID detected in batch input: '{chunk.id}'"
                )
            seen_ids.add(chunk.id)

        # 3. Transform chunks to EmbeddingInput objects
        inputs: list[EmbeddingInput] = [
            self.text_builder.build_input(
                chunk=chunk,
                model_name=self.provider.model_name,
                embedding_version=self.provider.embedding_version,
            )
            for chunk in chunk_list
        ]

        all_results: list[EmbeddingResult] = []
        all_failures: list[EmbeddingFailure] = []

        # 4. Process in batches
        for i in range(0, len(inputs), self.batch_size):
            batch = inputs[i : i + self.batch_size]
            batch_results, batch_failures = self._process_batch_with_retry(batch)
            all_results.extend(batch_results)
            all_failures.extend(batch_failures)

        return EmbeddingBatchResult(
            results=all_results,
            failures=all_failures,
            provider_name=self.provider.provider_name,
            model_name=self.provider.model_name,
            dimension=self.provider.dimension,
            embedding_version=self.provider.embedding_version,
        )

    def embed_chunk(self, chunk: CodeChunk) -> EmbeddingResult:
        """Embed a single CodeChunk into an EmbeddingResult.

        Delegates to embed_chunks batch pipeline.

        Args:
            chunk: CodeChunk instance.

        Returns:
            Single EmbeddingResult for the chunk.
        """
        batch_res = self.embed_chunks([chunk])
        if batch_res.failures:
            first_fail = batch_res.failures[0]
            raise EmbeddingProviderError(
                f"Failed to embed chunk '{chunk.id}': {first_fail.error_message}",
                retryable=first_fail.retryable,
            )
        return batch_res.results[0]

    def _process_batch_with_retry(
        self,
        batch: list[EmbeddingInput],
    ) -> tuple[list[EmbeddingResult], list[EmbeddingFailure]]:
        """Process a single batch of EmbeddingInputs with retries and output validation."""
        attempt = 0
        last_error: Exception | None = None

        while attempt <= self.max_retries:
            try:
                raw_results = self.provider.embed(batch)
                self._validate_provider_batch_output(batch, raw_results)
                return raw_results, []
            except (EmbeddingProviderError, EmbeddingDimensionError, EmbeddingBatchError) as exc:
                last_error = exc
                attempt += 1
                is_retryable = getattr(exc, "retryable", True)
                if not is_retryable or attempt > self.max_retries:
                    break
                logger.warning(
                    "Retrying embedding batch attempt %d/%d due to: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )

        if self.raise_on_failure and last_error:
            raise last_error

        # Format partial failure records if raise_on_failure is False
        error_msg = str(last_error) if last_error else "Unknown batch failure"
        failures = [
            EmbeddingFailure(
                chunk_id=inp.chunk_id,
                error_message=error_msg,
                retryable=getattr(last_error, "retryable", False),
            )
            for inp in batch
        ]
        return [], failures

    def _validate_provider_batch_output(
        self,
        inputs: list[EmbeddingInput],
        results: list[EmbeddingResult],
    ) -> None:
        """Verify vector count, identity mapping, and vector dimensions."""
        if len(results) != len(inputs):
            raise EmbeddingBatchError(
                f"Provider returned {len(results)} results for batch of {len(inputs)} inputs"
            )

        for inp, res in zip(inputs, results, strict=True):
            if res.chunk_id != inp.chunk_id:
                raise EmbeddingBatchError(
                    f"Chunk ID mismatch in provider result: expected '{inp.chunk_id}', got '{res.chunk_id}'"
                )
            if res.dimension != self.provider.dimension:
                raise EmbeddingDimensionError(
                    f"Provider returned vector dimension {res.dimension}, expected {self.provider.dimension}"
                )
