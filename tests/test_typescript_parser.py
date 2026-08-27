"""Unit tests for the TypeScript AST parser implementation (TASK-2D)."""

import pytest

from code_analyzer.parsers import (
    DiagnosticSeverity,
    Language,
    TypeScriptClass,
    TypeScriptExport,
    TypeScriptField,
    TypeScriptFunction,
    TypeScriptImport,
    TypeScriptInterface,
    TypeScriptParser,
    TypeScriptStructure,
    TypeScriptType,
)


@pytest.mark.unit
def test_typescript_parser_basic_parsing() -> None:
    """Test basic TypeScript source parsing producing a valid TypeScriptStructure AST."""
    parser = TypeScriptParser()
    source = """export class UserService {
    public get_user(id: string): string {
        return "user";
    }
}
"""
    result = parser.parse(source, source_path="services/user.ts")

    assert result.success is True
    assert result.language == Language.TYPESCRIPT
    assert result.source_path == "services/user.ts"
    assert isinstance(result.ast, TypeScriptStructure)
    assert result.has_errors is False
    assert len(result.diagnostics) == 0


@pytest.mark.unit
def test_typescript_parser_class_extraction() -> None:
    """Test extraction of TypeScript class, modifiers, extends, implements, constructors, fields, methods."""
    parser = TypeScriptParser()
    source = """export class UserServiceImpl extends BaseService implements Repository<User> {
    private readonly name: string;

    constructor(name: string) {
        super();
        this.name = name;
    }

    public getUser(id: string): string {
        return this.name;
    }
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.classes) == 1

    cls: TypeScriptClass = struct.classes[0]
    assert cls.name == "UserServiceImpl"
    assert cls.is_exported is True
    assert cls.extends_clause == "BaseService"
    assert "Repository<User>" in cls.implements_clause

    assert len(cls.fields) == 1
    assert cls.fields[0].name == "name"
    assert "private" in cls.fields[0].modifiers
    assert "readonly" in cls.fields[0].modifiers

    assert len(cls.constructors) == 1
    assert cls.constructors[0].name == "constructor"

    assert len(cls.methods) == 1
    assert cls.methods[0].name == "getUser"
    assert cls.methods[0].return_type == "string"


@pytest.mark.unit
def test_typescript_parser_interface_extraction() -> None:
    """Test extraction of interface declarations and members."""
    parser = TypeScriptParser()
    source = """export interface User {
    id: number;
    name: string;
    save(entity: any): boolean;
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.interfaces) == 1

    iface: TypeScriptInterface = struct.interfaces[0]
    assert iface.name == "User"
    assert iface.is_exported is True
    assert len(iface.fields) == 2
    assert iface.fields[0].name == "id"
    assert iface.fields[0].type_annotation == "number"
    assert iface.fields[1].name == "name"
    assert iface.fields[1].type_annotation == "string"

    assert len(iface.methods) == 1
    assert iface.methods[0].name == "save"


@pytest.mark.unit
def test_typescript_parser_function_extraction() -> None:
    """Test extraction of top-level function declarations."""
    parser = TypeScriptParser()
    source = """function calculateTotal(a: number, b: number): number {
    return a + b;
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.functions) == 1

    fn: TypeScriptFunction = struct.functions[0]
    assert fn.name == "calculateTotal"
    assert fn.is_async is False
    assert fn.is_exported is False
    assert fn.return_type == "number"
    assert len(fn.parameters) == 2
    assert fn.parameters[0].name == "a"
    assert fn.parameters[1].name == "b"


@pytest.mark.unit
def test_typescript_parser_async_functions() -> None:
    """Test extraction of async exported functions."""
    parser = TypeScriptParser()
    source = """export async function fetchUser(id: string): Promise<User> {
    return null as any;
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.functions) == 1

    fn: TypeScriptFunction = struct.functions[0]
    assert fn.name == "fetchUser"
    assert fn.is_async is True
    assert fn.is_exported is True
    assert fn.return_type == "Promise<User>"


