"""Embedding text builder for transforming CodeChunks into semantic embedding strings."""

from typing import Any

from retrieval.embedding_models import EmbeddingInput
from retrieval.models import CodeChunk


class EmbeddingTextBuilder:
    """Builder that transforms CodeChunk objects into deterministic embedding text representations."""

    def __init__(self, include_metadata_header: bool = True) -> None:
        self.include_metadata_header = include_metadata_header

    def build_text(self, chunk: CodeChunk) -> str:
        """Construct deterministic semantic embedding text from a CodeChunk.

        Source code remains primary. Metadata headers enrich the text with structural context.

        Args:
            chunk: CodeChunk instance.

        Returns:
            Formatted deterministic embedding text string.
        """
        lines: list[str] = []

        if self.include_metadata_header:
            lines.append(f"[Language: {chunk.language.value}]")
            lines.append(f"[Path: {chunk.file_path}]")
            lines.append(f"[ChunkType: {chunk.chunk_type.value}]")

            symbol_identifier = chunk.qualified_name or chunk.name
            if symbol_identifier:
                lines.append(f"[Symbol: {symbol_identifier}]")

            if chunk.signature:
                lines.append(f"[Signature: {chunk.signature}]")

            if chunk.parent_entity_id:
                lines.append(f"[Parent: {chunk.parent_entity_id}]")

            if chunk.doc_comment:
                # Normalize multiline doc comments to single-line stripped string
                clean_doc = " ".join(
                    line.strip() for line in chunk.doc_comment.splitlines() if line.strip()
                )
                if clean_doc:
                    lines.append(f"[Doc: {clean_doc}]")

        content = chunk.content.strip() if chunk.content else ""
        if content:
            if lines:
                lines.append("")  # Blank line separator between header and code content
            lines.append(content)
        else:
            # Fallback for chunks with empty code bodies
            if lines:
                lines.append("")
            lines.append("[Content: (Empty implementation)]")

        return "\n".join(lines)

    def build_input(
        self,
        chunk: CodeChunk,
        model_name: str,
        embedding_version: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> EmbeddingInput:
        """Construct an immutable EmbeddingInput object for a CodeChunk.

        Args:
            chunk: CodeChunk instance.
            model_name: Target embedding model identifier.
            embedding_version: Target embedding version identifier.
            extra_metadata: Optional additional metadata dict.

        Returns:
            Validated EmbeddingInput.
        """
        text = self.build_text(chunk)
        meta = chunk.to_index_dict()
        if extra_metadata:
            meta.update(extra_metadata)

        return EmbeddingInput(
            chunk_id=chunk.id,
            text=text,
            metadata=meta,
            model_name=model_name,
            embedding_version=embedding_version,
        )
