# Current State — AI Code Understanding Engine

## Active Phase

**Phase 2 — Ingestion, AST & Canonical Code IR**

---

## Current Task

TASK-2F (AST → Code IR Normalization) complete. Implemented language-specific normalizers (JavaNormalizer, PythonNormalizer, TypeScriptNormalizer) translating ASTs into language-independent Canonical Code IR. Next: TASK-2G (Symbol Extraction & Resolution).

---

## Completed

- [x] Project specification established
- [x] Architecture established
- [x] Core constraints established
- [x] Top-level directory structure created
- [x] `.gitignore` created
- [x] `.env.example` created
- [x] `README.md` created
- [x] `.ai/` project-memory files created and populated
- [x] TASK-1B: Python runtime setup complete
- [x] TASK-1C: Database foundation complete
- [x] TASK-1D: FastAPI foundation complete
- [x] TASK-1E: Test infrastructure complete
- [x] TASK-1F: Docker Compose Foundation complete
- [x] TASK-1G: Frontend Scaffold complete
- [x] TASK-1H: Phase 1 Verification complete
- [x] TASK-2A: Parser Abstraction complete
- [x] TASK-2B: Java AST complete
- [x] TASK-2C: Python AST complete
- [x] TASK-2D: TypeScript AST complete
- [x] TASK-2E: Canonical Code IR complete
- [x] TASK-2F: AST → Code IR Normalization complete
  - Normalization boundary `code_analyzer/normalization/` (`base.py`, `java.py`, `python.py`, `typescript.py`, `result.py`, `type_helper.py`, `location_helper.py`, `__init__.py`)
  - Unified normalization entry point `normalize_parse_result(parse_result, repository_id, file_path, content_hash, loc)`
  - Mapped Java, Python, and TypeScript AST nodes cleanly to canonical entities (`File`, `Module`, `Class`, `Interface`, `Function`, `Method`, `Variable`, `Parameter`, `Reference`, `Symbol`)
  - Helper functions for generic type representation parsing (`List<String>`, `list[str]`, `Promise<User>`) and source location mapping
  - Deterministic entity identity generation via `generate_entity_id` across all language normalizers
  - Comprehensive unit test suite `tests/test_normalization.py` with 13 test cases covering Java, Python, TypeScript, cross-language consistency, and idempotency
  - All quality gates pass: `uv sync` ✅ `ruff check` ✅ `ruff format --check` ✅ `pytest tests/` (100 passed) ✅

---

## In Progress

- [ ] TASK-2G — Symbol Extraction & Resolution

---

## Blocked / Pending

### Phase 1 Remaining
- [x] 1B: Python runtime setup — ✅ Done
- [x] 1C: Database foundation — ✅ Done
- [x] 1D: FastAPI skeleton — ✅ Done
- [x] 1E: Test infrastructure — ✅ Done
- [x] 1F: Docker Compose foundation — ✅ Done
- [x] 1G: Frontend scaffold — ✅ Done
- [x] 1H: Phase 1 verification — ✅ Done

### Phase 2 (Ingestion, AST & Canonical Code IR)
- [x] 2A: Parser Abstraction — ✅ Done
- [x] 2B: Java AST — ✅ Done
- [x] 2C: Python AST — ✅ Done
- [x] 2D: TypeScript AST — ✅ Done
- [x] 2E: Canonical Code IR Definition — ✅ Done
- [x] 2F: AST → Code IR Normalization — ✅ Done
- [ ] 2G: Symbol Extraction & Resolution
- [ ] 2H: Incremental AST & IR Pipeline

---

## Known Decisions Made This Phase

See `DECISIONS.md` for full ADR list.

---

## Last Updated

2026-08-28 — TASK-2F complete (AST → Code IR Normalization layer implemented; all 100 tests passing).



