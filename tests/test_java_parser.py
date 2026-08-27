"""Unit tests for the Java AST parser implementation (TASK-2B)."""

import pytest

from code_analyzer.parsers import (
    DiagnosticSeverity,
    JavaClass,
    JavaField,
    JavaImport,
    JavaMethod,
    JavaPackage,
    JavaParser,
    JavaStructure,
    Language,
)


@pytest.mark.unit
def test_java_parser_basic_parsing() -> None:
    """Test basic Java source parsing producing a valid JavaStructure AST."""
    parser = JavaParser()
    source = """package com.example;

import java.util.List;

public class UserService {
}
"""
    result = parser.parse(source, source_path="com/example/UserService.java")

    assert result.success is True
    assert result.language == Language.JAVA
    assert result.source_path == "com/example/UserService.java"
    assert isinstance(result.ast, JavaStructure)
    assert result.has_errors is False
    assert len(result.diagnostics) == 0


@pytest.mark.unit
def test_java_parser_package_extraction() -> None:
    """Test extraction of package declaration and location."""
    parser = JavaParser()
    source = "package com.example.service;\n"
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    assert ast.package is not None
    assert isinstance(ast.package, JavaPackage)
    assert ast.package.name == "com.example.service"
    assert ast.package.location.start_line == 1
    assert ast.package.location.start_column == 0


@pytest.mark.unit
def test_java_parser_import_extraction() -> None:
    """Test extraction of normal, static, and wildcard imports."""
    parser = JavaParser()
    source = """package com.example;

import java.util.List;
import java.util.Map;
import static java.util.Collections.emptyList;
import java.util.*;
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    assert len(ast.imports) == 4

    imp0: JavaImport = ast.imports[0]
    assert imp0.path == "java.util.List"
    assert imp0.is_static is False
    assert imp0.is_wildcard is False

    imp1: JavaImport = ast.imports[1]
    assert imp1.path == "java.util.Map"
    assert imp1.is_static is False
    assert imp1.is_wildcard is False

    imp2: JavaImport = ast.imports[2]
    assert imp2.path == "java.util.Collections.emptyList"
    assert imp2.is_static is True
    assert imp2.is_wildcard is False

    imp3: JavaImport = ast.imports[3]
    assert imp3.path == "java.util.*"
    assert imp3.is_static is False
    assert imp3.is_wildcard is True


@pytest.mark.unit
def test_java_parser_class_extraction() -> None:
    """Test extraction of class declarations, modifiers, extends, and implements."""
    parser = JavaParser()
    source = """package com.example;

public abstract class BaseService extends ParentService implements Runnable, Serializable {
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    assert len(ast.classes) == 1

    cls: JavaClass = ast.classes[0]
    assert cls.name == "BaseService"
    assert cls.is_interface is False
    assert "public" in cls.modifiers
    assert "abstract" in cls.modifiers
    assert cls.extends_clause == "ParentService"
    assert "Runnable" in cls.implements_clause
    assert "Serializable" in cls.implements_clause


@pytest.mark.unit
def test_java_parser_interface_extraction() -> None:
    """Test extraction of interface declaration."""
    parser = JavaParser()
    source = """package com.example;

public interface Repository {
    void save(Object entity);
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    assert len(ast.classes) == 1

    iface: JavaClass = ast.classes[0]
    assert iface.name == "Repository"
    assert iface.is_interface is True
    assert "public" in iface.modifiers
    assert len(iface.methods) == 1
    assert iface.methods[0].name == "save"
    assert iface.methods[0].return_type == "void"


@pytest.mark.unit
def test_java_parser_method_extraction() -> None:
    """Test extraction of constructors, instance methods, static methods, parameters, and return types."""
    parser = JavaParser()
    source = """package com.example;

public class UserService {
    private String name;

    public UserService(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }

    private void logInternal(String msg, int level) {
    }

    public static int calculateMax(int a, int b) {
        return a > b ? a : b;
    }
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    cls: JavaClass = ast.classes[0]

    assert len(cls.methods) == 4

    ctor: JavaMethod = cls.methods[0]
    assert ctor.name == "UserService"
    assert ctor.is_constructor is True
    assert ctor.return_type is None
    assert "public" in ctor.modifiers
    assert len(ctor.parameters) == 1
    assert ctor.parameters[0].name == "name"
    assert ctor.parameters[0].type_name == "String"

