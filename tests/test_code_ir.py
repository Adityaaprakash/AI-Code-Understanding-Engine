"""Unit tests for Canonical Code IR entity models, validation, identity, and serialization (TASK-2E)."""

import pytest
from pydantic import ValidationError

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
    Function,
    Interface,
    Method,
    Module,
    Parameter,
    Reference,
    ReferenceKind,
    Repository,
    SourceLocation,
    TypeRepresentation,
    Variable,
    Visibility,
    generate_entity_id,
)
from code_analyzer.parsers.models import Language


@pytest.mark.unit
def test_ir_entity_kind_enum_values() -> None:
    """Verify all required EntityKind enum values exist and match string representation."""
    expected_kinds = {
        "repository": EntityKind.REPOSITORY,
        "file": EntityKind.FILE,
        "module": EntityKind.MODULE,
        "class": EntityKind.CLASS,
        "interface": EntityKind.INTERFACE,
        "function": EntityKind.FUNCTION,
        "method": EntityKind.METHOD,
        "variable": EntityKind.VARIABLE,
        "parameter": EntityKind.PARAMETER,
        "reference": EntityKind.REFERENCE,
        "symbol": EntityKind.SYMBOL,
    }

    for expected_str, kind_enum in expected_kinds.items():
        assert kind_enum.value == expected_str
        assert EntityKind(expected_str) == kind_enum


@pytest.mark.unit
def test_ir_reference_kind_enum_values() -> None:
    """Verify baseline ReferenceKind enum values exist."""
    expected_refs = [
        ReferenceKind.IMPORT,
        ReferenceKind.CALL,
        ReferenceKind.EXTENDS,
        ReferenceKind.IMPLEMENTS,
        ReferenceKind.TYPE_USAGE,
        ReferenceKind.VARIABLE_USAGE,
        ReferenceKind.INSTANTIATION,
        ReferenceKind.OVERRIDE,
        ReferenceKind.FIELD_ACCESS,
    ]

    for ref in expected_refs:
        assert isinstance(ref.value, str)
        assert ReferenceKind(ref.value) == ref


@pytest.mark.unit
def test_ir_source_location_validation() -> None:
    """Verify SourceLocation attributes, 1-indexed line enforcement, and range invariants."""
    loc = SourceLocation(
        file_path="src/App.java",
        start_line=10,
        start_column=4,
        end_line=20,
        end_column=8,
    )
    assert loc.file_path == "src/App.java"
    assert loc.start_line == 10
    assert loc.start_column == 4
    assert loc.end_line == 20
    assert loc.end_column == 8

    # Invalid line (< 1)
    with pytest.raises(ValidationError):
        SourceLocation(start_line=0, start_column=0, end_line=1, end_column=5)

    # Invalid column (< 0)
    with pytest.raises(ValidationError):
        SourceLocation(start_line=1, start_column=-1, end_line=1, end_column=5)

    # Invalid line range (end_line < start_line)
    with pytest.raises(ValidationError):
        SourceLocation(start_line=10, start_column=0, end_line=5, end_column=5)

    # Invalid column range on same line (end_column < start_column)
    with pytest.raises(ValidationError):
        SourceLocation(start_line=10, start_column=15, end_line=10, end_column=5)


@pytest.mark.unit
def test_ir_repository_entity() -> None:
    """Verify Repository entity creation, attributes, and file containment."""
    repo_id = generate_entity_id(EntityKind.REPOSITORY, "", "CodeLensEngine")
    repo = Repository(
        id=repo_id,
        name="CodeLensEngine",
        root_path="/projects/CodeLensEngine",
        files=["file-id-1", "file-id-2"],
        language_breakdown={Language.JAVA: 500, Language.PYTHON: 1200},
    )

    assert repo.id == repo_id
    assert repo.kind == EntityKind.REPOSITORY
    assert repo.name == "CodeLensEngine"
    assert repo.root_path == "/projects/CodeLensEngine"
    assert len(repo.files) == 2
    assert repo.language_breakdown[Language.PYTHON] == 1200


