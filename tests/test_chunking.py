"""Comprehensive unit and integration test suite for AST/IR-aware CodeChunker."""

import time

import pytest

from code_analyzer.ir import (
    Class,
    File,
    Function,
    Interface,
    Method,
    Parameter,
    SourceLocation,
)
from code_analyzer.normalization import NormalizationResult, normalize_parse_result
from code_analyzer.parsers import JavaParser, Language, PythonParser, TypeScriptParser
from retrieval import (
    ChunkType,
    CodeChunker,
    generate_chunk_id,
)


@pytest.fixture
def chunker() -> CodeChunker:
    """Fixture providing a fresh CodeChunker instance."""
    return CodeChunker()


# ──────────────────────────────────────────────────────────────────────────────
# 1. Empty File
# ──────────────────────────────────────────────────────────────────────────────
def test_empty_file(chunker: CodeChunker) -> None:
    file_entity = File(
        id="file_empty",
        repository_id="repo_1",
        path="empty.py",
        language=Language.PYTHON,
        loc=0,
    )
    result = NormalizationResult(file=file_entity)

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 1
    assert collection.chunks[0].chunk_type == ChunkType.FILE_CONTEXT
    assert collection.chunks[0].file_path == "empty.py"


# ──────────────────────────────────────────────────────────────────────────────
# 2. File Context
# ──────────────────────────────────────────────────────────────────────────────
def test_file_context(chunker: CodeChunker) -> None:
    file_entity = File(
        id="file_ctx",
        repository_id="repo_1",
        path="service.py",
        language=Language.PYTHON,
        loc=50,
        doc_comment="Module header docstring",
    )
    result = NormalizationResult(file=file_entity)
    code = "# service.py\nimport os\nimport sys\n\n# Main logic"

    collection = chunker.chunk_normalization_result(result, source_code=code)
    assert len(collection) == 1
    chunk = collection.chunks[0]
    assert chunk.chunk_type == ChunkType.FILE_CONTEXT
    assert chunk.name == "service.py"
    assert chunk.doc_comment == "Module header docstring"
    assert "import os" in chunk.content


# ──────────────────────────────────────────────────────────────────────────────
# 3. Single Function
# ──────────────────────────────────────────────────────────────────────────────
def test_single_function(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f1", repository_id="repo_1", path="math_utils.py", language=Language.PYTHON, loc=10
    )
    func_entity = Function(
        id="func_add",
        file_id="f1",
        name="add",
        qualified_name="math_utils.add",
        parent_id="f1",
        parameters=[
            Parameter(id="p1", name="a", position=0, declared_type="int"),
            Parameter(id="p2", name="b", position=1, declared_type="int"),
        ],
        return_type="int",
        location=SourceLocation(
            file_path="math_utils.py", start_line=3, start_column=0, end_line=5, end_column=15
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[func_entity])
    code = "# utils\n\ndef add(a: int, b: int) -> int:\n    return a + b\n"

    collection = chunker.chunk_normalization_result(result, source_code=code)
    assert len(collection) == 2
    func_chunk = collection.get_chunks_for_entity("func_add")[0]
    assert func_chunk.chunk_type == ChunkType.FUNCTION
    assert func_chunk.name == "add"
    assert func_chunk.parent_entity_id == "f1"
    assert "def add(a: int, b: int) -> int:" in func_chunk.content


# ──────────────────────────────────────────────────────────────────────────────
# 4. Multiple Functions
# ──────────────────────────────────────────────────────────────────────────────
def test_multiple_functions(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_multi", repository_id="repo_1", path="helpers.py", language=Language.PYTHON, loc=20
    )
    fn1 = Function(
        id="fn1",
        file_id="f_multi",
        name="first",
        qualified_name="helpers.first",
        parent_id="f_multi",
        location=SourceLocation(
            file_path="helpers.py", start_line=2, start_column=0, end_line=3, end_column=10
        ),
    )
    fn2 = Function(
        id="fn2",
        file_id="f_multi",
        name="second",
        qualified_name="helpers.second",
        parent_id="f_multi",
        location=SourceLocation(
            file_path="helpers.py", start_line=5, start_column=0, end_line=6, end_column=10
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn1, fn2])

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 3
    fn_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.FUNCTION]
    assert len(fn_chunks) == 2
    assert [c.name for c in fn_chunks] == ["first", "second"]


