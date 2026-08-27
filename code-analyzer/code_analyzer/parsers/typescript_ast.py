"""Typed AST extraction models and helpers for TypeScript source code."""

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


class TypeScriptParameter(BaseModel):
    """Represents a function or method parameter in TypeScript."""

    model_config = ConfigDict(frozen=True)

    name: str
    type_annotation: str | None = None
    is_optional: bool = False
    location: SourceLocation


class TypeScriptFunction(BaseModel):
    """Represents a function declaration, async function, or method in TypeScript."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_async: bool = False
    is_exported: bool = False
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    parameters: list[TypeScriptParameter] = Field(default_factory=list)
    return_type: str | None = None
    location: SourceLocation


class TypeScriptField(BaseModel):
    """Represents a property or field definition in a class or interface."""

    model_config = ConfigDict(frozen=True)

    name: str
    type_annotation: str | None = None
    modifiers: list[str] = Field(default_factory=list)
    location: SourceLocation


class TypeScriptClass(BaseModel):
    """Represents a TypeScript class declaration."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_exported: bool = False
    modifiers: list[str] = Field(default_factory=list)
    type_parameters: list[str] = Field(default_factory=list)
    extends_clause: str | None = None
    implements_clause: list[str] = Field(default_factory=list)
    methods: list[TypeScriptFunction] = Field(default_factory=list)
    fields: list[TypeScriptField] = Field(default_factory=list)
    constructors: list[TypeScriptFunction] = Field(default_factory=list)
    nested_classes: list["TypeScriptClass"] = Field(default_factory=list)
    location: SourceLocation