@pytest.mark.unit
def test_typescript_parser_generic_declarations() -> None:
    """Test extraction of generic classes and generic functions."""
    parser = TypeScriptParser()
    source = """export class Repository<T> {
}

export function mapItem<T, R>(item: T): R {
    return null as any;
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast

    cls: TypeScriptClass = struct.classes[0]
    assert cls.name == "Repository"
    assert "T" in cls.type_parameters

    fn: TypeScriptFunction = struct.functions[0]
    assert fn.name == "mapItem"
    assert "T" in fn.type_parameters
    assert "R" in fn.type_parameters


@pytest.mark.unit
def test_typescript_parser_imports() -> None:
    """Test extraction of named, default, namespace, and type-only imports."""
    parser = TypeScriptParser()
    source = """import { User } from "./user";
import UserService from "./service";
import * as Utils from "./utils";
import type { User as UserType } from "./types";
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.imports) == 4

    imp0: TypeScriptImport = struct.imports[0]
    assert imp0.module_path == "./user"
    assert "User" in imp0.imported_names

    imp1: TypeScriptImport = struct.imports[1]
    assert imp1.module_path == "./service"
    assert imp1.default_import == "UserService"

    imp2: TypeScriptImport = struct.imports[2]
    assert imp2.module_path == "./utils"
    assert imp2.namespace_import == "Utils"

    imp3: TypeScriptImport = struct.imports[3]
    assert imp3.module_path == "./types"
    assert imp3.is_type_only is True
    assert imp3.alias_map.get("User") == "UserType"


@pytest.mark.unit
def test_typescript_parser_exports() -> None:
    """Test extraction of exported declarations and export default statements."""
    parser = TypeScriptParser()
    source = """export class User {}
export interface Item {}
export function getUser() {}
export default User;
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.exports) >= 4

    def_exp: TypeScriptExport = next(e for e in struct.exports if e.kind == "default")
    assert def_exp.default_export == "User"


@pytest.mark.unit
def test_typescript_parser_named_export_aliases() -> None:
    """Test extraction of named re-exports with aliases."""
    parser = TypeScriptParser()
    source = """export { User as AdminUser };
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.exports) == 1

    exp: TypeScriptExport = struct.exports[0]
    assert exp.alias_map.get("User") == "AdminUser"


@pytest.mark.unit
def test_typescript_parser_type_aliases() -> None:
    """Test extraction of type alias declarations."""
    parser = TypeScriptParser()
    source = """type UserId = string;

export type User = {
    id: UserId;
    name: string;
};
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    assert len(struct.types) == 2

    t0: TypeScriptType = struct.types[0]
    assert t0.name == "UserId"
    assert t0.is_exported is False
    assert t0.definition == "string"

    t1: TypeScriptType = struct.types[1]
    assert t1.name == "User"
    assert t1.is_exported is True


@pytest.mark.unit
def test_typescript_parser_nested_members() -> None:
    """Test extraction of class member fields and methods."""
    parser = TypeScriptParser()
    source = """class Outer {
    private count: number;

    public increment(): void {
        this.count++;
    }
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast
    cls: TypeScriptClass = struct.classes[0]

    assert len(cls.fields) == 1
    assert cls.fields[0].name == "count"
    assert len(cls.methods) == 1
    assert cls.methods[0].name == "increment"


@pytest.mark.unit
def test_typescript_parser_syntax_failures() -> None:
    """Test graceful error handling for malformed TypeScript code."""
    parser = TypeScriptParser()
    malformed_inputs = [
        "export class User {\n",
        "interface {\n",
        "function foo(a: string\n",
    ]

    for bad_source in malformed_inputs:
        result = parser.parse(bad_source)
        assert result.success is False
        assert len(result.diagnostics) > 0
        assert result.has_errors is True
        assert any(d.severity == DiagnosticSeverity.ERROR for d in result.diagnostics)


@pytest.mark.unit
def test_typescript_parser_source_locations() -> None:
    """Test accurate source locations for TypeScript elements."""
    parser = TypeScriptParser()
    source = """import { User } from "./user";

export class UserService {
    private name: string;
}
"""
    result = parser.parse(source)

    assert result.success is True
    struct: TypeScriptStructure = result.ast

    imp: TypeScriptImport = struct.imports[0]
    assert imp.location.start_line == 1
    assert imp.location.start_column == 0

    cls: TypeScriptClass = struct.classes[0]
    assert cls.location.start_line == 3
    assert cls.location.end_line == 5

    f: TypeScriptField = cls.fields[0]
    assert f.location.start_line == 4
    assert f.location.start_column == 4