@pytest.mark.unit
def test_ir_file_entity() -> None:
    """Verify File entity creation and metadata."""
    repo_id = generate_entity_id(EntityKind.REPOSITORY, "", "Repo")
    file_id = generate_entity_id(EntityKind.FILE, "services/user.py", "services/user.py")

    file_entity = File(
        id=file_id,
        repository_id=repo_id,
        path="services/user.py",
        language=Language.PYTHON,
        content_hash="a1b2c3d4e5f6",
        loc=150,
        module_ids=["module-1"],
        symbol_ids=["symbol-1", "symbol-2"],
        reference_ids=["ref-1"],
    )

    assert file_entity.id == file_id
    assert file_entity.kind == EntityKind.FILE
    assert file_entity.repository_id == repo_id
    assert file_entity.path == "services/user.py"
    assert file_entity.language == Language.PYTHON
    assert file_entity.loc == 150
    assert len(file_entity.symbol_ids) == 2


@pytest.mark.unit
def test_ir_module_entity() -> None:
    """Verify Module entity creation and relationships."""
    file_id = generate_entity_id(EntityKind.FILE, "com/example/App.java", "App.java")
    mod_id = generate_entity_id(EntityKind.MODULE, "com/example/App.java", "com.example")

    mod = Module(
        id=mod_id,
        file_id=file_id,
        name="example",
        qualified_name="com.example",
        exported_symbol_ids=["sym-1"],
    )

    assert mod.id == mod_id
    assert mod.kind == EntityKind.MODULE
    assert mod.file_id == file_id
    assert mod.name == "example"
    assert mod.qualified_name == "com.example"


@pytest.mark.unit
def test_ir_class_entity() -> None:
    """Verify Class entity creation, modifiers, inheritance references, and location."""
    file_id = generate_entity_id(EntityKind.FILE, "UserService.java", "UserService.java")
    class_id = generate_entity_id(EntityKind.CLASS, "UserService.java", "com.example.UserService")

    loc = SourceLocation(
        file_path="UserService.java",
        start_line=5,
        start_column=0,
        end_line=50,
        end_column=1,
    )

    super_ref = Reference(
        id=generate_entity_id(EntityKind.REFERENCE, "UserService.java", "BaseService"),
        ref_kind=ReferenceKind.EXTENDS,
        target_qualified_name="com.example.BaseService",
    )

    cls = Class(
        id=class_id,
        file_id=file_id,
        name="UserService",
        qualified_name="com.example.UserService",
        modifiers=["public", "final"],
        type_parameters=["T"],
        superclass_ref=super_ref,
        visibility=Visibility.PUBLIC,
        location=loc,
        doc_comment="/** Service handling users. */",
    )

    assert cls.id == class_id
    assert cls.kind == EntityKind.CLASS
    assert cls.name == "UserService"
    assert cls.qualified_name == "com.example.UserService"
    assert "public" in cls.modifiers
    assert cls.superclass_ref is not None
    assert cls.superclass_ref.target_qualified_name == "com.example.BaseService"
    assert cls.location == loc


@pytest.mark.unit
def test_ir_interface_entity() -> None:
    """Verify Interface entity creation, extends references, and location."""
    file_id = generate_entity_id(EntityKind.FILE, "Repository.ts", "Repository.ts")
    iface_id = generate_entity_id(EntityKind.INTERFACE, "Repository.ts", "Repository")

    loc = SourceLocation(
        file_path="Repository.ts",
        start_line=1,
        start_column=0,
        end_line=10,
        end_column=1,
    )

    extends_ref = Reference(
        id=generate_entity_id(EntityKind.REFERENCE, "Repository.ts", "BaseRepo"),
        ref_kind=ReferenceKind.EXTENDS,
        target_qualified_name="BaseRepo",
    )

    iface = Interface(
        id=iface_id,
        file_id=file_id,
        name="Repository",
        qualified_name="Repository",
        type_parameters=["T"],
        extends_refs=[extends_ref],
        visibility=Visibility.PUBLIC,
        location=loc,
    )

    assert iface.id == iface_id
    assert iface.kind == EntityKind.INTERFACE
    assert iface.name == "Repository"
    assert "T" in iface.type_parameters
    assert len(iface.extends_refs) == 1
    assert iface.extends_refs[0].target_qualified_name == "BaseRepo"


@pytest.mark.unit
def test_ir_function_entity() -> None:
    """Verify Function entity creation for standalone functions."""
    file_id = generate_entity_id(EntityKind.FILE, "helpers.py", "helpers.py")
    fn_id = generate_entity_id(EntityKind.FUNCTION, "helpers.py", "calculate_total")

    param = Parameter(
        id=generate_entity_id(EntityKind.PARAMETER, "helpers.py", "calculate_total.items"),
        name="items",
        declared_type=TypeRepresentation(display_name="List[Item]"),
        position=0,
    )

    fn = Function(
        id=fn_id,
        file_id=file_id,
        name="calculate_total",
        qualified_name="helpers.calculate_total",
        parameters=[param],
        return_type=TypeRepresentation(display_name="int"),
        is_async=True,
    )

    assert fn.id == fn_id
    assert fn.kind == EntityKind.FUNCTION
    assert fn.name == "calculate_total"
    assert fn.is_async is True
    assert len(fn.parameters) == 1
    assert fn.parameters[0].name == "items"
    assert fn.return_type.display_name == "int"  # type: ignore[union-attr]


