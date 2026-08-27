"""Typed AST extraction models and helpers for Java source code."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceLocation(BaseModel):
    """Represents line and column range in source code.

    Lines are 1-indexed; columns are 0-indexed.
    """

    model_config = ConfigDict(frozen=True)

    start_line: int
    start_column: int
    end_line: int
    end_column: int


class JavaPackage(BaseModel):
    """Represents a Java package declaration."""

    model_config = ConfigDict(frozen=True)

    name: str
    location: SourceLocation


class JavaImport(BaseModel):
    """Represents a Java import declaration."""

    model_config = ConfigDict(frozen=True)

    path: str
    is_static: bool = False
    is_wildcard: bool = False
    location: SourceLocation


class JavaParameter(BaseModel):
    """Represents a formal parameter in a Java method or constructor."""

    model_config = ConfigDict(frozen=True)

    name: str
    type_name: str
    modifiers: list[str] = Field(default_factory=list)
    location: SourceLocation


class JavaMethod(BaseModel):
    """Represents a method or constructor declaration in a Java class/interface."""

    model_config = ConfigDict(frozen=True)

    name: str
    return_type: str | None = None
    is_constructor: bool = False
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    parameters: list[JavaParameter] = Field(default_factory=list)
    location: SourceLocation


class JavaField(BaseModel):
    """Represents a field/variable declaration in a Java class or interface."""

    model_config = ConfigDict(frozen=True)

    name: str
    type_name: str
    modifiers: list[str] = Field(default_factory=list)
    location: SourceLocation


class JavaClass(BaseModel):
    """Represents a Java class, interface, enum, or record declaration."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_interface: bool = False
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    extends_clause: str | None = None
    implements_clause: list[str] = Field(default_factory=list)
    methods: list[JavaMethod] = Field(default_factory=list)
    fields: list[JavaField] = Field(default_factory=list)
    nested_classes: list["JavaClass"] = Field(default_factory=list)
    location: SourceLocation


class JavaStructure(BaseModel):
    """Container holding extracted structural elements from a parsed Java file."""

    model_config = ConfigDict(frozen=True)

    package: JavaPackage | None = None
    imports: list[JavaImport] = Field(default_factory=list)
    classes: list[JavaClass] = Field(default_factory=list)


def extract_location(node: Any) -> SourceLocation:
    """Extract SourceLocation (1-indexed lines, 0-indexed columns) from a Tree-sitter node."""
    start_pt = node.start_point
    end_pt = node.end_point
    return SourceLocation(
        start_line=start_pt[0] + 1,
        start_column=start_pt[1],
        end_line=end_pt[0] + 1,
        end_column=end_pt[1],
    )


def extract_modifiers(node: Any) -> list[str]:
    """Extract modifier keywords (public, static, final, etc.) from a declaration node."""
    modifiers_node = None
    for child in node.children:
        if child.type == "modifiers":
            modifiers_node = child
            break

    if not modifiers_node:
        return []

    result: list[str] = []
    for child in modifiers_node.children:
        if child.type not in ("marker_annotation", "annotation"):
            txt = child.text.decode("utf-8").strip()
            if txt:
                result.append(txt)
    return result


def extract_type_parameters(node: Any) -> list[str]:
    """Extract generic type parameter names from a type_parameters node."""
    type_params_node = None
    for child in node.children:
        if child.type == "type_parameters":
            type_params_node = child
            break

    if not type_params_node:
        return []

    params: list[str] = []
    for child in type_params_node.children:
        if child.type in ("type_parameter", "identifier"):
            txt = child.text.decode("utf-8").strip()
            if txt:
                params.append(txt)
    return params


def extract_package(node: Any) -> JavaPackage | None:
    """Extract package declaration from package_declaration node."""
    for child in node.children:
        if child.type in ("scoped_identifier", "identifier"):
            pkg_name = child.text.decode("utf-8").strip()
            return JavaPackage(
                name=pkg_name,
                location=extract_location(node),
            )
    return None


def extract_import(node: Any) -> JavaImport | None:
    """Extract import declaration from import_declaration node."""
    is_static = False
    is_wildcard = False
    path = ""

    node_text = node.text.decode("utf-8")
    if "static " in node_text:
        is_static = True

    for child in node.children:
        if child.type == "static":
            is_static = True
        elif child.type == "asterisk":
            is_wildcard = True
        elif child.type in ("scoped_identifier", "identifier"):
            path = child.text.decode("utf-8").strip()

    if node_text.strip().endswith(".*;") or node_text.strip().endswith(".*"):
        is_wildcard = True
        if not path.endswith(".*"):
            path += ".*"

    if not path:
        return None

    return JavaImport(
        path=path,
        is_static=is_static,
        is_wildcard=is_wildcard,
        location=extract_location(node),
    )


def extract_parameter(node: Any) -> JavaParameter | None:
    """Extract JavaParameter from formal_parameter or spread_parameter node."""
    name = ""
    type_name = ""
    modifiers = extract_modifiers(node)

    for child in node.children:
        if child.type == "identifier":
            name = child.text.decode("utf-8").strip()
        elif child.type not in ("modifiers", ";"):
            type_name = child.text.decode("utf-8").strip()

    if not name:
        return None

    return JavaParameter(
        name=name,
        type_name=type_name,
        modifiers=modifiers,
        location=extract_location(node),
    )


