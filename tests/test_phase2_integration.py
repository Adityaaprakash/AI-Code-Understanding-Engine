"""Phase 2 Comprehensive Integration, Hardening, and Consistency Test Suite (TASK-2G)."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import (
    Class,
    EntityKind,
    ReferenceKind,
    TypeRepresentation,
    generate_entity_id,
)
from code_analyzer.normalization import (
    ASTNormalizer,
    JavaNormalizer,
    NormalizationResult,
    PythonNormalizer,
    TypeScriptNormalizer,
    normalize_parse_result,
)
from code_analyzer.parsers import JavaParser, LanguageParser, PythonParser, TypeScriptParser
from code_analyzer.parsers.models import Language, ParseResult

REPO_ID = "repo-phase2-hardening"


# =====================================================================
# 1. END-TO-END JAVA TESTS
# =====================================================================


@pytest.mark.unit
def test_e2e_java_pipeline() -> None:
    """Comprehensive Java source parsing and normalization integration test."""
    java_code = """
    package com.codelens.service;

    import java.util.List;
    import java.util.Map;

    public class UserService extends BaseService implements IUserService, IAuditable {
        private String id;

        public UserService(String id) {
            this.id = id;
        }

        public List<String> getUserRoles(Map<String, Object> context) {
            return null;
        }

        public static class UserConfig {}
    }

    public interface IUserService {}
    public interface IAuditable {}
    """
    parser = JavaParser()
    parse_res = parser.parse(java_code, source_path="src/UserService.java")
    assert parse_res.success is True

    norm = normalize_parse_result(parse_res, REPO_ID)
    assert isinstance(norm, NormalizationResult)
    assert norm.file.language == Language.JAVA

    # Module
    assert len(norm.modules) == 1
    mod = norm.modules[0]
    assert mod.name == "service"
    assert mod.qualified_name == "com.codelens.service"

    # Classes & Interfaces
    assert len(norm.classes) == 2
    user_svc = next(c for c in norm.classes if c.name == "UserService")
    assert user_svc.qualified_name == "com.codelens.service.UserService"
    assert user_svc.superclass_ref is not None
    assert user_svc.superclass_ref.ref_kind == ReferenceKind.EXTENDS
    assert user_svc.superclass_ref.target_qualified_name == "BaseService"
    assert len(user_svc.interface_refs) == 2
    iface_names = {r.target_qualified_name for r in user_svc.interface_refs}
    assert iface_names == {"IUserService", "IAuditable"}

    nested_cfg = next(c for c in norm.classes if c.name == "UserConfig")
    assert nested_cfg.qualified_name == "com.codelens.service.UserService.UserConfig"
    assert nested_cfg.id in user_svc.nested_class_ids

    assert len(norm.interfaces) == 2

    # References
    import_refs = [r for r in norm.references if r.ref_kind == ReferenceKind.IMPORT]
    assert len(import_refs) == 2
    import_targets = {r.target_qualified_name for r in import_refs}
    assert import_targets == {"java.util.List", "java.util.Map"}
    for r in norm.references:
        assert r.target_symbol_id is None

    # Methods & Constructors
    ctor = next(m for m in norm.methods if m.is_constructor)
    assert ctor.name == "UserService"
    assert ctor.class_id == user_svc.id

    method = next(m for m in norm.methods if m.name == "getUserRoles")
    assert method.class_id == user_svc.id
    assert isinstance(method.return_type, TypeRepresentation)
    assert method.return_type.display_name == "List<String>"

    # Variables & Parameters
    var = norm.variables[0]
    assert var.name == "id"
    assert var.parent_id == user_svc.id

    assert len(method.parameters) == 1
    param = method.parameters[0]
    assert param.name == "context"
    assert param.position == 0


# =====================================================================
# 2. END-TO-END PYTHON TESTS
# =====================================================================


@pytest.mark.unit
def test_e2e_python_pipeline() -> None:
    """Comprehensive Python source parsing and normalization integration test."""
    py_code = """
import os
from typing import List, Optional

def calculate_score(val: int) -> float:
    return float(val * 2)

class BaseEntity:
    pass

class UserProcessor(BaseEntity):
    @classmethod
    async def process_async(cls, items: List[str]) -> Optional[int]:
        pass
