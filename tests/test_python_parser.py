"""Unit tests for the Python AST parser implementation (TASK-2C)."""

import pytest

from code_analyzer.parsers import (
    DiagnosticSeverity,
    Language,
    PythonClass,
    PythonFunction,
    PythonImport,
    PythonModule,
    PythonParser,
)


@pytest.mark.unit
def test_python_parser_basic_parsing() -> None:
    """Test basic Python source parsing producing a valid PythonModule AST."""
    parser = PythonParser()
    source = """class UserService:
    def get_user(self, user_id: int) -> str:
        return "user"
"""
    result = parser.parse(source, source_path="services/user.py")

    assert result.success is True
    assert result.language == Language.PYTHON
    assert result.source_path == "services/user.py"
    assert isinstance(result.ast, PythonModule)
    assert result.has_errors is False
    assert len(result.diagnostics) == 0


@pytest.mark.unit
def test_python_parser_module_level_functions() -> None:
    """Test extraction of top-level module functions."""
    parser = PythonParser()
    source = """def calculate_total(a: int, b: int) -> int:
    return a + b
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.functions) == 1

    fn: PythonFunction = module.functions[0]
    assert fn.name == "calculate_total"
    assert fn.is_method is False
    assert fn.return_type == "int"
    assert len(fn.parameters) == 2
    assert fn.parameters[0].name == "a"
    assert fn.parameters[0].annotation == "int"
    assert fn.parameters[1].name == "b"
    assert fn.parameters[1].annotation == "int"


@pytest.mark.unit
def test_python_parser_classes() -> None:
    """Test extraction of Python classes and base classes."""
    parser = PythonParser()
    source = """class BaseService:
    pass

class UserService(BaseService, Generic[T]):
    pass
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.classes) == 2

    cls0: PythonClass = module.classes[0]
    assert cls0.name == "BaseService"
    assert len(cls0.bases) == 0

    cls1: PythonClass = module.classes[1]
    assert cls1.name == "UserService"
    assert "BaseService" in cls1.bases
    assert "Generic[T]" in cls1.bases


@pytest.mark.unit
def test_python_parser_methods() -> None:
    """Test that class methods are distinguished from module-level functions."""
    parser = PythonParser()
    source = """def standalone():
    pass

class UserService:
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return self.name
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.functions) == 1
    assert module.functions[0].name == "standalone"
    assert module.functions[0].is_method is False

    cls: PythonClass = module.classes[0]
    assert len(cls.methods) == 2

    ctor: PythonFunction = cls.methods[0]
    assert ctor.name == "__init__"
    assert ctor.is_method is True
    assert ctor.parameters[0].name == "self"
    assert ctor.parameters[1].name == "name"

    getter: PythonFunction = cls.methods[1]
    assert getter.name == "get_name"
    assert getter.is_method is True
    assert getter.return_type == "str"


@pytest.mark.unit
def test_python_parser_async_functions() -> None:
    """Test extraction of async function and async method declarations."""
    parser = PythonParser()
    source = """async def fetch_user(user_id: int) -> str:
    return "user"

class APIClient:
    async def get_data(self) -> dict:
        return {}
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.functions) == 1
    assert module.functions[0].name == "fetch_user"
    assert module.functions[0].is_async is True

    cls: PythonClass = module.classes[0]
    assert len(cls.methods) == 1
    assert cls.methods[0].name == "get_data"
    assert cls.methods[0].is_async is True


