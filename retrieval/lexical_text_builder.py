"""Lexical text builder for constructing field-weighted LexicalDocument objects from CodeChunks."""

from retrieval.lexical_models import LexicalDocument
from retrieval.models import CodeChunk
from retrieval.tokenizer import CodeTokenizer, tokenize_code


class LexicalTextBuilder:
    """Builder that transforms CodeChunk instances into field-weighted LexicalDocuments."""

    def __init__(self, tokenizer: CodeTokenizer | None = None) -> None:
        self.tokenizer = tokenizer if tokenizer is not None else CodeTokenizer()

    def build_document(self, chunk: CodeChunk) -> LexicalDocument:
        """Construct an immutable LexicalDocument from a CodeChunk with explicit field weighting.

        Args:
            chunk: CodeChunk instance.

        Returns:
            Validated LexicalDocument with tokenized fields and flattened token stream.
        """
        field_tokens: dict[str, list[str]] = {}
        all_tokens: list[str] = []

        # 1. Symbol Name (Weight: 10.0)
        symbol_name = chunk.name
        if symbol_name:
            t_symbol = self.tokenizer.tokenize(symbol_name)
            field_tokens["symbol_name"] = t_symbol
            all_tokens.extend(t_symbol * 10)

        # 2. Qualified Name (Weight: 5.0)
        if chunk.qualified_name and chunk.qualified_name != symbol_name:
            t_qual = self.tokenizer.tokenize(chunk.qualified_name)
            field_tokens["qualified_name"] = t_qual
            all_tokens.extend(t_qual * 5)

        # 3. File Path (Weight: 3.0)
        if chunk.file_path:
            t_path = self.tokenizer.tokenize(chunk.file_path)
            field_tokens["file_path"] = t_path
            all_tokens.extend(t_path * 3)

        # 4. Signature (Weight: 3.0)
        if chunk.signature:
            t_sig = self.tokenizer.tokenize(chunk.signature)
            field_tokens["signature"] = t_sig
            all_tokens.extend(t_sig * 3)

        # 5. Doc Comment (Weight: 1.5)
        if chunk.doc_comment:
            t_doc = self.tokenizer.tokenize(chunk.doc_comment)
            field_tokens["doc_comment"] = t_doc
            all_tokens.extend(t_doc)

        # 6. Source Content (Weight: 1.0)
        if chunk.content and chunk.content.strip():
            t_content = self.tokenizer.tokenize(chunk.content)
            field_tokens["content"] = t_content
            all_tokens.extend(t_content)

        # Empty fallback handling: ensure doc_len > 0 if chunk has zero content/metadata tokens
        if not all_tokens:
            fallback_tokens = self.tokenizer.tokenize(chunk.file_path) or tokenize_code(chunk.id)
            field_tokens["fallback"] = fallback_tokens
            all_tokens.extend(fallback_tokens)

        symbol_label = chunk.qualified_name or chunk.name

        return LexicalDocument(
            chunk_id=chunk.id,
            repository_id=chunk.repository_id,
            commit_id=chunk.commit_id,
            commit_sha=chunk.commit_sha,
            file_path=chunk.file_path,
            symbol_name=symbol_label,
            chunk_type=chunk.chunk_type,
            language=chunk.language,
            field_tokens=field_tokens,
            all_tokens=all_tokens,
            doc_len=len(all_tokens),
        )
