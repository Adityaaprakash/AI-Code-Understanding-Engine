import logging
import os
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.repository import Repository
from backend.services.graph_service import graph_service
from backend.services.query import query_service
from code_analyzer.normalization import normalize_parse_result
from code_analyzer.parsers import JavaParser, PythonParser, TypeScriptParser
from code_analyzer.resolution import RelationshipExtractor, SymbolTable
from retrieval.chunker import CodeChunker
from retrieval.embedding_models import EmbeddingInput

logger = logging.getLogger(__name__)


class DemoIndexer:
    @staticmethod
    async def index_repository(repo_id: uuid.UUID, session: AsyncSession) -> dict:
        """Synchronous in-memory pipeline for Phase 9H Demo.
        Populates global in-memory stores needed for the demo.
        """
        logger.info(f"Starting DEMO index for repo {repo_id}")

        repo = await session.get(Repository, repo_id)
        if not repo:
            raise ValueError("Repository not found")

        if not repo.local_path:
            raise ValueError("Repository local_path is missing")

        repo_path = Path(repo.local_path).resolve()
        if not repo_path.exists():
            raise ValueError(f"Repository local path does not exist: {repo_path}")

        repo.status = "indexing"
        await session.flush()

        try:
            py_parser = PythonParser()
            java_parser = JavaParser()
            ts_parser = TypeScriptParser()

            results = []
            source_files = {}

            for root, _, files in os.walk(repo_path):
                # Skip common junk directories
                if any(
                    skip in Path(root).parts
                    for skip in [
                        ".git",
                        "__pycache__",
                        ".venv",
                        "node_modules",
                        ".pytest_cache",
                        ".ai",
                    ]
                ):
                    continue

                for f in files:
                    fpath = Path(root) / f
                    ext = fpath.suffix

                    parser = None
                    if ext == ".py":
                        parser = py_parser
                    elif ext == ".java":
                        parser = java_parser
                    elif ext in (".ts", ".tsx"):
                        parser = ts_parser

                    if parser:
                        try:
                            content = fpath.read_text(encoding="utf-8")
                        except Exception:
                            continue

                        rel_path = str(fpath.relative_to(repo_path)).replace("\\", "/")
                        parse_res = parser.parse(content, source_path=rel_path)
                        if parse_res.success:
                            norm = normalize_parse_result(parse_res, str(repo_id))
                            results.append(norm)
                            source_files[rel_path] = content

            if not results:
                raise ValueError("No parsable files found.")

            logger.info(f"Parsed {len(results)} files.")

            # Phase 2-3: Graph construction
            st = SymbolTable()
            for norm in results:
                st.register_normalization_result(norm, str(repo_id))

            extractor = RelationshipExtractor()
            all_nodes = []
            all_edges = []
            for norm in results:
                nodes, edges = extractor.extract_from_normalization_result(norm, st)
                all_nodes.extend(nodes)
                all_edges.extend(edges)

            # Clear and inject into global in-memory GraphStore
            graph_service.store.clear()
            graph_service.store.add_nodes(all_nodes)
            graph_service.store.add_edges(all_edges)

            logger.info(f"Graph created: {len(all_nodes)} nodes, {len(all_edges)} edges.")

            # Phase 4: Chunking
            chunker = CodeChunker()
            chunk_collection = chunker.chunk_repository(
                results=results,
                source_files=source_files,
                max_lines_per_chunk=150,
                commit_sha="demo-commit",
            )

            # Clear and inject into global in-memory Retrieval stores
            query_service.lexical_index.clear(str(repo_id))
            query_service.vector_index.clear(str(repo_id))

            embed_inputs = []
            for chunk in chunk_collection.chunks:
                query_service.lexical_index.add(chunk)

                inp = EmbeddingInput(
                    text=chunk.content or chunk.signature or "",
                    model_name=query_service.embedding_provider.model_name,
                    embedding_version=query_service.embedding_provider.embedding_version,
                    chunk_id=chunk.id,
                    metadata={"repository_id": chunk.repository_id, "commit_sha": chunk.commit_sha},
                )
                embed_inputs.append((inp, chunk))

            # Batch embed and add to vector index
            if embed_inputs:
                inputs = [i[0] for i in embed_inputs]
                embeddings = query_service.embedding_provider.embed(inputs)
                for emb, (_, chunk) in zip(embeddings, embed_inputs):
                    query_service.vector_index.add(emb, chunk)

            logger.info(f"Indexed {len(chunk_collection.chunks)} chunks.")

            # Mark success
            repo.status = "indexed"
            await session.flush()

            return {
                "files_parsed": len(results),
                "nodes_created": len(all_nodes),
                "edges_created": len(all_edges),
                "chunks_indexed": len(chunk_collection.chunks),
            }

        except Exception as e:
            logger.exception("Demo indexing failed")
            repo.status = "error"
            await session.flush()
            raise e from None
