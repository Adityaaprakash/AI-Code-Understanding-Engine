"""Embedding provider implementations: DeterministicTestEmbeddingProvider and HostedAPIEmbeddingProvider."""

import hashlib

import httpx

from retrieval.contracts import EmbeddingProviderContract
from retrieval.embedding_models import EmbeddingInput, EmbeddingResult
from retrieval.exceptions import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
)


class DeterministicTestEmbeddingProvider(EmbeddingProviderContract):
    """Deterministic fake embedding provider for unit tests and local development.

    Uses SHA-256 digest hashing of input text to generate normalized, reproducible dense vectors.
    Requires no external network calls, API keys, or GPU dependencies.
    """

    def __init__(
        self,
        provider_name: str = "test",
        model_name: str = "test-embed-v1",
        dimension: int = 384,
        embedding_version: str = "v1.0",
    ) -> None:
        if dimension <= 0:
            raise EmbeddingConfigurationError(f"Dimension must be > 0, got {dimension}")
        self._provider_name = provider_name
        self._model_name = model_name
        self._dimension = dimension
        self._embedding_version = embedding_version

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def embedding_version(self) -> str:
        return self._embedding_version

    def embed(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        """Generate deterministic pseudo-embedding vectors for a list of inputs."""
        results: list[EmbeddingResult] = []

        for inp in inputs:
            vector = self._generate_deterministic_vector(
                text=inp.text,
                model_name=inp.model_name,
                version=inp.embedding_version,
                dim=self._dimension,
            )

            repo_id = str(inp.metadata.get("repository_id", "unknown_repo"))
            commit_id = inp.metadata.get("commit_id")
            commit_sha = inp.metadata.get("commit_sha")

            results.append(
                EmbeddingResult(
                    chunk_id=inp.chunk_id,
                    vector=vector,
                    dimension=self._dimension,
                    provider_name=self._provider_name,
                    model_name=self._model_name,
                    embedding_version=self._embedding_version,
                    repository_id=repo_id,
                    commit_id=str(commit_id) if commit_id is not None else None,
                    commit_sha=str(commit_sha) if commit_sha is not None else None,
                )
            )

        return results

    @staticmethod
    def _generate_deterministic_vector(
        text: str, model_name: str, version: str, dim: int
    ) -> list[float]:
        """Derive a normalized float vector of length `dim` deterministically from input text."""
        seed_str = f"{model_name}:{version}:{text}"
        digest = hashlib.sha256(seed_str.encode("utf-8")).digest()

        raw_values: list[float] = []
        for i in range(dim):
            # Deterministically cycle through digest bytes with index offset
            b1 = digest[i % len(digest)]
            b2 = digest[(i * 7 + 13) % len(digest)]
            # Map [0, 65535] to [-1.0, 1.0]
            val = (((b1 << 8) | b2) / 32767.5) - 1.0
            raw_values.append(val)

        # L2 normalize vector
        norm = math_sqrt(sum(v * v for v in raw_values))
        if norm == 0:
            return [1.0 / math_sqrt(dim)] * dim
        return [v / norm for v in raw_values]


class HostedAPIEmbeddingProvider(EmbeddingProviderContract):
    """Optional HTTP API provider adapter (e.g. OpenAI/Ollama compatible endpoint)."""

    def __init__(
        self,
        provider_name: str = "hosted",
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
        embedding_version: str = "v1.0",
        api_base: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if dimension <= 0:
            raise EmbeddingConfigurationError(f"Dimension must be > 0, got {dimension}")
        self._provider_name = provider_name
        self._model_name = model_name
        self._dimension = dimension
        self._embedding_version = embedding_version
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def embedding_version(self) -> str:
        return self._embedding_version

    def embed(self, inputs: list[EmbeddingInput]) -> list[EmbeddingResult]:
        """Execute batch HTTP embedding call to remote provider."""
        if not inputs:
            return []

        if not self.api_key:
            raise EmbeddingConfigurationError(
                f"API key is required for HostedAPIEmbeddingProvider ({self._provider_name})"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model_name,
            "input": [inp.text for inp in inputs],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.api_base}/embeddings",
                    headers=headers,
                    json=payload,
                )

            if response.status_code != 200:
                is_retryable = response.status_code in (429, 500, 502, 503, 504)
                raise EmbeddingProviderError(
                    f"Provider returned HTTP {response.status_code}: {response.text}",
                    retryable=is_retryable,
                )

            data = response.json()
            data_items = data.get("data", [])

            if len(data_items) != len(inputs):
                raise EmbeddingProviderError(
                    f"Provider returned {len(data_items)} vectors, expected {len(inputs)}",
                    retryable=False,
                )

            results: list[EmbeddingResult] = []
            for idx, inp in enumerate(inputs):
                raw_vec = data_items[idx].get("embedding", [])
                repo_id = str(inp.metadata.get("repository_id", "unknown_repo"))
                commit_id = inp.metadata.get("commit_id")
                commit_sha = inp.metadata.get("commit_sha")

                results.append(
                    EmbeddingResult(
                        chunk_id=inp.chunk_id,
                        vector=raw_vec,
                        dimension=self._dimension,
                        provider_name=self._provider_name,
                        model_name=self._model_name,
                        embedding_version=self._embedding_version,
                        repository_id=repo_id,
                        commit_id=str(commit_id) if commit_id is not None else None,
                        commit_sha=str(commit_sha) if commit_sha is not None else None,
                    )
                )
            return results

        except httpx.TimeoutException as exc:
            raise EmbeddingProviderError(f"HTTP request timed out: {exc}", retryable=True) from exc
        except httpx.RequestError as exc:
            raise EmbeddingProviderError(f"HTTP connection error: {exc}", retryable=True) from exc


def math_sqrt(val: float) -> float:
    """Helper sqrt function."""
    import math

    return math.sqrt(val)