# ──────────────────────────────────────────────────────────────────────────────
# 5. Class
# ──────────────────────────────────────────────────────────────────────────────
def test_class(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_cls", repository_id="repo_1", path="user.py", language=Language.PYTHON, loc=30
    )
    cls_entity = Class(
        id="cls_user",
        file_id="f_cls",
        name="User",
        qualified_name="user.User",
        parent_id="f_cls",
        doc_comment="User model representation",
        location=SourceLocation(
            file_path="user.py", start_line=5, start_column=0, end_line=25, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, classes=[cls_entity])

    collection = chunker.chunk_normalization_result(result)
    cls_chunks = collection.get_chunks_for_entity("cls_user")
    assert len(cls_chunks) == 1
    assert cls_chunks[0].chunk_type == ChunkType.CLASS_CONTEXT
    assert cls_chunks[0].doc_comment == "User model representation"


# ──────────────────────────────────────────────────────────────────────────────
# 6. Multiple Methods
# ──────────────────────────────────────────────────────────────────────────────
def test_multiple_methods(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_svc", repository_id="repo_1", path="payment.py", language=Language.PYTHON, loc=50
    )
    cls_entity = Class(
        id="cls_pay",
        file_id="f_svc",
        name="PaymentService",
        qualified_name="payment.PaymentService",
        method_ids=["m1", "m2"],
        location=SourceLocation(
            file_path="payment.py", start_line=5, start_column=0, end_line=45, end_column=0
        ),
    )
    m1 = Method(
        id="m1",
        file_id="f_svc",
        class_id="cls_pay",
        name="process_payment",
        qualified_name="payment.PaymentService.process_payment",
        location=SourceLocation(
            file_path="payment.py", start_line=10, start_column=4, end_line=20, end_column=15
        ),
    )
    m2 = Method(
        id="m2",
        file_id="f_svc",
        class_id="cls_pay",
        name="refund_payment",
        qualified_name="payment.PaymentService.refund_payment",
        location=SourceLocation(
            file_path="payment.py", start_line=22, start_column=4, end_line=35, end_column=15
        ),
    )
    result = NormalizationResult(file=file_entity, classes=[cls_entity], methods=[m1, m2])

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 4
    m1_chunks = collection.get_chunks_for_entity("m1")
    m2_chunks = collection.get_chunks_for_entity("m2")
    assert len(m1_chunks) == 1
    assert len(m2_chunks) == 1
    assert m1_chunks[0].parent_entity_id == "cls_pay"
    assert m2_chunks[0].parent_entity_id == "cls_pay"


# ──────────────────────────────────────────────────────────────────────────────
# 7. Interface
# ──────────────────────────────────────────────────────────────────────────────
def test_interface(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_iface",
        repository_id="repo_1",
        path="gateway.ts",
        language=Language.TYPESCRIPT,
        loc=15,
    )
    iface = Interface(
        id="iface_gw",
        file_id="f_iface",
        name="PaymentGateway",
        qualified_name="gateway.PaymentGateway",
        location=SourceLocation(
            file_path="gateway.ts", start_line=3, start_column=0, end_line=10, end_column=1
        ),
    )
    result = NormalizationResult(file=file_entity, interfaces=[iface])

    collection = chunker.chunk_normalization_result(result)
    iface_chunks = collection.get_chunks_for_entity("iface_gw")
    assert len(iface_chunks) == 1
    assert iface_chunks[0].chunk_type == ChunkType.INTERFACE_CONTEXT
    assert iface_chunks[0].name == "PaymentGateway"


# ──────────────────────────────────────────────────────────────────────────────
# 8. Nested Entities
# ──────────────────────────────────────────────────────────────────────────────
def test_nested_entities(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_nest", repository_id="repo_1", path="Outer.java", language=Language.JAVA, loc=40
    )
    outer_cls = Class(
        id="cls_outer",
        file_id="f_nest",
        name="Outer",
        qualified_name="com.example.Outer",
        parent_id="f_nest",
        nested_class_ids=["cls_inner"],
        location=SourceLocation(
            file_path="Outer.java", start_line=3, start_column=0, end_line=35, end_column=1
        ),
    )
    inner_cls = Class(
        id="cls_inner",
        file_id="f_nest",
        name="Inner",
        qualified_name="com.example.Outer.Inner",
        parent_id="cls_outer",
        method_ids=["m_inner"],
        location=SourceLocation(
            file_path="Outer.java", start_line=10, start_column=4, end_line=25, end_column=5
        ),
    )
    inner_method = Method(
        id="m_inner",
        file_id="f_nest",
        class_id="cls_inner",
        name="innerMethod",
        qualified_name="com.example.Outer.Inner.innerMethod",
        location=SourceLocation(
            file_path="Outer.java", start_line=15, start_column=8, end_line=20, end_column=9
        ),
    )
    result = NormalizationResult(
        file=file_entity, classes=[outer_cls, inner_cls], methods=[inner_method]
    )

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 4
    inner_cls_chunk = collection.get_chunks_for_entity("cls_inner")[0]
    assert inner_cls_chunk.parent_entity_id == "cls_outer"
    inner_m_chunk = collection.get_chunks_for_entity("m_inner")[0]
    assert inner_m_chunk.parent_entity_id == "cls_inner"


# ──────────────────────────────────────────────────────────────────────────────
# 9. Parent-Child Relationship
# ──────────────────────────────────────────────────────────────────────────────
def test_parent_child_relationship(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_pc", repository_id="repo_1", path="test.py", language=Language.PYTHON, loc=20
    )
    cls_entity = Class(
        id="c1",
        file_id="f_pc",
        name="Foo",
        qualified_name="test.Foo",
        parent_id="f_pc",
        location=SourceLocation(
            file_path="test.py", start_line=2, start_column=0, end_line=15, end_column=0
        ),
    )
    method_entity = Method(
        id="m1",
        file_id="f_pc",
        class_id="c1",
        name="bar",
        qualified_name="test.Foo.bar",
        location=SourceLocation(
            file_path="test.py", start_line=5, start_column=4, end_line=10, end_column=10
        ),
    )
    result = NormalizationResult(file=file_entity, classes=[cls_entity], methods=[method_entity])

    collection = chunker.chunk_normalization_result(result)
    m_chunk = collection.get_chunks_for_entity("m1")[0]
    assert m_chunk.parent_entity_id == "c1"


# ──────────────────────────────────────────────────────────────────────────────
# 10. Source Ranges
# ──────────────────────────────────────────────────────────────────────────────
def test_source_ranges(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_sr", repository_id="repo_1", path="test.py", language=Language.PYTHON, loc=30
    )
    func_entity = Function(
        id="fn_sr",
        file_id="f_sr",
        name="do_work",
        qualified_name="test.do_work",
        location=SourceLocation(
            file_path="test.py", start_line=12, start_column=4, end_line=28, end_column=18
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[func_entity])

    collection = chunker.chunk_normalization_result(result)
    fn_chunk = collection.get_chunks_for_entity("fn_sr")[0]
    assert fn_chunk.source_location.start_line == 12
    assert fn_chunk.source_location.start_column == 4
    assert fn_chunk.source_location.end_line == 28
    assert fn_chunk.source_location.end_column == 18


# ──────────────────────────────────────────────────────────────────────────────
# 11. Source Ordering
# ──────────────────────────────────────────────────────────────────────────────
def test_source_ordering(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_ord", repository_id="repo_1", path="ordered.py", language=Language.PYTHON, loc=50
    )
    fn2 = Function(
        id="fn2",
        file_id="f_ord",
        name="second",
        qualified_name="ordered.second",
        location=SourceLocation(
            file_path="ordered.py", start_line=20, start_column=0, end_line=25, end_column=0
        ),
    )
    fn1 = Function(
        id="fn1",
        file_id="f_ord",
        name="first",
        qualified_name="ordered.first",
        location=SourceLocation(
            file_path="ordered.py", start_line=5, start_column=0, end_line=10, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn2, fn1])

    collection = chunker.chunk_normalization_result(result)
    non_file_chunks = [c for c in collection.chunks if c.chunk_type != ChunkType.FILE_CONTEXT]
    assert [c.name for c in non_file_chunks] == ["first", "second"]


# ──────────────────────────────────────────────────────────────────────────────
# 12. Duplicate Prevention
# ──────────────────────────────────────────────────────────────────────────────
def test_duplicate_prevention(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_dup", repository_id="repo_1", path="dup.py", language=Language.PYTHON, loc=20
    )
    fn1 = Function(
        id="fn1",
        file_id="f_dup",
        name="foo",
        qualified_name="dup.foo",
        location=SourceLocation(
            file_path="dup.py", start_line=2, start_column=0, end_line=5, end_column=0
        ),
    )
    # Duplicate function entity in IR
    result = NormalizationResult(file=file_entity, functions=[fn1, fn1])

    collection = chunker.chunk_normalization_result(result)
    fn_chunks = collection.get_chunks_for_entity("fn1")
    assert len(fn_chunks) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 13. Deterministic Repeated Runs
# ──────────────────────────────────────────────────────────────────────────────
def test_deterministic_repeated_runs(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_det", repository_id="repo_1", path="det.py", language=Language.PYTHON, loc=30
    )
    fn1 = Function(
        id="fn1",
        file_id="f_det",
        name="foo",
        qualified_name="det.foo",
        location=SourceLocation(
            file_path="det.py", start_line=2, start_column=0, end_line=10, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn1])

    c1 = chunker.chunk_normalization_result(result)
    c2 = chunker.chunk_normalization_result(result)

    assert len(c1) == len(c2)
    assert [c.id for c in c1.chunks] == [c.id for c in c2.chunks]
    assert [c.content for c in c1.chunks] == [c.content for c in c2.chunks]


# ──────────────────────────────────────────────────────────────────────────────
# 14. Deterministic Chunk IDs
# ──────────────────────────────────────────────────────────────────────────────
def test_deterministic_chunk_ids() -> None:
    id1 = generate_chunk_id("repo1", "app.py", ChunkType.FUNCTION, entity_id="ent1")
    id2 = generate_chunk_id("repo1", "app.py", ChunkType.FUNCTION, entity_id="ent1")
    id3 = generate_chunk_id("repo1", "app.py", ChunkType.FUNCTION, entity_id="ent2")

    assert id1 == id2
    assert id1 != id3


# ──────────────────────────────────────────────────────────────────────────────
# 15. Java Test Fixture
# ──────────────────────────────────────────────────────────────────────────────
def test_java_fixture(chunker: CodeChunker) -> None:
    java_code = """
package com.example.payment;

import com.example.gateway.PaymentGateway;

/**
 * Service handling payments.
 */
public class PaymentService {
    private final PaymentGateway gateway;

    public PaymentService(PaymentGateway gateway) {
        this.gateway = gateway;
    }

    public boolean processPayment(double amount) {
        return gateway.charge(amount);
    }
}
"""
    parser = JavaParser()
    parse_res = parser.parse(java_code, source_path="com/example/payment/PaymentService.java")
    norm_res = normalize_parse_result(parse_res, repository_id="repo_java")

    collection = chunker.chunk_normalization_result(norm_res, source_code=java_code)
    assert len(collection) >= 3

    class_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.CLASS_CONTEXT]
    assert len(class_chunks) == 1
    assert class_chunks[0].name == "PaymentService"

    method_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.METHOD]
    assert len(method_chunks) >= 1
    method_names = [m.name for m in method_chunks]
    assert "processPayment" in method_names


