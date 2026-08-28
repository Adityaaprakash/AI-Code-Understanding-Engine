"""Unit tests for AST -> Canonical Code IR normalization (TASK-2F)."""

import pytest

from code_analyzer.ir import EntityKind, ReferenceKind, TypeRepresentation, Visibility
from code_analyzer.normalization import normalize_parse_result
from code_analyzer.parsers.java import JavaParser
from code_analyzer.parsers.python import PythonParser
from code_analyzer.parsers.typescript import TypeScriptParser

REPO_ID = "repo-test-id"


# =====================================================================
# JAVA NORMALIZATION TESTS
# =====================================================================


@pytest.mark.unit
def test_java_package_to_module() -> None:
    code = "package com.example.service;\npublic class App {}"
    parser = JavaParser()
    res = parser.parse(code, source_path="src/App.java")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.modules) == 1
    mod = norm.modules[0]
    assert mod.name == "service"
    assert mod.qualified_name == "com.example.service"
    assert mod.file_id == norm.file.id


@pytest.mark.unit
def test_java_import_to_reference() -> None:
    code = "package com.example;\nimport java.util.List;\npublic class App {}"
    parser = JavaParser()
    res = parser.parse(code, source_path="App.java")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.references) == 1
    ref = norm.references[0]
    assert ref.ref_kind == ReferenceKind.IMPORT
    assert ref.target_qualified_name == "java.util.List"
    assert ref.target_symbol_id is None


@pytest.mark.unit
def test_java_class_and_interface() -> None:
    code = """
    package com.example;
    public class UserService extends BaseService implements IService {
        private String name;
        public UserService(String name) { this.name = name; }
        public String getName() { return this.name; }
    }
    public interface IService {}
    """
    parser = JavaParser()
    res = parser.parse(code, source_path="UserService.java")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.classes) == 1
    cls = norm.classes[0]
    assert cls.name == "UserService"
    assert cls.qualified_name == "com.example.UserService"
    assert cls.visibility == Visibility.PUBLIC
    assert cls.superclass_ref is not None
    assert cls.superclass_ref.target_qualified_name == "BaseService"
    assert len(cls.interface_refs) == 1
    assert cls.interface_refs[0].target_qualified_name == "IService"

    assert len(norm.interfaces) == 1
    iface = norm.interfaces[0]
    assert iface.name == "IService"
    assert iface.qualified_name == "com.example.IService"

    # Method & constructor check
    assert len(cls.method_ids) == 2
    constructors = [m for m in norm.methods if m.is_constructor]
    assert len(constructors) == 1
    assert constructors[0].name == "UserService"

    # Field check
    assert len(norm.variables) == 1
    var = norm.variables[0]
    assert var.name == "name"
    assert isinstance(var.declared_type, TypeRepresentation)
    assert var.declared_type.display_name == "String"


@pytest.mark.unit
def test_java_generic_types_and_parameters() -> None:
    code = """
    package com.example;
    import java.util.List;
    public class Container<T> {
        public List<String> processItems(List<T> items) { return null; }
    }
    """
    parser = JavaParser()
    res = parser.parse(code, source_path="Container.java")
    norm = normalize_parse_result(res, REPO_ID)

    cls = norm.classes[0]
    assert cls.type_parameters == ["T"]

    method = norm.methods[0]
    assert isinstance(method.return_type, TypeRepresentation)
    assert method.return_type.display_name == "List<String>"
    assert method.return_type.normalized_name == "List"
    assert len(method.return_type.type_arguments) == 1
    assert method.return_type.type_arguments[0].display_name == "String"

    assert len(method.parameters) == 1
    param = method.parameters[0]
    assert param.name == "items"
    assert param.position == 0
    assert isinstance(param.declared_type, TypeRepresentation)
    assert param.declared_type.display_name == "List<T>"


