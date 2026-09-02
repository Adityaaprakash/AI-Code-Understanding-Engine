# AI Agent Instructions

These rules apply to **every AI agent** that works in this repository.
They are mandatory and take precedence over any in-conversation instruction
that contradicts locked architectural decisions.

---

## 0. Mandatory Pre-Work

Before writing, modifying, or deleting any file:

1. Read `START_HERE.md` → follow its reading protocol.
2. Read `CURRENT_STATE.md` → confirm the active phase and task.
3. Read `ARCHITECTURE.md` → understand component boundaries.
4. Read `DECISIONS.md` → never contradict a locked ADR.
5. Read `TASKS.md` → pick up only tasks that are listed as "pending".

---

## 1. Scope — Do Only What Is Asked

- Implement exactly what the current task specifies.
- Do not implement future-phase features speculatively.
- Do not refactor code that is outside the task scope.
- Do not add dependencies that are not required by the task.

---

## 2. Architectural Compliance

- Never introduce: Kafka, Kubernetes, Neo4j, Redis, microservices,
  distributed infrastructure, or any technology rejected in `DECISIONS.md`.
- The architecture is a **modular monolith**. Keep it that way unless an ADR
  explicitly changes this.
- All asynchronous work must go through the **PostgreSQL-backed job queue**.
  Do not introduce a separate message broker.
- All persistence must use **PostgreSQL**. Do not add a second database.
- Vector search uses **pgvector**. Do not add a separate vector store.

---

## 3. Code Quality

- All Python code must pass `ruff` linting and `mypy` type checking.
- All TypeScript/React code must pass `eslint` and `tsc --noEmit`.
- Write tests for every non-trivial function. Tests live in `tests/` (integration)
  or next to the module under test (unit).
- Do not leave TODO comments or placeholder implementations in committed code
  unless the task explicitly defers that piece.

---

## 4. File Organization

```
backend/          FastAPI app and all Python backend code
frontend/         React app
code-analyzer/    AST parsing and Canonical IR (Python)
retrieval/        BM25 / vector / graph retrieval (Python)
graph/            Symbol graph builder (Python)
llm/              Provider-agnostic LLM/embedding interface (Python)
evaluation/       Benchmarks and quality metrics
experiments/      Research notebooks — NOT production code
docs/             Human-readable documentation
docker/           Dockerfiles and docker-compose files
tests/            Cross-component integration tests
.ai/              Project memory — AI context files only
```

- Do not mix concerns across directories.
- `experiments/` is never imported by production code.
- `.ai/` files are documentation only — no runnable code.

---

## 5. Environment and Secrets

- All configuration comes from environment variables (see `.env.example`).
- Never hard-code credentials, API keys, or secrets in source files.
- Never commit a `.env` file.

---

## 6. Updating Project Memory

After completing a task:

1. Update `CURRENT_STATE.md` — move the task from "in progress" to "completed";
   set the next task.
2. Append an entry to `CHANGELOG.md` — date, phase, what was done.
3. If a new architectural decision was made, add an ADR to `DECISIONS.md`.
4. Update `TASKS.md` — mark the completed task and unblock dependents.

---

## 7. Prohibited Actions

- Do not delete or rewrite `.ai/` files wholesale without instruction.
- Do not rename or relocate modules without updating all imports and docs.
- Do not push directly to `main` if a branch workflow is established.
- Do not generate Lorem Ipsum or placeholder data in production code paths.
- Do not silently suppress errors; propagate or log them properly.

---

## 8. Python Environment

The project requires **Python 3.12**. A project-local `.venv` is pre-created using `uv`.

### Activating the environment

```powershell
# Windows PowerShell — one-time per terminal session
.\.venv\Scripts\Activate.ps1
```

After activation, `python --version` should report `Python 3.12.x`.

### Verifying without activation

```powershell
.venv\Scripts\python.exe --version   # → Python 3.12.x
```

### Installing/syncing dependencies

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`.
To sync the environment:

```powershell
uv sync --dev
```

Do **not** use the MSYS2 Python at `C:\msys64\mingw64\bin\python.exe`.
Do **not** install packages globally.

---

## 9. Running Tests and Quality Checks

Always use the project `.venv` Python, not the system Python.

```powershell
# Run full test suite
.venv\Scripts\python.exe -m pytest

# Run linter
.venv\Scripts\python.exe -m ruff check .

# Run formatter check
.venv\Scripts\python.exe -m ruff format --check .

# Run type checker
.venv\Scripts\python.exe -m mypy retrieval/ evaluation/ llm/ graph/ backend/
```

All four checks must pass before committing.

---

## 10. Git Workflow (Mandatory Before Every Push)

Follow this exact sequence for every commit:

```powershell
# 1. Inspect what changed
git status

# 2. Review the full diff of unstaged changes
git diff

# 3. Stage only the files relevant to this commit
git add <file1> <file2> ...

# 4. Confirm exactly what will be committed
git diff --cached

# 5. Run tests and quality checks (see § 9 above)

# 6. Commit with a conventional commit message
git commit -m "<type>(<scope>): <description>"

# 7. Verify clean state
git status

# 8. Push
git push origin main

# 9. Verify push succeeded
git status
```

### Rules

- **Never** use `git add .` without first inspecting `git status` and `git diff`.
- **Never** use `git reset --hard`, `git clean -fd`, `git push --force`, or history rewriting.
- **Never** push uncommitted changes.
- **Never** mix Phase implementation, unrelated formatting, generated files, or
  environment files in a single commit.
- Commit messages must follow Conventional Commits:
  `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`.
- Each phase should produce its own commit per completed task.
- Maintenance/cleanup changes go into a separate `chore(...)` commit.