@pytest.mark.unit
def test_python_parser_imports() -> None:
    """Test extraction of import and from-import statements."""
    parser = PythonParser()
    source = """import os
import os.path
from typing import List, Optional
from services.user import UserService
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.imports) == 4

    imp0: PythonImport = module.imports[0]
    assert imp0.is_from_import is False
    assert "os" in imp0.names

    imp1: PythonImport = module.imports[1]
    assert imp1.is_from_import is False
    assert "os.path" in imp1.names

    imp2: PythonImport = module.imports[2]
    assert imp2.is_from_import is True
    assert imp2.module == "typing"
    assert "List" in imp2.names
    assert "Optional" in imp2.names

    imp3: PythonImport = module.imports[3]
    assert imp3.is_from_import is True
    assert imp3.module == "services.user"
    assert "UserService" in imp3.names


@pytest.mark.unit
def test_python_parser_import_aliases() -> None:
    """Test extraction of imported names with aliases."""
    parser = PythonParser()
    source = """import numpy as np
from package.module import Service as UserService, Helper as H
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    assert len(module.imports) == 2

    imp0: PythonImport = module.imports[0]
    assert imp0.alias_map.get("numpy") == "np"

    imp1: PythonImport = module.imports[1]
    assert imp1.alias_map.get("Service") == "UserService"
    assert imp1.alias_map.get("Helper") == "H"


@pytest.mark.unit
def test_python_parser_decorators() -> None:
    """Test extraction of function decorators."""
    parser = PythonParser()
    source = """@service
@router.get("/users")
def get_users():
    pass
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    fn: PythonFunction = module.functions[0]

    assert len(fn.decorators) == 2
    assert fn.decorators[0].expression == "service"
    assert fn.decorators[1].expression == 'router.get("/users")'


@pytest.mark.unit
def test_python_parser_decorated_classes() -> None:
    """Test extraction of class decorators."""
    parser = PythonParser()
    source = """@dataclass
@service
class User:
    name: str
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast
    cls: PythonClass = module.classes[0]

    assert len(cls.decorators) == 2
    assert cls.decorators[0].expression == "dataclass"
    assert cls.decorators[1].expression == "service"


@pytest.mark.unit
def test_python_parser_nested_declarations() -> None:
    """Test extraction of nested functions and nested classes."""
    parser = PythonParser()
    source = """def outer_func():
    def inner_func():
        pass
    class InnerClassInFunc:
        pass

class OuterClass:
    class InnerClass:
        def inner_method(self):
            pass
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast

    outer_fn: PythonFunction = module.functions[0]
    assert len(outer_fn.nested_functions) == 1
    assert outer_fn.nested_functions[0].name == "inner_func"
    assert len(outer_fn.nested_classes) == 1
    assert outer_fn.nested_classes[0].name == "InnerClassInFunc"

    outer_cls: PythonClass = module.classes[0]
    assert len(outer_cls.nested_classes) == 1
    inner_cls: PythonClass = outer_cls.nested_classes[0]
    assert inner_cls.name == "InnerClass"
    assert len(inner_cls.methods) == 1
    assert inner_cls.methods[0].name == "inner_method"


@pytest.mark.unit
def test_python_parser_syntax_failures() -> None:
    """Test graceful error handling for malformed Python code."""
    parser = PythonParser()
    malformed_inputs = [
        "def foo(:\n",
        "class:\n",
        "def bar(a, b",
    ]

    for bad_source in malformed_inputs:
        result = parser.parse(bad_source)
        assert result.success is False
        assert len(result.diagnostics) > 0
        assert result.has_errors is True
        assert any(d.severity == DiagnosticSeverity.ERROR for d in result.diagnostics)


@pytest.mark.unit
def test_python_parser_source_locations() -> None:
    """Test accurate source locations for Python elements."""
    parser = PythonParser()
    source = """import os

class UserService:
    def get_user(self):
        pass
"""
    result = parser.parse(source)

    assert result.success is True
    module: PythonModule = result.ast

    imp: PythonImport = module.imports[0]
    assert imp.location.start_line == 1
    assert imp.location.start_column == 0

    cls: PythonClass = module.classes[0]
    assert cls.location.start_line == 3
    assert cls.location.end_line == 5

    fn: PythonFunction = cls.methods[0]
    assert fn.location.start_line == 4
    assert fn.location.start_column == 4
