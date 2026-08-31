"""Production-quality AST/IR-aware code chunking engine for CodeLens AI."""

from typing import Any

from code_analyzer.ir import Class, Function, Interface, Method, SourceLocation
from code_analyzer.normalization import NormalizationResult
from retrieval.contracts import CodeChunkerContract
from retrieval.enums import ChunkType
from retrieval.identity import generate_chunk_id
from retrieval.models import CodeChunk, CodeChunkCollection


def extract_source_text(source_code: str | None, location: SourceLocation | None) -> str:
    """Safely extract source code lines corresponding to an IR SourceLocation.

    Args:
        source_code: Raw source code string.
        location: IR SourceLocation tracking start and end line/column.

    Returns:
        Extracted source code snippet string.
    """
    if not source_code or not location:
        return ""

    lines = source_code.splitlines()
    if not lines:
        return ""

    start_idx = max(0, location.start_line - 1)
    end_idx = min(len(lines), location.end_line)

    if start_idx >= len(lines) or start_idx >= end_idx:
        return ""

    selected_lines = lines[start_idx:end_idx]
    return "\n".join(selected_lines)


class CodeChunker(CodeChunkerContract):
    """AST/IR-aware code chunker that transforms Canonical Code IR into retrievable code chunks.

    Operates purely on Canonical Code IR (NormalizationResult) without reparsing source code,
    ensuring cross-language semantic parity across Java, Python, and TypeScript.
    """

    def chunk_normalization_result(
        self,
        result: NormalizationResult,
        source_code: str | None = None,
        max_lines_per_chunk: int = 150,
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks from a single file NormalizationResult."""
        if not result or not result.file:
            return CodeChunkCollection(
                repository_id=result.file.repository_id if result and result.file else "unknown",
                chunks=[],
                file_chunk_map={},
                entity_chunk_map={},
            )

        repository_id = result.file.repository_id
        file_id = result.file.id
        file_path = result.file.path
        language = result.file.language

        raw_chunks: list[CodeChunk] = []
        seen_keys: set[tuple[str, str, int]] = set()  # (entity_id, chunk_type, sub_chunk_index)

        # 1. FILE_CONTEXT Chunk
        file_chunk = self._build_file_context_chunk(
            result=result,
            source_code=source_code,
            max_lines_per_chunk=max_lines_per_chunk,
        )
        if file_chunk:
            key = (file_chunk.entity_id or file_id, file_chunk.chunk_type.value, 0)
            if key not in seen_keys:
                seen_keys.add(key)
                raw_chunks.append(file_chunk)

        # 2. CLASS_CONTEXT Chunks
        for cls_entity in result.classes:
            cls_chunks = self._build_class_chunks(
                cls_entity=cls_entity,
                file_id=file_id,
                file_path=file_path,
                repository_id=repository_id,
                language=language,
                source_code=source_code,
                max_lines_per_chunk=max_lines_per_chunk,
            )
            for c in cls_chunks:
                key = (c.entity_id or cls_entity.id, c.chunk_type.value, c.sub_chunk_index)
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_chunks.append(c)

        # 3. INTERFACE_CONTEXT Chunks
        for iface_entity in result.interfaces:
            iface_chunks = self._build_interface_chunks(
                iface_entity=iface_entity,
                file_id=file_id,
                file_path=file_path,
                repository_id=repository_id,
                language=language,
                source_code=source_code,
                max_lines_per_chunk=max_lines_per_chunk,
            )
            for c in iface_chunks:
                key = (c.entity_id or iface_entity.id, c.chunk_type.value, c.sub_chunk_index)
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_chunks.append(c)

        # 4. FUNCTION Chunks
        for func_entity in result.functions:
            func_chunks = self._build_function_chunks(
                func_entity=func_entity,
                file_id=file_id,
                file_path=file_path,
                repository_id=repository_id,
                language=language,
                source_code=source_code,
                max_lines_per_chunk=max_lines_per_chunk,
            )
            for c in func_chunks:
                key = (c.entity_id or func_entity.id, c.chunk_type.value, c.sub_chunk_index)
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_chunks.append(c)

        # 5. METHOD Chunks
        for method_entity in result.methods:
            method_chunks = self._build_method_chunks(
                method_entity=method_entity,
                file_id=file_id,
                file_path=file_path,
                repository_id=repository_id,
                language=language,
                source_code=source_code,
                max_lines_per_chunk=max_lines_per_chunk,
            )
            for c in method_chunks:
                key = (c.entity_id or method_entity.id, c.chunk_type.value, c.sub_chunk_index)
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_chunks.append(c)

        # Deterministic Sort Rule:
        # 1. FILE_CONTEXT first
        # 2. Source start_line ASC, start_column ASC, chunk_type ASC, entity_id ASC, sub_chunk_index ASC
        sorted_chunks = sorted(raw_chunks, key=self._chunk_sort_key)

        # Build index maps
        file_map: dict[str, list[str]] = {file_id: [c.id for c in sorted_chunks]}
        entity_map: dict[str, list[str]] = {}
        for c in sorted_chunks:
            if c.entity_id:
                entity_map.setdefault(c.entity_id, []).append(c.id)

        return CodeChunkCollection(
            repository_id=repository_id,
            chunks=sorted_chunks,
            file_chunk_map=file_map,
            entity_chunk_map=entity_map,
        )

    def chunk_repository(
        self,
        results: list[NormalizationResult],
        source_files: dict[str, str] | None = None,
        max_lines_per_chunk: int = 150,
    ) -> CodeChunkCollection:
        """Generate deterministic semantic chunks across multiple NormalizationResults."""
        source_files = source_files or {}
        repo_id = results[0].file.repository_id if results and results[0].file else "unknown"

        all_chunks: list[CodeChunk] = []
        file_map: dict[str, list[str]] = {}
        entity_map: dict[str, list[str]] = {}

        # Process files in deterministic path order
        sorted_results = sorted(results, key=lambda r: r.file.path if r and r.file else "")

        for res in sorted_results:
            if not res or not res.file:
                continue
            file_code = source_files.get(res.file.path)
            file_coll = self.chunk_normalization_result(
                result=res,
                source_code=file_code,
                max_lines_per_chunk=max_lines_per_chunk,
            )
            for c in file_coll.chunks:
                all_chunks.append(c)
                file_map.setdefault(c.file_id, []).append(c.id)
                if c.entity_id:
                    entity_map.setdefault(c.entity_id, []).append(c.id)

        return CodeChunkCollection(
            repository_id=repo_id,
            chunks=all_chunks,
            file_chunk_map=file_map,
            entity_chunk_map=entity_map,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helper Builder Methods
    # ──────────────────────────────────────────────────────────────────────────

    def _build_file_context_chunk(
        self,
        result: NormalizationResult,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> CodeChunk | None:
        """Construct the FILE_CONTEXT chunk representing top-level context."""
        file_entity = result.file
        loc = file_entity.location or SourceLocation(
            file_path=file_entity.path,
            start_line=1,
            start_column=0,
            end_line=max(1, file_entity.loc),
            end_column=0,
        )

        content = ""
        if source_code:
            # Extract header lines (imports, package, top-level comments)
            lines = source_code.splitlines()
            if len(lines) <= max_lines_per_chunk:
                content = source_code
            else:
                # Capture first N lines as top-level file header
                content = "\n".join(lines[:max_lines_per_chunk])
        else:
            content = f"// File: {file_entity.path} (LOC: {file_entity.loc})"

        chunk_id = generate_chunk_id(
            repository_id=file_entity.repository_id,
            file_path=file_entity.path,
            chunk_type=ChunkType.FILE_CONTEXT,
            entity_id=file_entity.id,
            location=loc,
        )

        metadata: dict[str, Any] = {
            "module_count": len(result.modules),
            "class_count": len(result.classes),
            "interface_count": len(result.interfaces),
            "function_count": len(result.functions),
            "method_count": len(result.methods),
        }

        return CodeChunk(
            id=chunk_id,
            chunk_type=ChunkType.FILE_CONTEXT,
            repository_id=file_entity.repository_id,
            file_id=file_entity.id,
            file_path=file_entity.path,
            language=file_entity.language,
            entity_id=file_entity.id,
            parent_entity_id=file_entity.repository_id,
            name=file_entity.name or file_entity.path,
            qualified_name=file_entity.path,
            source_location=loc,
            content=content,
            doc_comment=file_entity.doc_comment,
            metadata=metadata,
        )

    def _build_class_chunks(
        self,
        cls_entity: Class,
        file_id: str,
        file_path: str,
        repository_id: str,
        language: Any,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> list[CodeChunk]:
        """Construct CLASS_CONTEXT chunk and sub-chunks if oversized."""
        loc = cls_entity.location or SourceLocation(
            file_path=file_path, start_line=1, start_column=0, end_line=1, end_column=0
        )
        total_lines = loc.end_line - loc.start_line + 1

        signature = f"class {cls_entity.name}"
        if cls_entity.superclass_ref:
            signature += f" extends {cls_entity.superclass_ref.target_qualified_name}"
        if cls_entity.interface_refs:
            ifaces = ", ".join(r.target_qualified_name for r in cls_entity.interface_refs)
            signature += f" implements {ifaces}"

        raw_content = extract_source_text(source_code, loc)
        if not raw_content:
            raw_content = f"{signature} {{\n  // Methods: {len(cls_entity.method_ids)}\n}}"

        if total_lines <= max_lines_per_chunk:
            chunk_id = generate_chunk_id(
                repository_id=repository_id,
                file_path=file_path,
                chunk_type=ChunkType.CLASS_CONTEXT,
                entity_id=cls_entity.id,
                location=loc,
            )
            return [
                CodeChunk(
                    id=chunk_id,
                    chunk_type=ChunkType.CLASS_CONTEXT,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    entity_id=cls_entity.id,
                    parent_entity_id=cls_entity.parent_id or file_id,
                    name=cls_entity.name,
                    qualified_name=cls_entity.qualified_name,
                    source_location=loc,
                    content=raw_content,
                    doc_comment=cls_entity.doc_comment,
                    signature=signature,
                    sub_chunk_index=0,
                    total_sub_chunks=1,
                    metadata={
                        "is_abstract": cls_entity.is_abstract,
                        "visibility": cls_entity.visibility,
                    },
                )
            ]

        # Oversized class sub-chunking
        return self._split_oversized_entity(
            entity_id=cls_entity.id,
            name=cls_entity.name,
            qualified_name=cls_entity.qualified_name,
            doc_comment=cls_entity.doc_comment,
            signature=signature,
            primary_chunk_type=ChunkType.CLASS_CONTEXT,
            parent_entity_id=cls_entity.parent_id or file_id,
            file_id=file_id,
            file_path=file_path,
            repository_id=repository_id,
            language=language,
            loc=loc,
            source_code=source_code,
            max_lines_per_chunk=max_lines_per_chunk,
        )

    def _build_interface_chunks(
        self,
        iface_entity: Interface,
        file_id: str,
        file_path: str,
        repository_id: str,
        language: Any,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> list[CodeChunk]:
        """Construct INTERFACE_CONTEXT chunk and sub-chunks if oversized."""
        loc = iface_entity.location or SourceLocation(
            file_path=file_path, start_line=1, start_column=0, end_line=1, end_column=0
        )
        total_lines = loc.end_line - loc.start_line + 1

        signature = f"interface {iface_entity.name}"
        if iface_entity.extends_refs:
            exts = ", ".join(r.target_qualified_name for r in iface_entity.extends_refs)
            signature += f" extends {exts}"

        raw_content = extract_source_text(source_code, loc)
        if not raw_content:
            raw_content = f"{signature} {{\n  // Methods: {len(iface_entity.method_ids)}\n}}"

        if total_lines <= max_lines_per_chunk:
            chunk_id = generate_chunk_id(
                repository_id=repository_id,
                file_path=file_path,
                chunk_type=ChunkType.INTERFACE_CONTEXT,
                entity_id=iface_entity.id,
                location=loc,
            )
            return [
                CodeChunk(
                    id=chunk_id,
                    chunk_type=ChunkType.INTERFACE_CONTEXT,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    entity_id=iface_entity.id,
                    parent_entity_id=iface_entity.parent_id or file_id,
                    name=iface_entity.name,
                    qualified_name=iface_entity.qualified_name,
                    source_location=loc,
                    content=raw_content,
                    doc_comment=iface_entity.doc_comment,
                    signature=signature,
                    sub_chunk_index=0,
                    total_sub_chunks=1,
                    metadata={"visibility": iface_entity.visibility},
                )
            ]

        return self._split_oversized_entity(
            entity_id=iface_entity.id,
            name=iface_entity.name,
            qualified_name=iface_entity.qualified_name,
            doc_comment=iface_entity.doc_comment,
            signature=signature,
            primary_chunk_type=ChunkType.INTERFACE_CONTEXT,
            parent_entity_id=iface_entity.parent_id or file_id,
            file_id=file_id,
            file_path=file_path,
            repository_id=repository_id,
            language=language,
            loc=loc,
            source_code=source_code,
            max_lines_per_chunk=max_lines_per_chunk,
        )

    def _build_function_chunks(
        self,
        func_entity: Function,
        file_id: str,
        file_path: str,
        repository_id: str,
        language: Any,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> list[CodeChunk]:
        """Construct FUNCTION chunk and sub-chunks if oversized."""
        loc = func_entity.location or SourceLocation(
            file_path=file_path, start_line=1, start_column=0, end_line=1, end_column=0
        )
        total_lines = loc.end_line - loc.start_line + 1

        param_strs = [
            f"{p.name}: {p.declared_type}" if p.declared_type else p.name
            for p in func_entity.parameters
        ]
        ret_str = f" -> {func_entity.return_type}" if func_entity.return_type else ""
        signature = f"def {func_entity.name}({', '.join(param_strs)}){ret_str}"

        raw_content = extract_source_text(source_code, loc)
        if not raw_content:
            raw_content = f"{signature}\n    ..."

        if total_lines <= max_lines_per_chunk:
            chunk_id = generate_chunk_id(
                repository_id=repository_id,
                file_path=file_path,
                chunk_type=ChunkType.FUNCTION,
                entity_id=func_entity.id,
                location=loc,
            )
            return [
                CodeChunk(
                    id=chunk_id,
                    chunk_type=ChunkType.FUNCTION,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    entity_id=func_entity.id,
                    parent_entity_id=func_entity.parent_id or file_id,
                    name=func_entity.name,
                    qualified_name=func_entity.qualified_name,
                    source_location=loc,
                    content=raw_content,
                    doc_comment=func_entity.doc_comment,
                    signature=signature,
                    sub_chunk_index=0,
                    total_sub_chunks=1,
                    metadata={
                        "is_async": func_entity.is_async,
                        "visibility": func_entity.visibility,
                    },
                )
            ]

        return self._split_oversized_entity(
            entity_id=func_entity.id,
            name=func_entity.name,
            qualified_name=func_entity.qualified_name,
            doc_comment=func_entity.doc_comment,
            signature=signature,
            primary_chunk_type=ChunkType.FUNCTION,
            parent_entity_id=func_entity.parent_id or file_id,
            file_id=file_id,
            file_path=file_path,
            repository_id=repository_id,
            language=language,
            loc=loc,
            source_code=source_code,
            max_lines_per_chunk=max_lines_per_chunk,
        )

    def _build_method_chunks(
        self,
        method_entity: Method,
        file_id: str,
        file_path: str,
        repository_id: str,
        language: Any,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> list[CodeChunk]:
        """Construct METHOD chunk and sub-chunks if oversized."""
        loc = method_entity.location or SourceLocation(
            file_path=file_path, start_line=1, start_column=0, end_line=1, end_column=0
        )
        total_lines = loc.end_line - loc.start_line + 1

        param_strs = [
            f"{p.name}: {p.declared_type}" if p.declared_type else p.name
            for p in method_entity.parameters
        ]
        ret_str = f" -> {method_entity.return_type}" if method_entity.return_type else ""
        prefix = "static " if method_entity.is_static else ""
        signature = f"{prefix}def {method_entity.name}({', '.join(param_strs)}){ret_str}"

        raw_content = extract_source_text(source_code, loc)
        if not raw_content:
            raw_content = f"{signature}\n    ..."

        parent_id = method_entity.class_id or file_id

        if total_lines <= max_lines_per_chunk:
            chunk_id = generate_chunk_id(
                repository_id=repository_id,
                file_path=file_path,
                chunk_type=ChunkType.METHOD,
                entity_id=method_entity.id,
                location=loc,
            )
            return [
                CodeChunk(
                    id=chunk_id,
                    chunk_type=ChunkType.METHOD,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    entity_id=method_entity.id,
                    parent_entity_id=parent_id,
                    name=method_entity.name,
                    qualified_name=method_entity.qualified_name,
                    source_location=loc,
                    content=raw_content,
                    doc_comment=method_entity.doc_comment,
                    signature=signature,
                    sub_chunk_index=0,
                    total_sub_chunks=1,
                    metadata={
                        "is_async": method_entity.is_async,
                        "is_static": method_entity.is_static,
                        "is_constructor": method_entity.is_constructor,
                        "visibility": method_entity.visibility,
                    },
                )
            ]

        return self._split_oversized_entity(
            entity_id=method_entity.id,
            name=method_entity.name,
            qualified_name=method_entity.qualified_name,
            doc_comment=method_entity.doc_comment,
            signature=signature,
            primary_chunk_type=ChunkType.METHOD,
            parent_entity_id=parent_id,
            file_id=file_id,
            file_path=file_path,
            repository_id=repository_id,
            language=language,
            loc=loc,
            source_code=source_code,
            max_lines_per_chunk=max_lines_per_chunk,
        )

    def _split_oversized_entity(
        self,
        entity_id: str,
        name: str,
        qualified_name: str,
        doc_comment: str | None,
        signature: str,
        primary_chunk_type: ChunkType,
        parent_entity_id: str,
        file_id: str,
        file_path: str,
        repository_id: str,
        language: Any,
        loc: SourceLocation,
        source_code: str | None,
        max_lines_per_chunk: int,
    ) -> list[CodeChunk]:
        """Hierarchical deterministic fallback for splitting oversized entities into sub-chunks.

        Preserves parent entity identity, source location sub-ranges, and exact source ordering.
        """
        start_line = loc.start_line
        end_line = loc.end_line
        total_lines = end_line - start_line + 1

        # Calculate number of sub-chunks required
        num_sub_chunks = (total_lines + max_lines_per_chunk - 1) // max_lines_per_chunk
        num_sub_chunks = max(1, num_sub_chunks)

        # Primary chunk (sub_chunk_index=0) acts as entity header / overview
        primary_chunk_id = generate_chunk_id(
            repository_id=repository_id,
            file_path=file_path,
            chunk_type=primary_chunk_type,
            entity_id=entity_id,
            location=loc,
            sub_chunk_index=0,
        )

        header_end = min(end_line, start_line + max_lines_per_chunk - 1)
        header_loc = SourceLocation(
            file_path=file_path,
            start_line=start_line,
            start_column=loc.start_column,
            end_line=header_end,
            end_column=loc.end_column if header_end == end_line else 0,
        )
        header_content = (
            extract_source_text(source_code, header_loc) if source_code else f"{signature}\n    ..."
        )

        primary_chunk = CodeChunk(
            id=primary_chunk_id,
            chunk_type=primary_chunk_type,
            repository_id=repository_id,
            file_id=file_id,
            file_path=file_path,
            language=language,
            entity_id=entity_id,
            parent_entity_id=parent_entity_id,
            name=name,
            qualified_name=qualified_name,
            source_location=header_loc,
            content=header_content,
            doc_comment=doc_comment,
            signature=signature,
            sub_chunk_index=0,
            total_sub_chunks=num_sub_chunks,
            metadata={"oversized": True},
        )

        chunks: list[CodeChunk] = [primary_chunk]

        # Remaining sub-chunks (sub_chunk_index 1..N-1)
        curr_start = header_end + 1
        sub_idx = 1
        while curr_start <= end_line:
            curr_end = min(end_line, curr_start + max_lines_per_chunk - 1)
            sub_loc = SourceLocation(
                file_path=file_path,
                start_line=curr_start,
                start_column=0,
                end_line=curr_end,
                end_column=loc.end_column if curr_end == end_line else 0,
            )
            sub_content = (
                extract_source_text(source_code, sub_loc)
                if source_code
                else f"// Sub-chunk {sub_idx} ({curr_start}-{curr_end})"
            )

            sub_chunk_id = generate_chunk_id(
                repository_id=repository_id,
                file_path=file_path,
                chunk_type=ChunkType.SUB_CHUNK,
                entity_id=entity_id,
                location=sub_loc,
                sub_chunk_index=sub_idx,
            )

            chunks.append(
                CodeChunk(
                    id=sub_chunk_id,
                    chunk_type=ChunkType.SUB_CHUNK,
                    repository_id=repository_id,
                    file_id=file_id,
                    file_path=file_path,
                    language=language,
                    entity_id=entity_id,
                    parent_entity_id=entity_id,
                    parent_chunk_id=primary_chunk_id,
                    name=name,
                    qualified_name=qualified_name,
                    source_location=sub_loc,
                    content=sub_content,
                    doc_comment=doc_comment,
                    signature=signature,
                    sub_chunk_index=sub_idx,
                    total_sub_chunks=num_sub_chunks,
                    metadata={"oversized": True},
                )
            )
            curr_start = curr_end + 1
            sub_idx += 1

        return chunks

    def _chunk_sort_key(self, c: CodeChunk) -> tuple[int, int, int, str, str, int]:
        """Key function for deterministic source ordering."""
        # FILE_CONTEXT gets priority 0, others get priority 1
        type_priority = 0 if c.chunk_type == ChunkType.FILE_CONTEXT else 1
        start_line = c.source_location.start_line if c.source_location else 0
        start_col = c.source_location.start_column if c.source_location else 0
        return (
            type_priority,
            start_line,
            start_col,
            c.chunk_type.value,
            c.entity_id or "",
            c.sub_chunk_index,
        )