class TypeScriptInterface(BaseModel):
    """Represents a TypeScript interface declaration."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_exported: bool = False
    type_parameters: list[str] = Field(default_factory=list)
    extends_clause: str | None = None
    methods: list[TypeScriptFunction] = Field(default_factory=list)
    fields: list[TypeScriptField] = Field(default_factory=list)
    location: SourceLocation


class TypeScriptImport(BaseModel):
    """Represents a TypeScript import statement."""

    model_config = ConfigDict(frozen=True)

    module_path: str
    imported_names: list[str] = Field(default_factory=list)
    alias_map: dict[str, str] = Field(default_factory=dict)
    default_import: str | None = None
    namespace_import: str | None = None
    is_type_only: bool = False
    location: SourceLocation


class TypeScriptExport(BaseModel):
    """Represents a TypeScript export statement or clause."""

    model_config = ConfigDict(frozen=True)

    kind: str
    exported_names: list[str] = Field(default_factory=list)
    alias_map: dict[str, str] = Field(default_factory=dict)
    default_export: str | None = None
    location: SourceLocation


class TypeScriptType(BaseModel):
    """Represents a TypeScript type alias declaration (`type Foo = ...`)."""

    model_config = ConfigDict(frozen=True)

    name: str
    is_exported: bool = False
    type_parameters: list[str] = Field(default_factory=list)
    definition: str
    location: SourceLocation


class TypeScriptStructure(BaseModel):
    """Container holding extracted structural elements from a parsed TypeScript file."""

    model_config = ConfigDict(frozen=True)

    imports: list[TypeScriptImport] = Field(default_factory=list)
    exports: list[TypeScriptExport] = Field(default_factory=list)
    classes: list[TypeScriptClass] = Field(default_factory=list)
    interfaces: list[TypeScriptInterface] = Field(default_factory=list)
    functions: list[TypeScriptFunction] = Field(default_factory=list)
    types: list[TypeScriptType] = Field(default_factory=list)


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
    """Extract modifier keywords (public, private, protected, readonly, static, async, export) from a node."""
    modifiers: list[str] = []
    for child in node.children:
        if child.type in (
            "accessibility_modifier",
            "readonly",
            "static",
            "async",
            "export",
            "declare",
            "abstract",
        ):
            txt = child.text.decode("utf-8").strip()
            if txt and txt not in modifiers:
                modifiers.append(txt)
    return modifiers


def extract_type_parameters(node: Any) -> list[str]:
    """Extract type parameter names from a type_parameters node."""
    type_params_node = None
    for child in node.children:
        if child.type == "type_parameters":
            type_params_node = child
            break

    if not type_params_node:
        return []

    params: list[str] = []
    for child in type_params_node.children:
        if child.type in ("type_parameter", "type_identifier", "identifier"):
            txt = child.text.decode("utf-8").strip()
            if txt:
                params.append(txt)
    return params


def extract_import(node: Any) -> TypeScriptImport | None:
    """Extract TypeScriptImport from import_statement node."""
    module_path = ""
    imported_names: list[str] = []
    alias_map: dict[str, str] = {}
    default_import: str | None = None
    namespace_import: str | None = None
    is_type_only = any(c.type == "type" for c in node.children)

    for child in node.children:
        if child.type == "string":
            raw_path = child.text.decode("utf-8").strip()
            module_path = raw_path.strip("'\"`")

    for child in node.children:
        if child.type == "import_clause":
            for sub in child.children:
                if sub.type == "type":
                    is_type_only = True
                elif sub.type == "identifier":
                    default_import = sub.text.decode("utf-8").strip()
                elif sub.type == "namespace_import":
                    # e.g. * as Utils
                    for ns_child in sub.children:
                        if ns_child.type in ("identifier", "type_identifier"):
                            namespace_import = ns_child.text.decode("utf-8").strip()
                elif sub.type == "named_imports":
                    for spec in sub.children:
                        if spec.type == "import_specifier":
                            spec_children = [
                                x
                                for x in spec.children
                                if x.type
                                in ("identifier", "type_identifier", "property_identifier")
                            ]
                            if len(spec_children) == 1:
                                imported_names.append(spec_children[0].text.decode("utf-8").strip())
                            elif len(spec_children) >= 2:
                                imp_name = spec_children[0].text.decode("utf-8").strip()
                                alias_name = spec_children[-1].text.decode("utf-8").strip()
                                imported_names.append(imp_name)
                                alias_map[imp_name] = alias_name

    if not module_path and not imported_names and not default_import and not namespace_import:
        # Check node text fallback if missing string
        node_txt = node.text.decode("utf-8")
        if "from" in node_txt:
            parts = node_txt.split("from")
            module_path = parts[-1].strip().strip(";").strip("'\"`")

    return TypeScriptImport(
        module_path=module_path,
        imported_names=imported_names,
        alias_map=alias_map,
        default_import=default_import,
        namespace_import=namespace_import,
        is_type_only=is_type_only,
        location=extract_location(node),
    )


def extract_parameter(node: Any) -> TypeScriptParameter | None:
    """Extract TypeScriptParameter from required_parameter, optional_parameter, or field definition parameter."""
    name = ""
    type_annotation: str | None = None
    is_optional = node.type == "optional_parameter"

    for child in node.children:
        if child.type in ("identifier", "property_identifier"):
            name = child.text.decode("utf-8").strip()
        elif child.type == "type_annotation":
            type_annotation = child.text.decode("utf-8").strip()
            if type_annotation.startswith(":"):
                type_annotation = type_annotation[1:].strip()

    if not name:
        txt = node.text.decode("utf-8").strip()
        if ":" in txt:
            parts = txt.split(":", 1)
            name = parts[0].strip("?").strip()
            type_annotation = parts[1].strip()
        else:
            name = txt.strip("?").strip()

    if not name or name in ("(", ")", ","):
        return None

    return TypeScriptParameter(
        name=name,
        type_annotation=type_annotation,
        is_optional=is_optional,
        location=extract_location(node),
    )


def extract_function(node: Any, is_exported: bool = False) -> TypeScriptFunction | None:
    """Extract TypeScriptFunction from function_declaration or method_definition."""
    is_async = any(c.type == "async" for c in node.children)
    modifiers = extract_modifiers(node)
    name = ""
    type_params = extract_type_parameters(node)
    parameters: list[TypeScriptParameter] = []
    return_type: str | None = None

    for child in node.children:
        if child.type in ("identifier", "property_identifier"):
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "formal_parameters":
            for param_node in child.children:
                if param_node.type not in ("(", ")", ","):
                    param = extract_parameter(param_node)
                    if param:
                        parameters.append(param)
        elif child.type == "type_annotation":
            txt = child.text.decode("utf-8").strip()
            if txt.startswith(":"):
                txt = txt[1:].strip()
            return_type = txt

    return TypeScriptFunction(
        name=name,
        is_async=is_async,
        is_exported=is_exported,
        modifiers=modifiers,
        type_parameters=type_params,
        parameters=parameters,
        return_type=return_type,
        location=extract_location(node),
    )


def extract_field(node: Any) -> TypeScriptField | None:
    """Extract TypeScriptField from property_definition, field_definition, or property_signature."""
    name = ""
    type_annotation: str | None = None
    modifiers = extract_modifiers(node)

    for child in node.children:
        if child.type in ("property_identifier", "identifier"):
            name = child.text.decode("utf-8").strip()
        elif child.type == "type_annotation":
            txt = child.text.decode("utf-8").strip()
            if txt.startswith(":"):
                txt = txt[1:].strip()
            type_annotation = txt

    if not name:
        return None

    return TypeScriptField(
        name=name,
        type_annotation=type_annotation,
        modifiers=modifiers,
        location=extract_location(node),
    )


def extract_type_alias(node: Any, is_exported: bool = False) -> TypeScriptType | None:
    """Extract TypeScriptType from type_alias_declaration."""
    name = ""
    type_params = extract_type_parameters(node)
    definition = ""

    for child in node.children:
        if child.type in ("type_identifier", "identifier"):
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    # Definition is the expression after '='
    found_eq = False
    def_parts: list[str] = []
    for child in node.children:
        if child.type == "=":
            found_eq = True
        elif found_eq and child.type != ";":
            def_parts.append(child.text.decode("utf-8").strip())

    definition = " ".join(def_parts).strip()

    return TypeScriptType(
        name=name,
        is_exported=is_exported,
        type_parameters=type_params,
        definition=definition,
        location=extract_location(node),
    )


def extract_class(node: Any, is_exported: bool = False) -> TypeScriptClass | None:
    """Extract TypeScriptClass from class_declaration."""
    name = ""
    modifiers = extract_modifiers(node)
    type_params = extract_type_parameters(node)
    extends_clause: str | None = None
    implements_clause: list[str] = []

    for child in node.children:
        if child.type in ("type_identifier", "identifier"):
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "class_heritage":
            for h_child in child.children:
                if h_child.type == "extends_clause":
                    txt = h_child.text.decode("utf-8").strip()
                    if txt.startswith("extends "):
                        txt = txt[8:].strip()
                    extends_clause = txt
                elif h_child.type == "implements_clause":
                    txt = h_child.text.decode("utf-8").strip()
                    if txt.startswith("implements "):
                        txt = txt[11:].strip()
                    implements_clause = [iface.strip() for iface in txt.split(",") if iface.strip()]

    methods: list[TypeScriptFunction] = []
    fields: list[TypeScriptField] = []
    constructors: list[TypeScriptFunction] = []
    nested_classes: list[TypeScriptClass] = []

    body_node = None
    for child in node.children:
        if child.type == "class_body":
            body_node = child
            break

    if body_node:
        for child in body_node.children:
            if child.type == "method_definition":
                m_name = ""
                for mc in child.children:
                    if mc.type in ("property_identifier", "identifier"):
                        m_name = mc.text.decode("utf-8").strip()
                        break
                if m_name == "constructor":
                    ctor = extract_function(child, is_exported=False)
                    if ctor:
                        constructors.append(ctor)
                else:
                    m = extract_function(child, is_exported=False)
                    if m:
                        methods.append(m)
            elif child.type in (
                "public_field_definition",
                "field_definition",
                "property_definition",
            ):
                f = extract_field(child)
                if f:
                    fields.append(f)
            elif child.type == "class_declaration":
                nested = extract_class(child, is_exported=False)
                if nested:
                    nested_classes.append(nested)

    return TypeScriptClass(
        name=name,
        is_exported=is_exported,
        modifiers=modifiers,
        type_parameters=type_params,
        extends_clause=extends_clause,
        implements_clause=implements_clause,
        methods=methods,
        fields=fields,
        constructors=constructors,
        nested_classes=nested_classes,
        location=extract_location(node),
    )


def extract_interface(node: Any, is_exported: bool = False) -> TypeScriptInterface | None:
    """Extract TypeScriptInterface from interface_declaration."""
    name = ""
    type_params = extract_type_parameters(node)
    extends_clause: str | None = None

    for child in node.children:
        if child.type in ("type_identifier", "identifier"):
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "extends_clause":
            txt = child.text.decode("utf-8").strip()
            if txt.startswith("extends "):
                txt = txt[8:].strip()
            extends_clause = txt

    methods: list[TypeScriptFunction] = []
    fields: list[TypeScriptField] = []

    body_node = None
    for child in node.children:
        if child.type in ("interface_body", "object_type"):
            body_node = child
            break

    if body_node:
        for child in body_node.children:
            if child.type == "method_signature":
                m = extract_function(child, is_exported=False)
                if m:
                    methods.append(m)
            elif child.type == "property_signature":
                f = extract_field(child)
                if f:
                    fields.append(f)

    return TypeScriptInterface(
        name=name,
        is_exported=is_exported,
        type_parameters=type_params,
        extends_clause=extends_clause,
        methods=methods,
        fields=fields,
        location=extract_location(node),
    )


def extract_export(node: Any) -> TypeScriptExport | None:
    """Extract TypeScriptExport from export_statement."""
    exported_names: list[str] = []
    alias_map: dict[str, str] = {}
    default_export: str | None = None
    kind = "named"

    is_default = any(c.type == "default" for c in node.children)

    if is_default:
        kind = "default"
        for child in node.children:
            if child.type not in ("export", "default", ";"):
                default_export = child.text.decode("utf-8").strip()
    else:
        for child in node.children:
            if child.type == "export_clause":
                for spec in child.children:
                    if spec.type == "export_specifier":
                        spec_children = [
                            x
                            for x in spec.children
                            if x.type in ("identifier", "type_identifier", "property_identifier")
                        ]
                        if len(spec_children) == 1:
                            exported_names.append(spec_children[0].text.decode("utf-8").strip())
                        elif len(spec_children) >= 2:
                            exp_name = spec_children[0].text.decode("utf-8").strip()
                            alias_name = spec_children[-1].text.decode("utf-8").strip()
                            exported_names.append(exp_name)
                            alias_map[exp_name] = alias_name
            elif child.type in (
                "class_declaration",
                "interface_declaration",
                "function_declaration",
                "type_alias_declaration",
            ):
                for sub in child.children:
                    if sub.type in ("identifier", "type_identifier"):
                        exported_names.append(sub.text.decode("utf-8").strip())
                        break

    return TypeScriptExport(
        kind=kind,
        exported_names=exported_names,
        alias_map=alias_map,
        default_export=default_export,
        location=extract_location(node),
    )


def extract_typescript_structure(root_node: Any) -> TypeScriptStructure:
    """Walk root node of TypeScript AST and extract structural elements."""
    imports: list[TypeScriptImport] = []
    exports: list[TypeScriptExport] = []
    classes: list[TypeScriptClass] = []
    interfaces: list[TypeScriptInterface] = []
    functions: list[TypeScriptFunction] = []
    types: list[TypeScriptType] = []

    for child in root_node.children:
        if child.type == "import_statement":
            imp = extract_import(child)
            if imp:
                imports.append(imp)
        elif child.type == "export_statement":
            exp = extract_export(child)
            if exp:
                exports.append(exp)

            # Also extract the declaration wrapped by export_statement
            for inner in child.children:
                if inner.type == "class_declaration":
                    cls = extract_class(inner, is_exported=True)
                    if cls:
                        classes.append(cls)
                elif inner.type == "interface_declaration":
                    iface = extract_interface(inner, is_exported=True)
                    if iface:
                        interfaces.append(iface)
                elif inner.type == "function_declaration":
                    fn = extract_function(inner, is_exported=True)
                    if fn:
                        functions.append(fn)
                elif inner.type == "type_alias_declaration":
                    t = extract_type_alias(inner, is_exported=True)
                    if t:
                        types.append(t)
        elif child.type == "class_declaration":
            cls = extract_class(child, is_exported=False)
            if cls:
                classes.append(cls)
        elif child.type == "interface_declaration":
            iface = extract_interface(child, is_exported=False)
            if iface:
                interfaces.append(iface)
        elif child.type == "function_declaration":
            fn = extract_function(child, is_exported=False)
            if fn:
                functions.append(fn)
        elif child.type == "type_alias_declaration":
            t = extract_type_alias(child, is_exported=False)
            if t:
                types.append(t)

    return TypeScriptStructure(
        imports=imports,
        exports=exports,
        classes=classes,
        interfaces=interfaces,
        functions=functions,
        types=types,
    )