@pytest.mark.unit
def test_ir_method_entity() -> None:
    """Verify Method entity creation including constructor, static, and abstract flags."""
    file_id = generate_entity_id(EntityKind.FILE, "UserService.java", "UserService.java")
    class_id = generate_entity_id(EntityKind.CLASS, "UserService.java", "UserService")
    method_id = generate_entity_id(EntityKind.METHOD, "UserService.java", "UserService.getUser")

    param = Parameter(
        id=generate_entity_id(EntityKind.PARAMETER, "UserService.java", "getUser.id"),
        name="id",
        declared_type="String",
        position=0,
    )

    method = Method(
        id=method_id,
        file_id=file_id,
        class_id=class_id,
        name="getUser",
        qualified_name="com.example.UserService.getUser",
        parameters=[param],
        return_type="User",
        is_static=False,
        is_constructor=False,
        visibility=Visibility.PUBLIC,
    )

    assert method.id == method_id
    assert method.kind == EntityKind.METHOD
    assert method.class_id == class_id
    assert method.name == "getUser"
    assert method.is_constructor is False
    assert method.parameters[0].name == "id"


@pytest.mark.unit
def test_ir_variable_entity() -> None:
    """Verify Variable entity creation for fields and properties."""
    file_id = generate_entity_id(EntityKind.FILE, "config.py", "config.py")
    var_id = generate_entity_id(EntityKind.VARIABLE, "config.py", "MAX_CONNECTIONS")

    var = Variable(
        id=var_id,
        file_id=file_id,
        name="MAX_CONNECTIONS",
        qualified_name="config.MAX_CONNECTIONS",
        declared_type="int",
        initializer="100",
        is_constant=True,
    )

    assert var.id == var_id
    assert var.kind == EntityKind.VARIABLE
    assert var.name == "MAX_CONNECTIONS"
    assert var.is_constant is True
    assert var.initializer == "100"


@pytest.mark.unit
def test_ir_parameter_entity() -> None:
    """Verify Parameter entity creation and negative position validation."""
    param_id = generate_entity_id(EntityKind.PARAMETER, "service.ts", "getUser.id")
    param = Parameter(
        id=param_id,
        name="id",
        declared_type=TypeRepresentation(display_name="string"),
        position=0,
        is_optional=True,
    )

    assert param.id == param_id
    assert param.kind == EntityKind.PARAMETER
    assert param.name == "id"
    assert param.position == 0
    assert param.is_optional is True

    # Negative position validation failure
    with pytest.raises(ValidationError):
        Parameter(id=param_id, name="id", position=-1)


@pytest.mark.unit
def test_ir_reference_entity() -> None:
    """Verify Reference entity creation with unresolved and resolved target states."""
    ref_id = generate_entity_id(EntityKind.REFERENCE, "main.py", "target_func")
    ref = Reference(
        id=ref_id,
        ref_kind=ReferenceKind.CALL,
        source_symbol_id="caller-id",
        source_file_id="file-id",
        target_qualified_name="services.user.fetch_user",
        target_symbol_id=None,  # Unresolved reference
    )

    assert ref.id == ref_id
    assert ref.kind == EntityKind.REFERENCE
    assert ref.ref_kind == ReferenceKind.CALL
    assert ref.target_qualified_name == "services.user.fetch_user"
    assert ref.target_symbol_id is None  # Unresolved target symbol


@pytest.mark.unit
def test_ir_deterministic_stable_identity() -> None:
    """Verify that logical identity components produce identical IDs across runs."""
    id1 = generate_entity_id(EntityKind.CLASS, "services/user.py", "UserService")
    id2 = generate_entity_id(EntityKind.CLASS, "services/user.py", "UserService")

    assert id1 == id2
    assert isinstance(id1, str)

    # Changing any component produces a different ID
    id_diff_name = generate_entity_id(EntityKind.CLASS, "services/user.py", "UserRepo")
    id_diff_file = generate_entity_id(EntityKind.CLASS, "services/other.py", "UserService")
    id_diff_kind = generate_entity_id(EntityKind.INTERFACE, "services/user.py", "UserService")

    assert id1 != id_diff_name
    assert id1 != id_diff_file
    assert id1 != id_diff_kind