@pytest.mark.unit
def test_java_nested_class_and_deterministic_ids() -> None:
    code = """
    package com.example;
    public class Outer {
        public static class Inner {}
    }
    """
    parser = JavaParser()
    res = parser.parse(code, source_path="Outer.java")
    norm1 = normalize_parse_result(res, REPO_ID)
    norm2 = normalize_parse_result(res, REPO_ID)

    assert len(norm1.classes) == 2
    outer = next(c for c in norm1.classes if c.name == "Outer")
    inner = next(c for c in norm1.classes if c.name == "Inner")

    assert inner.qualified_name == "com.example.Outer.Inner"
    assert inner.id in outer.nested_class_ids

    # Verify deterministic IDs across runs
    assert norm1.file.id == norm2.file.id
    assert outer.id == next(c.id for c in norm2.classes if c.name == "Outer")
    assert inner.id == next(c.id for c in norm2.classes if c.name == "Inner")


# =====================================================================
# PYTHON NORMALIZATION TESTS
# =====================================================================


@pytest.mark.unit
def test_python_module_and_imports() -> None:
    code = "import os\nfrom typing import List, Optional\n"
    parser = PythonParser()
    res = parser.parse(code, source_path="services/utils.py")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.modules) == 1
    mod = norm.modules[0]
    assert mod.name == "utils"
    assert mod.qualified_name == "services.utils"

    assert len(norm.references) == 3
    targets = {r.target_qualified_name for r in norm.references}
    assert targets == {"os", "typing.List", "typing.Optional"}


@pytest.mark.unit
def test_python_class_function_method_async() -> None:
    code = """
import asyncio

def top_function(x: int) -> int:
    return x + 1

class UserService(BaseService):
    @classmethod
    async def fetch_user(cls, user_id: int) -> Optional[User]:
        pass
"""
    parser = PythonParser()
    res = parser.parse(code, source_path="services/user.py")
    norm = normalize_parse_result(res, REPO_ID)

    # Function vs Method check
    assert len(norm.functions) == 1
    fn = norm.functions[0]
    assert fn.name == "top_function"
    assert fn.kind == EntityKind.FUNCTION
    assert isinstance(fn.return_type, TypeRepresentation)
    assert fn.return_type.display_name == "int"

    assert len(norm.classes) == 1
    cls = norm.classes[0]
    assert cls.name == "UserService"
    assert cls.kind == EntityKind.CLASS
    assert cls.superclass_ref is not None
    assert cls.superclass_ref.target_qualified_name == "BaseService"

    assert len(norm.methods) == 1
    method = norm.methods[0]
    assert method.name == "fetch_user"
    assert method.kind == EntityKind.METHOD
    assert method.is_async is True
    assert method.is_static is True  # @classmethod mapped to static-like
    assert "decorators" in method.metadata
    assert "classmethod" in method.metadata["decorators"]


@pytest.mark.unit
def test_python_field_and_parameters() -> None:
    code = """
class Config:
    MAX_ITEMS: int = 100

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
"""
    parser = PythonParser()
    res = parser.parse(code, source_path="config.py")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.variables) == 1
    var = norm.variables[0]
    assert var.name == "MAX_ITEMS"
    assert var.initializer == "100"

    method = norm.methods[0]
    assert method.name == "__init__"
    assert method.is_constructor is True

    assert len(method.parameters) == 2
    param_timeout = method.parameters[1]
    assert param_timeout.name == "timeout"
    assert param_timeout.default_value == "30"


# =====================================================================
# TYPESCRIPT NORMALIZATION TESTS
# =====================================================================


@pytest.mark.unit
def test_typescript_class_interface_generics() -> None:
    code = """
import { BaseService } from "./base";

export interface IRepository<T> {
    find(id: string): Promise<T>;
}

export class UserService<T> extends BaseService implements IRepository<T> {
    public constructor(public name: string) {}
    public async find(id: string): Promise<T> { return null; }
}
"""
    parser = TypeScriptParser()
    res = parser.parse(code, source_path="services/user.ts")
    norm = normalize_parse_result(res, REPO_ID)

    assert len(norm.interfaces) == 1
    iface = norm.interfaces[0]
    assert iface.name == "IRepository"
    assert iface.type_parameters == ["T"]
    assert iface.metadata.get("is_exported") is True

    assert len(norm.classes) == 1
    cls = norm.classes[0]
    assert cls.name == "UserService"
    assert cls.type_parameters == ["T"]
    assert cls.superclass_ref is not None
    assert cls.superclass_ref.target_qualified_name == "BaseService"
    assert len(cls.interface_refs) == 1
    assert cls.interface_refs[0].target_qualified_name == "IRepository<T>"

    # Method & async check
    find_method = next(m for m in norm.methods if m.name == "find")
    assert find_method.is_async is True
    assert isinstance(find_method.return_type, TypeRepresentation)
    assert find_method.return_type.display_name == "Promise<T>"


