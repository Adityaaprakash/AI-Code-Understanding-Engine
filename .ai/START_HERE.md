# START HERE — AI Agent Entry Point

> **The repository is the source of truth, not the AI conversation.**

---

## Mandatory Reading Protocol

Every AI agent working on this repository **must** read the following files
**in order** before writing, modifying, or deleting any code:

1. [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) — What this project is, what it does, and why.
2. [`AI_INSTRUCTIONS.md`](AI_INSTRUCTIONS.md) — Behavioural rules and constraints for AI agents.
3. [`CURRENT_STATE.md`](CURRENT_STATE.md) — Live development phase, what is done, what is in progress.
4. [`ARCHITECTURE.md`](ARCHITECTURE.md) — System architecture, component responsibilities, data flows.
5. [`DECISIONS.md`](DECISIONS.md) — Locked architectural decision records (ADRs). Do not contradict them.
6. [`TASKS.md`](TASKS.md) — The current set of small, independently implementable tasks.

---

## Why This Protocol Exists

AI agents start each conversation without memory of previous sessions.
Without context, agents make decisions that contradict the architecture,
reintroduce rejected technologies, or duplicate existing work.

These `.ai/` files are the shared memory of this project.
Reading them before acting is **not optional**.

---

## Quick Reference

| File | Purpose |
|---|---|
| `START_HERE.md` | This file — entry point |
| `PROJECT_CONTEXT.md` | Goals, scope, constraints, non-goals |
| `AI_INSTRUCTIONS.md` | Agent behaviour rules |
| `CURRENT_STATE.md` | Live phase and task tracker |
| `ARCHITECTURE.md` | Full system architecture |
| `DECISIONS.md` | Locked ADRs |
| `ROADMAP.md` | Full development roadmap |
| `TASKS.md` | Current phase task list |
| `CODE_IR.md` | Canonical Code IR specification |
| `DATABASE_SCHEMA.md` | Intended database schema |
| `API_CONTRACTS.md` | Intended REST API contracts |
| `RETRIEVAL.md` | Retrieval architecture specification |
| `CHANGELOG.md` | Record of completed work |

---

## Architectural Restrictions (Summary)

The following are **permanently prohibited** unless explicitly unlocked by the
human developer in a new ADR:

- Kafka, RabbitMQ, or any message broker
- Kubernetes or container orchestration
- Neo4j or any dedicated graph database
- Redis or any external cache store
- Microservices split
- Distributed infrastructure

See [`DECISIONS.md`](DECISIONS.md) for the full ADR list.