    getter: JavaMethod = cls.methods[1]
    assert getter.name == "getName"
    assert getter.is_constructor is False
    assert getter.return_type == "String"
    assert "public" in getter.modifiers

    internal: JavaMethod = cls.methods[2]
    assert internal.name == "logInternal"
    assert internal.return_type == "void"
    assert "private" in internal.modifiers
    assert len(internal.parameters) == 2
    assert internal.parameters[0].name == "msg"
    assert internal.parameters[0].type_name == "String"
    assert internal.parameters[1].name == "level"
    assert internal.parameters[1].type_name == "int"

    calc: JavaMethod = cls.methods[3]
    assert calc.name == "calculateMax"
    assert calc.return_type == "int"
    assert "public" in calc.modifiers
    assert "static" in calc.modifiers


@pytest.mark.unit
def test_java_parser_field_extraction() -> None:
    """Test extraction of instance fields, static final fields, and multiple declarators."""
    parser = JavaParser()
    source = """package com.example;

public class Config {
    private String name;
    private static final int MAX = 10;
    int x, y;
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    cls: JavaClass = ast.classes[0]

    assert len(cls.fields) == 4

    f0: JavaField = cls.fields[0]
    assert f0.name == "name"
    assert f0.type_name == "String"
    assert "private" in f0.modifiers

    f1: JavaField = cls.fields[1]
    assert f1.name == "MAX"
    assert f1.type_name == "int"
    assert "private" in f1.modifiers
    assert "static" in f1.modifiers
    assert "final" in f1.modifiers

    f2: JavaField = cls.fields[2]
    assert f2.name == "x"
    assert f2.type_name == "int"

    f3: JavaField = cls.fields[3]
    assert f3.name == "y"
    assert f3.type_name == "int"


@pytest.mark.unit
def test_java_parser_nested_declarations() -> None:
    """Test extraction of nested classes and nested interfaces."""
    parser = JavaParser()
    source = """package com.example;

public class Outer {
    public class InnerClass {
        private int innerValue;
    }

    public interface InnerInterface {
        void execute();
    }
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    cls: JavaClass = ast.classes[0]

    assert len(cls.nested_classes) == 2

    nested_cls: JavaClass = cls.nested_classes[0]
    assert nested_cls.name == "InnerClass"
    assert nested_cls.is_interface is False
    assert len(nested_cls.fields) == 1
    assert nested_cls.fields[0].name == "innerValue"

    nested_iface: JavaClass = cls.nested_classes[1]
    assert nested_iface.name == "InnerInterface"
    assert nested_iface.is_interface is True
    assert len(nested_iface.methods) == 1
    assert nested_iface.methods[0].name == "execute"


@pytest.mark.unit
def test_java_parser_generic_declarations() -> None:
    """Test extraction of generic classes and generic methods."""
    parser = JavaParser()
    source = """package com.example;

public class Container<T> {
    public <E> E processItem(E item) {
        return item;
    }
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast
    cls: JavaClass = ast.classes[0]

    assert cls.name == "Container"
    assert "T" in cls.type_parameters
    assert len(cls.methods) == 1

    method: JavaMethod = cls.methods[0]
    assert method.name == "processItem"
    assert "E" in method.type_parameters
    assert method.return_type == "E"


@pytest.mark.unit
def test_java_parser_syntax_failures() -> None:
    """Test graceful handling of malformed Java source code."""
    parser = JavaParser()

    malformed_inputs = [
        "package com.example;\npublic class Foo {",  # missing closing brace
        "public class Foo { void bar( }",  # malformed method parameter list
        "class {",  # malformed class declaration
    ]

    for bad_source in malformed_inputs:
        result = parser.parse(bad_source)
        assert result.success is False
        assert len(result.diagnostics) > 0
        assert result.has_errors is True
        assert any(d.severity == DiagnosticSeverity.ERROR for d in result.diagnostics)


@pytest.mark.unit
def test_java_parser_source_locations() -> None:
    """Test accurate source location ranges for extracted Java elements."""
    parser = JavaParser()
    source = """package com.example;

public class UserService {
    private String name;
}
"""
    result = parser.parse(source)

    assert result.success is True
    ast: JavaStructure = result.ast

    assert ast.package is not None
    assert ast.package.location.start_line == 1
    assert ast.package.location.start_column == 0

    cls: JavaClass = ast.classes[0]
    assert cls.location.start_line == 3
    assert cls.location.end_line == 5

    f: JavaField = cls.fields[0]
    assert f.location.start_line == 4
    assert f.location.start_column == 4