@pytest.mark.unit
def test_typescript_type_aliases_and_exports() -> None:
    code = """
export type UserID = string;
export function getUser(id: UserID): void {}
"""
    parser = TypeScriptParser()
    res = parser.parse(code, source_path="types.ts")
    norm = normalize_parse_result(res, REPO_ID)

    # Type alias mapped to Variable with metadata
    type_var = next(v for v in norm.variables if v.name == "UserID")
    assert type_var.metadata.get("is_type_alias") is True
    assert type_var.metadata.get("definition") == "string"

    fn = norm.functions[0]
    assert fn.name == "getUser"
    assert fn.metadata.get("is_exported") is True


# =====================================================================
# CROSS-LANGUAGE CONSISTENCY & IDEMPOTENCY TESTS
# =====================================================================


@pytest.mark.unit
def test_cross_language_entity_kind_consistency() -> None:
    """Verify equivalent constructs in Java, Python, and TypeScript produce identical EntityKinds."""
    java_code = "public class UserService { public void getUser() {} }"
    py_code = "class UserService:\n    def get_user(self):\n        pass"
    ts_code = "class UserService { getUser(): void {} }"

    java_norm = normalize_parse_result(
        JavaParser().parse(java_code, source_path="UserService.java"), REPO_ID
    )
    py_norm = normalize_parse_result(
        PythonParser().parse(py_code, source_path="user_service.py"), REPO_ID
    )
    ts_norm = normalize_parse_result(
        TypeScriptParser().parse(ts_code, source_path="UserService.ts"), REPO_ID
    )

    # All produce EntityKind.CLASS for class declaration
    assert java_norm.classes[0].kind == EntityKind.CLASS
    assert py_norm.classes[0].kind == EntityKind.CLASS
    assert ts_norm.classes[0].kind == EntityKind.CLASS
    assert type(java_norm.classes[0]) is type(py_norm.classes[0]) is type(ts_norm.classes[0])

    # All produce EntityKind.METHOD for class methods
    assert java_norm.methods[0].kind == EntityKind.METHOD
    assert py_norm.methods[0].kind == EntityKind.METHOD
    assert ts_norm.methods[0].kind == EntityKind.METHOD
    assert type(java_norm.methods[0]) is type(py_norm.methods[0]) is type(ts_norm.methods[0])


@pytest.mark.unit
def test_no_language_ast_leakage() -> None:
    """Verify normalized entities contain only canonical IR models and standard types."""
    code = "public class App { private String version; }"
    norm = normalize_parse_result(JavaParser().parse(code, source_path="App.java"), REPO_ID)

    cls = norm.classes[0]
    assert not hasattr(cls, "JavaClass")
    assert not hasattr(cls, "JavaField")
    assert type(cls.name) is str
    assert type(cls.kind) is EntityKind


@pytest.mark.unit
def test_normalization_idempotency() -> None:
    """Verify normalizing the exact same ParseResult twice yields identical results."""
    code = "package com.test;\npublic class App { public void main() {} }"
    parse_res = JavaParser().parse(code, source_path="App.java")

    norm1 = normalize_parse_result(parse_res, REPO_ID)
    norm2 = normalize_parse_result(parse_res, REPO_ID)

    assert norm1.file.id == norm2.file.id
    assert norm1.classes[0].id == norm2.classes[0].id
    assert norm1.methods[0].id == norm2.methods[0].id
    assert norm1 == norm2