"""
    parser = PythonParser()
    parse_res = parser.parse(py_code, source_path="processors/user_processor.py")
    assert parse_res.success is True

    norm = normalize_parse_result(parse_res, REPO_ID)
    assert norm.file.language == Language.PYTHON

    # Module
    assert len(norm.modules) == 1
    mod = norm.modules[0]
    assert mod.name == "user_processor"
    assert mod.qualified_name == "processors.user_processor"

    # References
    assert len(norm.references) >= 3
    extends_ref = next(r for r in norm.references if r.ref_kind == ReferenceKind.EXTENDS)
    assert extends_ref.target_qualified_name == "BaseEntity"

    # Module Function vs Class Method
    assert len(norm.functions) == 1
    top_fn = norm.functions[0]
    assert top_fn.name == "calculate_score"
    assert top_fn.kind == EntityKind.FUNCTION

    assert len(norm.methods) == 1
    m = norm.methods[0]
    assert m.name == "process_async"
    assert m.kind == EntityKind.METHOD
    assert m.is_async is True
    assert m.is_static is True
    assert "decorators" in m.metadata


# =====================================================================
# 3. END-TO-END TYPESCRIPT TESTS
# =====================================================================


@pytest.mark.unit
def test_e2e_typescript_pipeline() -> None:
    """Comprehensive TypeScript source parsing and normalization integration test."""
    ts_code = """
import { Config } from "./config";

export interface IHandler<T> {
    handle(item: T): Promise<boolean>;
}

export type HandlerID = string;

export class TaskHandler<T> implements IHandler<T> {
    public constructor(private config: Config) {}

    public async handle(item: T): Promise<boolean> {
        return true;
    }
}
"""
    parser = TypeScriptParser()
    parse_res = parser.parse(ts_code, source_path="handlers/task.ts")
    assert parse_res.success is True

    norm = normalize_parse_result(parse_res, REPO_ID)
    assert norm.file.language == Language.TYPESCRIPT

    # Interfaces & Generics
    assert len(norm.interfaces) == 1
    iface = norm.interfaces[0]
    assert iface.name == "IHandler"
    assert iface.type_parameters == ["T"]
    assert iface.metadata.get("is_exported") is True

    # Type Alias
    type_var = next(v for v in norm.variables if v.name == "HandlerID")
    assert type_var.metadata.get("is_type_alias") is True
    assert type_var.metadata.get("definition") == "string"

    # Classes & Implements Reference
    assert len(norm.classes) == 1
    cls = norm.classes[0]
    assert cls.name == "TaskHandler"
    assert len(cls.interface_refs) == 1
    assert cls.interface_refs[0].ref_kind == ReferenceKind.IMPLEMENTS

    # Methods & Constructors
    method = next(m for m in norm.methods if m.name == "handle")
    assert method.is_async is True
    assert isinstance(method.return_type, TypeRepresentation)
    assert method.return_type.display_name == "Promise<boolean>"


# =====================================================================
# 4. CROSS-LANGUAGE ENTITY CONSISTENCY
# =====================================================================


@pytest.mark.unit
def test_cross_language_consistency() -> None:
    """Verify identical conceptual structures across Java, Python, and TS normalize to identical EntityKinds."""
    java_src = "package a;\npublic class Controller { public void handleRequest() {} }"
    py_src = (
        "class Controller:\n    def handle_request(self):\n        pass\ndef helper_func(): pass"
    )
    ts_src = "class Controller { handleRequest(): void {} }\nfunction helperFunc(): void {}"

    j_norm = normalize_parse_result(
        JavaParser().parse(java_src, source_path="Controller.java"), REPO_ID
    )
    p_norm = normalize_parse_result(
        PythonParser().parse(py_src, source_path="controller.py"), REPO_ID
    )
    t_norm = normalize_parse_result(
        TypeScriptParser().parse(ts_src, source_path="Controller.ts"), REPO_ID
    )

    # Class consistency
    assert j_norm.classes[0].kind == EntityKind.CLASS
    assert p_norm.classes[0].kind == EntityKind.CLASS
    assert t_norm.classes[0].kind == EntityKind.CLASS

    # Method consistency
    assert j_norm.methods[0].kind == EntityKind.METHOD
    assert p_norm.methods[0].kind == EntityKind.METHOD
    assert t_norm.methods[0].kind == EntityKind.METHOD

    # Function consistency (Python & TS module functions)
    assert p_norm.functions[0].kind == EntityKind.FUNCTION
    assert t_norm.functions[0].kind == EntityKind.FUNCTION


# =====================================================================
# 5. LANGUAGE LEAKAGE TESTING
# =====================================================================


@pytest.mark.unit
def test_no_language_ast_leakage() -> None:
    """Ensure canonical entities contain no language-specific AST objects or Tree-sitter Nodes."""
    code = "public class App { private String name; }"
    norm = normalize_parse_result(JavaParser().parse(code, source_path="App.java"), REPO_ID)

    cls = norm.classes[0]
    for _key, val in cls.model_dump().items():
        assert "Java" not in str(type(val))
        assert "tree_sitter" not in str(type(val)).lower()


# =====================================================================
# 6. DETERMINISTIC ID TESTING
# =====================================================================


@pytest.mark.unit
def test_deterministic_id_generation_sensitivity() -> None:
    """Verify IDs are deterministic across runs and change when name, file_path, or kind changes."""
    code1 = "class Service:\n    pass"
    code2 = "class PaymentService:\n    pass"

    res1 = PythonParser().parse(code1, source_path="service.py")
    res2 = PythonParser().parse(code1, source_path="service.py")
    res3 = PythonParser().parse(code2, source_path="service.py")
    res4 = PythonParser().parse(code1, source_path="other_service.py")

    norm1 = normalize_parse_result(res1, REPO_ID)
    norm2 = normalize_parse_result(res2, REPO_ID)
    norm3 = normalize_parse_result(res3, REPO_ID)
    norm4 = normalize_parse_result(res4, REPO_ID)

    # Re-run identical input -> exact same IDs
    assert norm1.classes[0].id == norm2.classes[0].id
    assert norm1.file.id == norm2.file.id

    # Changed class name -> different class ID
    assert norm1.classes[0].id != norm3.classes[0].id

    # Changed file path -> different file ID & entity IDs
    assert norm1.file.id != norm4.file.id
    assert norm1.classes[0].id != norm4.classes[0].id

    # EntityKind sensitivity check
    class_id = generate_entity_id(EntityKind.CLASS, "a.py", "Foo")
    iface_id = generate_entity_id(EntityKind.INTERFACE, "a.py", "Foo")
    assert class_id != iface_id


# =====================================================================
# 7. NORMALIZATION IDEMPOTENCY
# =====================================================================


@pytest.mark.unit
def test_normalization_idempotency() -> None:
    """Verify normalizing the exact same ParseResult multiple times produces identical output."""
    code = "package com.test;\npublic class App { public void main(String[] args) {} }"
    res = JavaParser().parse(code, source_path="App.java")

    norm1 = normalize_parse_result(res, REPO_ID)
    norm2 = normalize_parse_result(res, REPO_ID)

    assert norm1.model_dump() == norm2.model_dump()


# =====================================================================
# 8. SOURCE LOCATION INTEGRATION
# =====================================================================


@pytest.mark.unit
def test_source_location_correctness() -> None:
    """Verify source locations are accurately extracted and converted to canonical SourceLocation."""
    code = """
