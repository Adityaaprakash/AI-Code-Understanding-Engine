# Project Context — AI Code Understanding Engine

## Overview

| Field | Value |
|---|---|
| Official project name | AI Code Understanding Engine |
| Working product name | CodeLens AI |
| Deployment model | Local-first |
| Architecture style | Modular monolith + worker processes |
| Current phase | Phase 1 — Foundation |

---

## Problem Statement

Developers working on large codebases spend significant time navigating unfamiliar
code, tracing call paths, identifying the blast radius of a change, and
understanding how cross-cutting concerns (authentication, observability, data
access) are implemented.

Standard code-search tools (grep, IDE find-usages) require the developer to
already know what to search for. Standard vector-RAG chatbots retrieve chunks by
embedding similarity but have no awareness of code structure, cross-file
relationships, or symbol identity.

**CodeLens AI** answers natural-language questions about a codebase by combining:

- Structural AST analysis to build a Canonical Code IR
- A symbol relationship graph stored in PostgreSQL
- Hybrid retrieval (BM25 + vector similarity + graph traversal)
- A provider-agnostic LLM interface for answer generation

---

## Goals

1. Accept a repository (GitHub URL or local path) and index it fully.
2. Accept incremental updates via git-diff based re-indexing.
3. Answer natural-language questions about the codebase with citations.
4. Support impact analysis: "What breaks if I change X?"
5. Support dependency queries: "What does symbol Y depend on?"
6. Operate entirely locally; no mandatory cloud data upload.

---

## Non-Goals (MVP)

- Real-time collaborative editing
- Code-generation (write new code on behalf of the developer)
- IDE plugin (Phase 1 is a standalone web UI)
- Supporting repositories larger than 1 M LOC in MVP
- Languages beyond Java, Python, TypeScript in MVP

---

## MVP Languages

| Language | Rationale |
|---|---|
| Java | Large enterprise codebases; strong AST tooling via tree-sitter |
| Python | Dominant in data/ML; widely used in backend services |
| TypeScript | Dominant in frontend; typed superset enables better analysis |

---

## Deployment

- **Local**: Docker Compose. PostgreSQL + backend + frontend + worker in containers.
- **Cloud-ready**: No local-only APIs; the same images deploy to any container host.

---

## Scale Targets

| Metric | Target |
|---|---|
| Maximum repository size | ≤ 1 M LOC |
| Query P95 latency | ≤ 8 seconds |

---

## Technology Selections (Locked)

| Component | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Frontend | React (TypeScript) |
| Primary database | PostgreSQL 16 |
| Vector search | pgvector (PostgreSQL extension) |
| Full-text search | PostgreSQL BM25 (pg_bm25 / tsvector) |
| Job queue | PostgreSQL-backed (no external broker) |
| AST parsing | tree-sitter |
| LLM interface | Provider-agnostic (OpenAI / Anthropic / Ollama / Azure) |
| Embedding interface | Provider-agnostic (OpenAI / Cohere / sentence-transformers / Ollama) |
| Containerisation | Docker / Docker Compose |