@pytest.mark.unit
def test_ir_serialization_round_trip() -> None:
    """Verify JSON serialization and deserialization round-trip preserving semantic equality."""
    loc = SourceLocation(
        file_path="service.py",
        start_line=1,
        start_column=0,
        end_line=15,
        end_column=5,
    )
    param = Parameter(
        id=generate_entity_id(EntityKind.PARAMETER, "service.py", "fetch.user_id"),
        name="user_id",
        declared_type=TypeRepresentation(display_name="int"),
        position=0,
    )
    fn = Function(
        id=generate_entity_id(EntityKind.FUNCTION, "service.py", "fetch_user"),
        file_id=generate_entity_id(EntityKind.FILE, "service.py", "service.py"),
        name="fetch_user",
        qualified_name="service.fetch_user",
        parameters=[param],
        return_type=TypeRepresentation(display_name="User"),
        is_async=True,
        location=loc,
        doc_comment="Fetch user entity by ID.",
    )

    # Serialize to JSON
    json_str = fn.model_dump_json()
    assert isinstance(json_str, str)
    assert "fetch_user" in json_str

    # Deserialize back from JSON
    restored_fn = Function.model_validate_json(json_str)

    assert restored_fn == fn
    assert restored_fn.id == fn.id
    assert restored_fn.location == loc
    assert restored_fn.parameters[0].name == "user_id"


@pytest.mark.unit
def test_ir_language_neutrality() -> None:
    """Verify Java, Python, and TypeScript constructs map to common canonical IR types."""
    java_class = Class(
        id=generate_entity_id(EntityKind.CLASS, "App.java", "com.example.App"),
        file_id=generate_entity_id(EntityKind.FILE, "App.java", "App.java"),
        name="App",
        qualified_name="com.example.App",
        modifiers=["public"],
    )

    py_class = Class(
        id=generate_entity_id(EntityKind.CLASS, "app.py", "app.App"),
        file_id=generate_entity_id(EntityKind.FILE, "app.py", "app.py"),
        name="App",
        qualified_name="app.App",
    )

    ts_class = Class(
        id=generate_entity_id(EntityKind.CLASS, "app.ts", "App"),
        file_id=generate_entity_id(EntityKind.FILE, "app.ts", "app.ts"),
        name="App",
        qualified_name="App",
        modifiers=["export"],
    )

    # All share exact same canonical Class model type
    assert type(java_class) is type(py_class) is type(ts_class) is Class
    assert java_class.kind == py_class.kind == ts_class.kind == EntityKind.CLASS


@pytest.mark.unit
def test_ir_hierarchy_chain() -> None:
    """Verify parent/container relationships: Repository -> File -> Class -> Method -> Parameter."""
    repo_id = generate_entity_id(EntityKind.REPOSITORY, "", "MyProject")
    file_id = generate_entity_id(EntityKind.FILE, "UserService.java", "UserService.java")
    class_id = generate_entity_id(EntityKind.CLASS, "UserService.java", "UserService")
    method_id = generate_entity_id(EntityKind.METHOD, "UserService.java", "getUser")
    param_id = generate_entity_id(EntityKind.PARAMETER, "UserService.java", "getUser.id")

    repo = Repository(
        id=repo_id,
        name="MyProject",
        root_path="/projects/MyProject",
        files=[file_id],
    )

    file_entity = File(
        id=file_id,
        repository_id=repo.id,
        path="UserService.java",
        language=Language.JAVA,
        symbol_ids=[class_id],
    )

    cls = Class(
        id=class_id,
        file_id=file_entity.id,
        name="UserService",
        qualified_name="com.example.UserService",
        method_ids=[method_id],
    )

    method = Method(
        id=method_id,
        file_id=file_entity.id,
        class_id=cls.id,
        name="getUser",
        qualified_name="com.example.UserService.getUser",
        parameters=[
            Parameter(
                id=param_id,
                parent_callable_id=method_id,
                name="id",
                position=0,
            )
        ],
    )

    # Verify hierarchy containment
    assert repo.files[0] == file_entity.id
    assert file_entity.repository_id == repo.id
    assert cls.file_id == file_entity.id
    assert method.class_id == cls.id
    assert method.parameters[0].parent_callable_id == method.id