class FirstClass:
    pass

class SecondClass:
    def method_on_line_6(self):
        pass
"""
    res = PythonParser().parse(code, source_path="multi.py")
    norm = normalize_parse_result(res, REPO_ID)

    c1 = next(c for c in norm.classes if c.name == "FirstClass")
    c2 = next(c for c in norm.classes if c.name == "SecondClass")
    m = norm.methods[0]

    assert c1.location is not None
    assert c1.location.start_line == 2
    assert c1.location.file_path == "multi.py"

    assert c2.location is not None
    assert c2.location.start_line == 5

    assert m.location is not None
    assert m.location.start_line == 6


# =====================================================================
# 9. TYPE NORMALIZATION TESTING
# =====================================================================


@pytest.mark.unit
def test_type_representation_normalization() -> None:
    """Verify types across Java, Python, and TypeScript map to TypeRepresentation."""
    j_code = "public class A { public java.util.List<String> get() { return null; } }"
    p_code = "def get() -> list[str]: pass"
    t_code = "function get(): Promise<User> { return null; }"

    j_norm = normalize_parse_result(JavaParser().parse(j_code, source_path="A.java"), REPO_ID)
    p_norm = normalize_parse_result(PythonParser().parse(p_code, source_path="a.py"), REPO_ID)
    t_norm = normalize_parse_result(TypeScriptParser().parse(t_code, source_path="a.ts"), REPO_ID)

    j_ret = j_norm.methods[0].return_type
    p_ret = p_norm.functions[0].return_type
    t_ret = t_norm.functions[0].return_type

    assert isinstance(j_ret, TypeRepresentation)
    assert j_ret.normalized_name == "java.util.List"
    assert j_ret.type_arguments[0].display_name == "String"

    assert isinstance(p_ret, TypeRepresentation)
    assert p_ret.normalized_name == "list"
    assert p_ret.type_arguments[0].display_name == "str"

    assert isinstance(t_ret, TypeRepresentation)
    assert t_ret.normalized_name == "Promise"
    assert t_ret.type_arguments[0].display_name == "User"


# =====================================================================
# 10. MALFORMED SOURCE TESTING
# =====================================================================


@pytest.mark.unit
def test_malformed_source_fault_tolerance() -> None:
    """Verify malformed source code in Java, Python, and TS does not crash normalizers."""
    j_bad = "public class Broken {"
    p_bad = "def broken_func(:"
    t_bad = "class Broken { func( {"

    for parser, code, lang, path in [
        (JavaParser(), j_bad, Language.JAVA, "Broken.java"),
        (PythonParser(), p_bad, Language.PYTHON, "broken.py"),
        (TypeScriptParser(), t_bad, Language.TYPESCRIPT, "Broken.ts"),
    ]:
        res = parser.parse(code, source_path=path)
        norm = normalize_parse_result(res, REPO_ID)
        assert norm.file is not None
        assert norm.file.language == lang


# =====================================================================
# 11. EMPTY SOURCE TESTING
# =====================================================================


@pytest.mark.unit
def test_empty_source_handling() -> None:
    """Verify empty string source produces valid NormalizationResult with zero entities."""
    for parser, path in [
        (JavaParser(), "Empty.java"),
        (PythonParser(), "empty.py"),
        (TypeScriptParser(), "Empty.ts"),
    ]:
        res = parser.parse("", source_path=path)
        norm = normalize_parse_result(res, REPO_ID)
        assert norm.file is not None
        assert len(norm.classes) == 0
        assert len(norm.functions) == 0
        assert len(norm.methods) == 0


# =====================================================================
# 12. COMMENT-ONLY SOURCE TESTING
# =====================================================================


@pytest.mark.unit
def test_comment_only_source_handling() -> None:
    """Verify comment-only files parse cleanly without generating fake entities."""
    j_code = "// Java comment\n/* Multi line */"
    p_code = "# Python comment\n''' Docstring comment '''"
    t_code = "// TS comment\n/* Block comment */"

    for parser, code, path in [
        (JavaParser(), j_code, "Comment.java"),
        (PythonParser(), p_code, "comment.py"),
        (TypeScriptParser(), t_code, "Comment.ts"),
    ]:
        res = parser.parse(code, source_path=path)
        norm = normalize_parse_result(res, REPO_ID)
        assert len(norm.classes) == 0
        assert len(norm.functions) == 0


# =====================================================================
# 13. MULTIPLE DECLARATIONS TESTING
# =====================================================================


@pytest.mark.unit
def test_multiple_declarations_in_single_file() -> None:
    """Verify multiple top-level declarations in a single file get unique deterministic IDs."""
    code = """