# ──────────────────────────────────────────────────────────────────────────────
# 16. Python Test Fixture
# ──────────────────────────────────────────────────────────────────────────────
def test_python_fixture(chunker: CodeChunker) -> None:
    py_code = """
from typing import Optional

def top_level_helper(x: int) -> int:
    return x * 2

class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        return a + b
"""
    parser = PythonParser()
    parse_res = parser.parse(py_code, source_path="calc.py")
    norm_res = normalize_parse_result(parse_res, repository_id="repo_py")

    collection = chunker.chunk_normalization_result(norm_res, source_code=py_code)

    file_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.FILE_CONTEXT]
    func_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.FUNCTION]
    cls_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.CLASS_CONTEXT]
    method_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.METHOD]

    assert len(file_chunks) == 1
    assert len(func_chunks) == 1
    assert func_chunks[0].name == "top_level_helper"
    assert len(cls_chunks) == 1
    assert cls_chunks[0].name == "Calculator"
    assert len(method_chunks) == 1
    assert method_chunks[0].name == "add"


# ──────────────────────────────────────────────────────────────────────────────
# 17. TypeScript Test Fixture
# ──────────────────────────────────────────────────────────────────────────────
def test_typescript_fixture(chunker: CodeChunker) -> None:
    ts_code = """
import { Logger } from "./logger";

export interface IService {
    execute(): void;
}

export class OrderService implements IService {
    private logger: Logger;

    constructor(logger: Logger) {
        this.logger = logger;
    }

    public execute(): void {
        this.logger.info("Executing order");
    }
}
"""
    parser = TypeScriptParser()
    parse_res = parser.parse(ts_code, source_path="order.ts")
    norm_res = normalize_parse_result(parse_res, repository_id="repo_ts")

    collection = chunker.chunk_normalization_result(norm_res, source_code=ts_code)

    iface_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.INTERFACE_CONTEXT]
    cls_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.CLASS_CONTEXT]
    method_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.METHOD]

    assert len(iface_chunks) == 1
    assert iface_chunks[0].name == "IService"
    assert len(cls_chunks) == 1
    assert cls_chunks[0].name == "OrderService"
    assert len(method_chunks) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# 18. Decorators / Annotations Preservation
