# Canonical Code IR — AI Code Understanding Engine

> **Status:** Contract defined. Implementation deferred to Phase 3.
>
> This document is the source of truth for the Canonical Code IR.
> Any change to the IR must go through an ADR update (see `DECISIONS.md`).

---

## Purpose

The Canonical Code IR (Intermediate Representation) is a language-agnostic,
structured representation of a parsed source file. It is produced by the
`code-analyzer/` module from tree-sitter ASTs and consumed by:

- The **symbol graph builder** (`graph/`) — reads relationships to build edges
- The **chunker** — splits the IR into retrievable text chunks
- The **retrieval engine** — uses symbol metadata for query matching

---

## Design Principles

1. **Language-agnostic** — IR concepts map to all three MVP languages
   (Java, Python, TypeScript) without language-specific fields.
2. **Hierarchical** — IR nodes form a tree:
   `Repository → File → Module → (Class | Interface) → (Method | Function | Variable)`
3. **Reference-complete** — every cross-file reference is captured as a
   `Reference` node with both a source and a resolved target symbol.
4. **Immutable per parse** — the IR for a file is fully rebuilt on each
   re-index of that file; incremental patching happens at the database level.

---

## Concepts

### Repository

The root of the IR tree. Represents a single indexed repository.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier (matches `repositories.id` in DB) |
| `name` | string | Human-readable repository name |
| `root_path` | string | Absolute local path of the checkout |
| `language_breakdown` | map[language → int] | LOC per language |
| `files` | File[] | All parsed source files |

---

### File

Represents a single source file in the repository.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier |
| `repository_id` | UUID | Parent repository |
| `relative_path` | string | Path relative to repository root |
| `language` | enum | `java` \| `python` \| `typescript` |
| `content_hash` | string | SHA-256 of file contents (for incremental diffing) |
| `loc` | int | Lines of code (non-blank, non-comment) |
| `modules` | Module[] | Top-level modules declared in this file |
| `symbols` | Symbol[] | All symbols declared directly in this file |
| `references` | Reference[] | All outbound references from this file |

---

### Module

Represents a module-level namespace. In Python this is the file itself.
In Java it is a package declaration. In TypeScript it is an ES module.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier |
| `file_id` | UUID | Parent file |
| `qualified_name` | string | Fully-qualified module name |
| `exported_symbols` | Symbol[] | Symbols visible to importers |

---

### Class

A class declaration.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier (also a Symbol) |
| `module_id` | UUID | Parent module |
| `name` | string | Simple name |
| `qualified_name` | string | Fully-qualified name |
| `start_line` | int | First line of the declaration |
| `end_line` | int | Last line of the declaration |
| `doc_comment` | string? | Extracted doc comment |
| `superclass` | Reference? | Reference to parent class |
| `interfaces` | Reference[] | Implemented interfaces |
| `methods` | Method[] | Methods declared in this class |
| `fields` | Variable[] | Fields/properties declared in this class |
| `is_abstract` | bool | Whether the class is abstract |
| `visibility` | enum | `public` \| `protected` \| `private` \| `package` \| `internal` |

---

### Interface

An interface or abstract type declaration (Java `interface`, TypeScript `interface`,
Python `Protocol`).

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier (also a Symbol) |
| `module_id` | UUID | Parent module |
| `name` | string | Simple name |
| `qualified_name` | string | Fully-qualified name |
| `start_line` | int | |
| `end_line` | int | |
| `doc_comment` | string? | |
| `extends` | Reference[] | Parent interfaces |
| `methods` | Method[] | Method signatures |
| `visibility` | enum | |

---

### Function

A standalone function (not a class method). Common in Python and TypeScript.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier (also a Symbol) |
| `module_id` | UUID | Parent module |
| `name` | string | |
| `qualified_name` | string | |
| `start_line` | int | |
| `end_line` | int | |
| `doc_comment` | string? | |
| `parameters` | Parameter[] | Ordered list of parameters |
| `return_type` | string? | Declared return type (as string) |
| `is_async` | bool | |
| `visibility` | enum | |
| `calls` | Reference[] | References to callees within function body |

---

### Method

A function declared within a Class or Interface.
Identical structure to Function with an additional `class_id` field.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | |
| `class_id` | UUID | Parent class or interface |
| `name` | string | |
| `qualified_name` | string | `com.example.MyClass.myMethod` |
| `start_line` | int | |
| `end_line` | int | |
| `doc_comment` | string? | |
| `parameters` | Parameter[] | |
| `return_type` | string? | |
| `is_async` | bool | |
| `is_static` | bool | |
| `is_abstract` | bool | |
| `overrides` | Reference? | Reference to overridden method |
| `visibility` | enum | |
| `calls` | Reference[] | |

---

### Variable

A variable, constant, field, or property declaration.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier (also a Symbol) |
| `parent_id` | UUID | Parent (module, class, function, or method) |
| `name` | string | |
| `qualified_name` | string | |
| `declared_type` | string? | Declared type annotation |
| `start_line` | int | |
| `is_constant` | bool | `final`, `const`, `val` |
| `visibility` | enum | |

---

### Parameter

A formal parameter of a function or method. Embedded within Function/Method;
not stored as an independent symbol unless explicitly referenced.

| Field | Type | Description |
|---|---|---|
| `name` | string | |
| `declared_type` | string? | |
| `default_value` | string? | Literal default (as string) |
| `position` | int | 0-indexed position |

---

### Reference

A use-site reference from one symbol to another. References are the edges
of the symbol graph.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | |
| `source_symbol_id` | UUID | Symbol that contains this reference |
| `source_file_id` | UUID | File containing the reference |
| `source_line` | int | Line of the reference |
| `target_qualified_name` | string | Fully-qualified name of the referenced symbol |
| `target_symbol_id` | UUID? | Resolved target (null if unresolved) |
| `kind` | enum | `call` \| `import` \| `extends` \| `implements` \| `type_use` \| `field_access` \| `override` |

---

### Symbol

A unified concept representing any named, addressable entity in the codebase.
Classes, interfaces, functions, methods, and variables are all Symbols.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | |
| `qualified_name` | string | The globally unique name |
| `kind` | enum | `class` \| `interface` \| `function` \| `method` \| `variable` \| `parameter` |
| `language` | enum | `java` \| `python` \| `typescript` |
| `file_id` | UUID | File where this symbol is declared |
| `start_line` | int | |
| `end_line` | int | |
| `doc_comment` | string? | |
| `embedding_id` | UUID? | FK to vector embeddings table (set after indexing) |

---

### Relationship

An indexed edge in the symbol graph, derived from Reference nodes.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | |
| `source_symbol_id` | UUID | |
| `target_symbol_id` | UUID | |
| `kind` | enum | Same as Reference.kind |
| `repository_id` | UUID | |

---

## Serialisation

The IR is an in-memory Python data structure during parsing. It is persisted
to PostgreSQL via the `IRWriter` (to be implemented in Phase 3). It is
**not** serialised to disk as JSON or protobuf in MVP.

---

## Future Extensions (not in MVP)

- Generic type parameters
- Decorator / annotation metadata
- Control-flow graph within functions
- Data-flow graph (variable assignment chains)