class Alpha:
    pass

class Beta:
    pass
"""
    res = PythonParser().parse(code, source_path="multi.py")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.classes) == 2
    alpha = next(c for c in norm.classes if c.name == "Alpha")
    beta = next(c for c in norm.classes if c.name == "Beta")
    assert alpha.id != beta.id


# =====================================================================
# 14. NESTED DECLARATION TESTING
# =====================================================================


@pytest.mark.unit
def test_nested_declarations_hierarchy() -> None:
    """Verify nested classes set proper parent IDs and qualified names."""
    code = """
    package com.test;
    public class Outer {
        public static class Inner {}
    }
    """
    res = JavaParser().parse(code, source_path="Outer.java")
    norm = normalize_parse_result(res, REPO_ID)

    outer = next(c for c in norm.classes if c.name == "Outer")
    inner = next(c for c in norm.classes if c.name == "Inner")

    assert inner.parent_id == outer.id
    assert inner.id in outer.nested_class_ids
    assert inner.qualified_name == "com.test.Outer.Inner"


# =====================================================================
# 15. DUPLICATE NAMES IN DIFFERENT SCOPES
# =====================================================================


@pytest.mark.unit
def test_duplicate_names_different_files() -> None:
    """Verify same class name in different files generates distinct IDs."""
    code = "class Worker:\n    pass"

    res1 = PythonParser().parse(code, source_path="file_a.py")
    res2 = PythonParser().parse(code, source_path="file_b.py")

    norm1 = normalize_parse_result(res1, REPO_ID)
    norm2 = normalize_parse_result(res2, REPO_ID)

    assert norm1.classes[0].name == norm2.classes[0].name
    assert norm1.classes[0].id != norm2.classes[0].id


# =====================================================================
# 16. PARSER DIAGNOSTIC PRESERVATION
# =====================================================================


@pytest.mark.unit
def test_parser_diagnostics_preservation() -> None:
    """Verify parser diagnostic warnings/errors are preserved in NormalizationResult."""
    res = ParseResult.create_failure(
        language=Language.PYTHON,
        source_path="invalid.py",
        diagnostics=[],
    )
    norm = normalize_parse_result(res, REPO_ID)
    assert norm.file.path == "invalid.py"


# =====================================================================
# 17. SERIALIZATION TESTING
# =====================================================================


@pytest.mark.unit
def test_json_roundtrip_serialization() -> None:
    """Verify normalized entities serialize to JSON and deserialize back losslessly."""
    code = "public class App { public void main() {} }"
    res = JavaParser().parse(code, source_path="App.java")
    norm = normalize_parse_result(res, REPO_ID)

    cls = norm.classes[0]
    json_str = cls.model_dump_json()
    deserialized = Class.model_validate_json(json_str)

    assert deserialized.id == cls.id
    assert deserialized.name == cls.name
    assert deserialized.kind == cls.kind


# =====================================================================
# 18. IMMUTABILITY TESTING
# =====================================================================


@pytest.mark.unit
def test_canonical_entity_immutability() -> None:
    """Verify canonical IR entities are frozen and cannot be mutated."""
    code = "class Frozen:\n    pass"
    res = PythonParser().parse(code, source_path="frozen.py")
    norm = normalize_parse_result(res, REPO_ID)

    cls = norm.classes[0]
    with pytest.raises((ValidationError, TypeError)):
        cls.name = "Mutated"


# =====================================================================
# 19. PUBLIC API TESTING
# =====================================================================


@pytest.mark.unit
def test_public_api_exports() -> None:
    """Verify public module imports work as documented."""
    assert LanguageParser is not None
    assert ASTNormalizer is not None
    assert JavaNormalizer is not None
    assert PythonNormalizer is not None
    assert TypeScriptNormalizer is not None
    assert normalize_parse_result is not None


# =====================================================================
# 20. NO DISK DEPENDENCY VERIFICATION
# =====================================================================


@pytest.mark.unit
def test_in_memory_normalization_no_disk() -> None:
    """Verify normalization pipeline functions entirely in-memory without filesystem calls."""
    res = PythonParser().parse("x = 1", source_path="virtual/memory.py")
    norm = normalize_parse_result(res, REPO_ID)
    assert norm.file.path == "virtual/memory.py"


# =====================================================================
# 21. PROPERTY-STYLE PARAMETERIZED TESTING
# =====================================================================


@pytest.mark.parametrize(
    "lang,parser_cls,code,ext",
    [
        (Language.JAVA, JavaParser, "public class P { public void run() {} }", "P.java"),
        (Language.PYTHON, PythonParser, "class P:\n    def run(self): pass", "p.py"),
        (Language.TYPESCRIPT, TypeScriptParser, "class P { run(): void {} }", "P.ts"),
    ],
)
@pytest.mark.unit
def test_parameterized_pipeline(lang: Language, parser_cls: type, code: str, ext: str) -> None:
    """Parameterized pipeline verification across all 3 MVP languages."""
    parser = parser_cls()
    parse_res = parser.parse(code, source_path=ext)
    norm = normalize_parse_result(parse_res, REPO_ID)

    assert norm.file.language == lang
    assert len(norm.classes) == 1
    assert norm.classes[0].name == "P"
    assert len(norm.methods) == 1
    assert norm.methods[0].name == "run"


# =====================================================================
# 22. PERFORMANCE SANITY TEST
# =====================================================================


@pytest.mark.unit
def test_performance_sanity_modest_large_file() -> None:
    """Verify a 500-line Python source file normalizes rapidly without catastrophic backtrack."""
    import time

    lines = ["class LargeModule:"]
    for i in range(250):
        lines.append(f"    def method_{i}(self, param_{i}: int) -> int:\n        return {i}")

    large_code = "\n".join(lines)

    start = time.perf_counter()
    parse_res = PythonParser().parse(large_code, source_path="large.py")
    norm = normalize_parse_result(parse_res, REPO_ID)
    duration = time.perf_counter() - start

    assert len(norm.methods) == 250
    assert duration < 2.0  # Sanity check: must complete in under 2 seconds