# ──────────────────────────────────────────────────────────────────────────────
def test_decorators_annotations(chunker: CodeChunker) -> None:
    py_code = """
@dataclass
@authenticated
def secure_action():
    pass
"""
    parser = PythonParser()
    parse_res = parser.parse(py_code, source_path="secure.py")
    norm_res = normalize_parse_result(parse_res, repository_id="repo_dec")

    collection = chunker.chunk_normalization_result(norm_res, source_code=py_code)
    func_chunks = [c for c in collection.chunks if c.chunk_type == ChunkType.FUNCTION]
    assert len(func_chunks) == 1
    assert func_chunks[0].name == "secure_action"


# ──────────────────────────────────────────────────────────────────────────────
# 19. Imports / Module Context
# ──────────────────────────────────────────────────────────────────────────────
def test_imports_module_context(chunker: CodeChunker) -> None:
    py_code = "import os\nimport sys\nfrom path import Path"
    parser = PythonParser()
    parse_res = parser.parse(py_code, source_path="mod.py")
    norm_res = normalize_parse_result(parse_res, repository_id="repo_mod")

    collection = chunker.chunk_normalization_result(norm_res, source_code=py_code)
    file_chunk = collection.chunks[0]
    assert file_chunk.chunk_type == ChunkType.FILE_CONTEXT
    assert "import os" in file_chunk.content