def extract_method(node: Any) -> JavaMethod | None:
    """Extract JavaMethod from method_declaration or constructor_declaration node."""
    is_constructor = node.type == "constructor_declaration"
    name = ""
    return_type = None
    modifiers = extract_modifiers(node)
    type_params = extract_type_parameters(node)
    parameters: list[JavaParameter] = []

    identifier_node = None
    for child in node.children:
        if child.type == "identifier":
            identifier_node = child
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    if not is_constructor and identifier_node:
        # Return type is the node right before identifier (and after modifiers/type_parameters)
        return_type_nodes = [
            c
            for c in node.children
            if c.type not in ("modifiers", "type_parameters", "formal_parameters", "block", ";")
            and c != identifier_node
            and c.end_point <= identifier_node.start_point
        ]
        if return_type_nodes:
            return_type = return_type_nodes[-1].text.decode("utf-8").strip()

    for child in node.children:
        if child.type == "formal_parameters":
            for param_node in child.children:
                if param_node.type in ("formal_parameter", "spread_parameter"):
                    param = extract_parameter(param_node)
                    if param:
                        parameters.append(param)

    return JavaMethod(
        name=name,
        return_type=return_type,
        is_constructor=is_constructor,
        modifiers=modifiers,
        type_parameters=type_params,
        parameters=parameters,
        location=extract_location(node),
    )


def extract_fields(node: Any) -> list[JavaField]:
    """Extract JavaField list from a field_declaration node."""
    modifiers = extract_modifiers(node)
    type_node = None
    declarators: list[Any] = []

    for child in node.children:
        if child.type == "variable_declarator":
            declarators.append(child)
        elif child.type not in ("modifiers", ";") and type_node is None:
            type_node = child

    if not type_node or not declarators:
        return []

    type_name = type_node.text.decode("utf-8").strip()
    fields: list[JavaField] = []

    for decl in declarators:
        name = ""
        for c in decl.children:
            if c.type in ("identifier", "variable_declarator_id"):
                name = c.text.decode("utf-8").strip()
                break
        if name:
            fields.append(
                JavaField(
                    name=name,
                    type_name=type_name,
                    modifiers=modifiers,
                    location=extract_location(node),
                )
            )

    return fields


def extract_class_or_interface(node: Any) -> JavaClass | None:
    """Extract JavaClass from class_declaration, interface_declaration, enum_declaration, etc."""
    is_interface = node.type in ("interface_declaration", "annotation_type_declaration")
    name = ""
    modifiers = extract_modifiers(node)
    type_params = extract_type_parameters(node)
    extends_clause = None
    implements_clause: list[str] = []

    for child in node.children:
        if child.type in ("identifier", "type_identifier"):
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "superclass" or (child.type == "extends_interfaces" and is_interface):
            txt = child.text.decode("utf-8").strip()
            if txt.startswith("extends "):
                txt = txt[8:].strip()
            extends_clause = txt
        elif child.type == "super_interfaces":
            txt = child.text.decode("utf-8").strip()
            if txt.startswith("implements "):
                txt = txt[11:].strip()
            implements_clause = [iface.strip() for iface in txt.split(",") if iface.strip()]

    methods: list[JavaMethod] = []
    fields: list[JavaField] = []
    nested_classes: list[JavaClass] = []

    body_node = None
    for child in node.children:
        if child.type in ("class_body", "interface_body", "enum_body_declarations"):
            body_node = child
            break

    if body_node:
        for child in body_node.children:
            if child.type in ("method_declaration", "constructor_declaration"):
                m = extract_method(child)
                if m:
                    methods.append(m)
            elif child.type == "field_declaration":
                f_list = extract_fields(child)
                fields.extend(f_list)
            elif child.type in (
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
                "annotation_type_declaration",
            ):
                nested = extract_class_or_interface(child)
                if nested:
                    nested_classes.append(nested)

    return JavaClass(
        name=name,
        is_interface=is_interface,
        modifiers=modifiers,
        type_parameters=type_params,
        extends_clause=extends_clause,
        implements_clause=implements_clause,
        methods=methods,
        fields=fields,
        nested_classes=nested_classes,
        location=extract_location(node),
    )


def extract_java_structure(root_node: Any) -> JavaStructure:
    """Walk root node of Java AST and extract all structural elements."""
    package: JavaPackage | None = None
    imports: list[JavaImport] = []
    classes: list[JavaClass] = []

    for child in root_node.children:
        if child.type == "package_declaration":
            pkg = extract_package(child)
            if pkg:
                package = pkg
        elif child.type == "import_declaration":
            imp = extract_import(child)
            if imp:
                imports.append(imp)
        elif child.type in (
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
            "annotation_type_declaration",
        ):
            cls = extract_class_or_interface(child)
            if cls:
                classes.append(cls)

    return JavaStructure(
        package=package,
        imports=imports,
        classes=classes,
    )