# ──────────────────────────────────────────────────────────────────────────────
# 20. Documentation Association
# ──────────────────────────────────────────────────────────────────────────────
def test_documentation_association(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_doc", repository_id="repo_1", path="doc.py", language=Language.PYTHON, loc=15
    )
    fn = Function(
        id="fn_doc",
        file_id="f_doc",
        name="foo",
        qualified_name="doc.foo",
        doc_comment="Calculates foo value.",
        location=SourceLocation(
            file_path="doc.py", start_line=2, start_column=0, end_line=5, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn])

    collection = chunker.chunk_normalization_result(result)
    func_chunk = collection.get_chunks_for_entity("fn_doc")[0]
    assert func_chunk.doc_comment == "Calculates foo value."


# ──────────────────────────────────────────────────────────────────────────────
# 21. Large Class Policy
# ──────────────────────────────────────────────────────────────────────────────
def test_large_class(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_lc", repository_id="repo_1", path="large_class.py", language=Language.PYTHON, loc=300
    )
    cls_entity = Class(
        id="cls_large",
        file_id="f_lc",
        name="GiantClass",
        qualified_name="large_class.GiantClass",
        location=SourceLocation(
            file_path="large_class.py", start_line=1, start_column=0, end_line=300, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, classes=[cls_entity])

    collection = chunker.chunk_normalization_result(result, max_lines_per_chunk=100)
    cls_chunks = collection.get_chunks_for_entity("cls_large")
    assert len(cls_chunks) == 3
    assert cls_chunks[0].chunk_type == ChunkType.CLASS_CONTEXT
    assert cls_chunks[1].chunk_type == ChunkType.SUB_CHUNK
    assert cls_chunks[2].chunk_type == ChunkType.SUB_CHUNK


# ──────────────────────────────────────────────────────────────────────────────
# 22. Large Method Policy
# ──────────────────────────────────────────────────────────────────────────────
def test_large_method_policy(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_lm", repository_id="repo_1", path="large_method.py", language=Language.PYTHON, loc=400
    )
    m = Method(
        id="m_giant",
        file_id="f_lm",
        class_id="c_any",
        name="giant_method",
        qualified_name="large_method.giant_method",
        location=SourceLocation(
            file_path="large_method.py", start_line=10, start_column=0, end_line=310, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, methods=[m])

    collection = chunker.chunk_normalization_result(result, max_lines_per_chunk=100)
    m_chunks = collection.get_chunks_for_entity("m_giant")
    assert len(m_chunks) == 4
    assert m_chunks[0].chunk_type == ChunkType.METHOD
    assert m_chunks[0].sub_chunk_index == 0
    assert m_chunks[1].chunk_type == ChunkType.SUB_CHUNK
    assert m_chunks[1].sub_chunk_index == 1
    assert m_chunks[1].parent_chunk_id == m_chunks[0].id


# ──────────────────────────────────────────────────────────────────────────────
# 23. Unknown / Unsupported IR Entities
# ──────────────────────────────────────────────────────────────────────────────
def test_unknown_unsupported_entity_behavior(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_unk", repository_id="repo_1", path="unk.py", language=Language.PYTHON, loc=10
    )
    result = NormalizationResult(file=file_entity)

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 1


# ──────────────────────────────────────────────────────────────────────────────
# 24. Top-Level Functions
# ──────────────────────────────────────────────────────────────────────────────
def test_top_level_functions(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_top", repository_id="repo_1", path="main.py", language=Language.PYTHON, loc=20
    )
    fn = Function(
        id="fn_top",
        file_id="f_top",
        name="main",
        qualified_name="main.main",
        parent_id="f_top",
        location=SourceLocation(
            file_path="main.py", start_line=2, start_column=0, end_line=5, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn])

    collection = chunker.chunk_normalization_result(result)
    fn_chunk = collection.get_chunks_for_entity("fn_top")[0]
    assert fn_chunk.parent_entity_id == "f_top"


# ──────────────────────────────────────────────────────────────────────────────
# 25. Declaration-Only Interface
# ──────────────────────────────────────────────────────────────────────────────
def test_declaration_only_interface(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_decl", repository_id="repo_1", path="EmptyIface.java", language=Language.JAVA, loc=5
    )
    iface = Interface(
        id="iface_empty",
        file_id="f_decl",
        name="EmptyIface",
        qualified_name="com.example.EmptyIface",
        location=SourceLocation(
            file_path="EmptyIface.java", start_line=3, start_column=0, end_line=5, end_column=1
        ),
    )
    result = NormalizationResult(file=file_entity, interfaces=[iface])

    collection = chunker.chunk_normalization_result(result)
    chunks = collection.get_chunks_for_entity("iface_empty")
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ChunkType.INTERFACE_CONTEXT


# ──────────────────────────────────────────────────────────────────────────────
# 26. Synthetic Scale Sanity
# ──────────────────────────────────────────────────────────────────────────────
def test_synthetic_scale_sanity(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_scale",
        repository_id="repo_scale",
        path="scale.py",
        language=Language.PYTHON,
        loc=10000,
    )
    functions: list[Function] = []
    for i in range(1000):
        start_l = i * 10 + 1
        end_l = start_l + 8
        functions.append(
            Function(
                id=f"fn_{i:04d}",
                file_id="f_scale",
                name=f"func_{i:04d}",
                qualified_name=f"scale.func_{i:04d}",
                location=SourceLocation(
                    file_path="scale.py",
                    start_line=start_l,
                    start_column=0,
                    end_line=end_l,
                    end_column=0,
                ),
            )
        )
    result = NormalizationResult(file=file_entity, functions=functions)

    start_time = time.perf_counter()
    collection = chunker.chunk_normalization_result(result)
    elapsed = time.perf_counter() - start_time

    assert len(collection) == 1001
    assert elapsed < 1.0


# ──────────────────────────────────────────────────────────────────────────────
# 27. Canonical IR Immutability
# ──────────────────────────────────────────────────────────────────────────────
def test_canonical_ir_immutability(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_imm", repository_id="repo_1", path="imm.py", language=Language.PYTHON, loc=15
    )
    fn = Function(
        id="fn_imm",
        file_id="f_imm",
        name="immutable_func",
        qualified_name="imm.immutable_func",
        location=SourceLocation(
            file_path="imm.py", start_line=2, start_column=0, end_line=5, end_column=0
        ),
    )
    result = NormalizationResult(file=file_entity, functions=[fn])

    fn_dump_before = fn.model_dump()
    file_dump_before = file_entity.model_dump()

    _ = chunker.chunk_normalization_result(result)

    assert fn.model_dump() == fn_dump_before
    assert file_entity.model_dump() == file_dump_before


# ──────────────────────────────────────────────────────────────────────────────
# 28. Malformed / Incomplete IR Handling
# ──────────────────────────────────────────────────────────────────────────────
def test_malformed_incomplete_ir_handling(chunker: CodeChunker) -> None:
    file_entity = File(
        id="f_mal", repository_id="repo_1", path="mal.py", language=Language.PYTHON, loc=10
    )
    fn_no_loc = Function(
        id="fn_noloc",
        file_id="f_mal",
        name="no_loc",
        qualified_name="mal.no_loc",
        location=None,
    )
    result = NormalizationResult(file=file_entity, functions=[fn_no_loc])

    collection = chunker.chunk_normalization_result(result)
    assert len(collection) == 2
    no_loc_chunk = collection.get_chunks_for_entity("fn_noloc")[0]
    assert no_loc_chunk.source_location is not None


# ──────────────────────────────────────────────────────────────────────────────
# 29. Section 56 & 57 Validation Scenario (Cross-Language Parity & Graph Independence)
# ──────────────────────────────────────────────────────────────────────────────
def test_cross_language_parity_and_graph_independence(chunker: CodeChunker) -> None:
    java_code = """
public class PaymentService {
    public void processPayment() {}
}
"""
    py_code = """
class PaymentService:
    def process_payment(self):
        pass
"""
    ts_code = """
export class PaymentService {
    public processPayment(): void {}
}
"""
    j_res = normalize_parse_result(
        JavaParser().parse(java_code, source_path="PaymentService.java"), "r1"
    )
    p_res = normalize_parse_result(
        PythonParser().parse(py_code, source_path="payment_service.py"), "r1"
    )
    t_res = normalize_parse_result(
        TypeScriptParser().parse(ts_code, source_path="PaymentService.ts"), "r1"
    )

    j_coll = chunker.chunk_normalization_result(j_res, source_code=java_code)
    p_coll = chunker.chunk_normalization_result(p_res, source_code=py_code)
    t_coll = chunker.chunk_normalization_result(t_res, source_code=ts_code)

    for coll in (j_coll, p_coll, t_coll):
        assert any(c.chunk_type == ChunkType.CLASS_CONTEXT for c in coll.chunks)
        assert any(c.chunk_type == ChunkType.METHOD for c in coll.chunks)
