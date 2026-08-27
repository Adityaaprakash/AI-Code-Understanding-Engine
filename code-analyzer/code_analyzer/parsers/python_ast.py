"""Typed AST extraction models and helpers for Python source code."""

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


class PythonDecorator(BaseModel):
    """Represents a Python decorator expression."""

    model_config = ConfigDict(frozen=True)

    expression: str
    location: SourceLocation


class PythonParameter(BaseModel):
    """Represents a function parameter in Python."""

    model_config = ConfigDict(frozen=True)

    name: str
    annotation: str | None = None
    default_value: str | None = None
    location: SourceLocation


class PythonFunction(BaseModel):
    """Represents a function or method definition in Python."""

    model_config = ConfigDict(frozen=True)

    name: str
    parameters: list[PythonParameter] = Field(default_factory=list)
    return_type: str | None = None
    decorators: list[PythonDecorator] = Field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    nested_functions: list["PythonFunction"] = Field(default_factory=list)
    nested_classes: list["PythonClass"] = Field(default_factory=list)
    location: SourceLocation


class PythonField(BaseModel):
    """Represents a class-level variable assignment or annotated attribute."""

    model_config = ConfigDict(frozen=True)

    name: str
    annotation: str | None = None
    value: str | None = None
    location: SourceLocation


class PythonClass(BaseModel):
    """Represents a Python class definition."""

    model_config = ConfigDict(frozen=True)

    name: str
    bases: list[str] = Field(default_factory=list)
    decorators: list[PythonDecorator] = Field(default_factory=list)
    methods: list[PythonFunction] = Field(default_factory=list)
    fields: list[PythonField] = Field(default_factory=list)
    nested_classes: list["PythonClass"] = Field(default_factory=list)
    location: SourceLocation


class PythonImport(BaseModel):
    """Represents a Python import statement (import or from-import)."""

    model_config = ConfigDict(frozen=True)

    module: str | None = None
    names: list[str] = Field(default_factory=list)
    alias_map: dict[str, str] = Field(default_factory=dict)
    is_from_import: bool = False
    location: SourceLocation


class PythonModule(BaseModel):
    """Container holding extracted structural elements from a parsed Python file."""

    model_config = ConfigDict(frozen=True)

    imports: list[PythonImport] = Field(default_factory=list)
    classes: list[PythonClass] = Field(default_factory=list)
    functions: list[PythonFunction] = Field(default_factory=list)


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


def extract_decorator(node: Any) -> PythonDecorator | None:
    """Extract PythonDecorator from a decorator node."""
    txt = node.text.decode("utf-8").strip()
    if txt.startswith("@"):
        expression = txt[1:].strip()
    else:
        expression = txt
    return PythonDecorator(
        expression=expression,
        location=extract_location(node),
    )


def extract_import(node: Any) -> PythonImport | None:
    """Extract PythonImport from import_statement or import_from_statement."""
    is_from = node.type == "import_from_statement"
    module: str | None = None
    names: list[str] = []
    alias_map: dict[str, str] = {}

    if is_from:
        import_seen = False
        for child in node.children:
            if child.type == "import":
                import_seen = True
                continue

            if not import_seen:
                if child.type in ("dotted_name", "relative_import", "identifier", "import_prefix"):
                    txt = child.text.decode("utf-8").strip()
                    module = (module or "") + txt
            else:
                if child.type == "aliased_import":
                    name_node = child.children[0]
                    alias_node = child.children[-1]
                    imp_name = name_node.text.decode("utf-8").strip()
                    alias_name = alias_node.text.decode("utf-8").strip()
                    names.append(imp_name)
                    alias_map[imp_name] = alias_name
                elif child.type in ("dotted_name", "identifier"):
                    txt = child.text.decode("utf-8").strip()
                    if txt:
                        names.append(txt)
                elif child.type == "wildcard_import" or child.text == b"*":
                    names.append("*")
    else:
        for child in node.children:
            if child.type == "dotted_name":
                names.append(child.text.decode("utf-8").strip())
            elif child.type == "aliased_import":
                name_node = child.children[0]
                alias_node = child.children[-1]
                imp_name = name_node.text.decode("utf-8").strip()
                alias_name = alias_node.text.decode("utf-8").strip()
                names.append(imp_name)
                alias_map[imp_name] = alias_name

    if not names and not module:
        return None

    return PythonImport(
        module=module,
        names=names,
        alias_map=alias_map,
        is_from_import=is_from,
        location=extract_location(node),
    )


def extract_parameter(node: Any) -> PythonParameter | None:
    """Extract PythonParameter from formal parameter node."""
    name = ""
    annotation: str | None = None
    default_value: str | None = None

    if node.type == "identifier" or node.type in ("list_splat_pattern", "dictionary_splat_pattern"):
        name = node.text.decode("utf-8").strip()
    elif node.type == "typed_parameter":
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8").strip()
            elif child.type not in (":", "identifier"):
                annotation = child.text.decode("utf-8").strip()
    elif node.type == "default_parameter":
        for child in node.children:
            if child.type == "identifier" and not name:
                name = child.text.decode("utf-8").strip()
            elif child.type not in ("=", "identifier"):
                default_value = child.text.decode("utf-8").strip()
    elif node.type == "typed_default_parameter":
        parts = [c for c in node.children if c.type not in (":", "=")]
        if len(parts) >= 1:
            name = parts[0].text.decode("utf-8").strip()
        if len(parts) >= 2:
            annotation = parts[1].text.decode("utf-8").strip()
        if len(parts) >= 3:
            default_value = parts[2].text.decode("utf-8").strip()

    if not name:
        return None

    return PythonParameter(
        name=name,
        annotation=annotation,
        default_value=default_value,
        location=extract_location(node),
    )


def extract_function(
    node: Any, decorators: list[PythonDecorator] | None = None, is_method: bool = False
) -> PythonFunction | None:
    """Extract PythonFunction from function_definition or async_function_definition node."""
    if decorators is None:
        decorators = []

    is_async = node.type == "async_function_definition" or any(
        c.type == "async" for c in node.children
    )
    name = ""
    parameters: list[PythonParameter] = []
    return_type: str | None = None

    for child in node.children:
        if child.type == "identifier":
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "parameters":
            for param_node in child.children:
                if param_node.type not in ("(", ")", ","):
                    param = extract_parameter(param_node)
                    if param:
                        parameters.append(param)
        elif child.type == "type":
            return_type = child.text.decode("utf-8").strip()

    nested_functions: list[PythonFunction] = []
    nested_classes: list[PythonClass] = []

    body_node = None
    for child in node.children:
        if child.type == "block":
            body_node = child
            break

    if body_node:
        _extract_block_contents(
            body_node,
            functions=nested_functions,
            classes=nested_classes,
            fields=None,
            is_inside_class=False,
        )

    return PythonFunction(
        name=name,
        parameters=parameters,
        return_type=return_type,
        decorators=decorators,
        is_async=is_async,
        is_method=is_method,
        nested_functions=nested_functions,
        nested_classes=nested_classes,
        location=extract_location(node),
    )


def extract_class(node: Any, decorators: list[PythonDecorator] | None = None) -> PythonClass | None:
    """Extract PythonClass from class_definition node."""
    if decorators is None:
        decorators = []

    name = ""
    bases: list[str] = []

    for child in node.children:
        if child.type == "identifier":
            name = child.text.decode("utf-8").strip()
            break

    if not name:
        return None

    for child in node.children:
        if child.type == "argument_list":
            for arg in child.children:
                if arg.type not in ("(", ")", ","):
                    txt = arg.text.decode("utf-8").strip()
                    if txt:
                        bases.append(txt)

    methods: list[PythonFunction] = []
    fields: list[PythonField] = []
    nested_classes: list[PythonClass] = []

    body_node = None
    for child in node.children:
        if child.type == "block":
            body_node = child
            break

    if body_node:
        _extract_block_contents(
            body_node,
            functions=methods,
            classes=nested_classes,
            fields=fields,
            is_inside_class=True,
        )

    return PythonClass(
        name=name,
        bases=bases,
        decorators=decorators,
        methods=methods,
        fields=fields,
        nested_classes=nested_classes,
        location=extract_location(node),
    )


def _extract_block_contents(
    block_node: Any,
    functions: list[PythonFunction],
    classes: list[PythonClass],
    fields: list[PythonField] | None = None,
    is_inside_class: bool = False,
) -> None:
    """Helper to process statements inside a block node."""
    i = 0
    children = block_node.children
    n = len(children)

    while i < n:
        child = children[i]

        if child.type == "decorated_definition":
            dec_list: list[PythonDecorator] = []
            def_node = None
            for sub in child.children:
                if sub.type == "decorator":
                    dec = extract_decorator(sub)
                    if dec:
                        dec_list.append(dec)
                elif sub.type in (
                    "function_definition",
                    "async_function_definition",
                    "class_definition",
                ):
                    def_node = sub

            if def_node:
                if def_node.type in ("function_definition", "async_function_definition"):
                    fn = extract_function(def_node, decorators=dec_list, is_method=is_inside_class)
                    if fn:
                        functions.append(fn)
                elif def_node.type == "class_definition":
                    cls = extract_class(def_node, decorators=dec_list)
                    if cls:
                        classes.append(cls)

        elif child.type in ("function_definition", "async_function_definition"):
            fn = extract_function(child, is_method=is_inside_class)
            if fn:
                functions.append(fn)

        elif child.type == "class_definition":
            cls = extract_class(child)
            if cls:
                classes.append(cls)

        elif child.type == "expression_statement" and fields is not None and is_inside_class:
            for sub in child.children:
                if sub.type == "assignment":
                    left = sub.children[0]
                    right = sub.children[-1]
                    name = left.text.decode("utf-8").strip()
                    val = right.text.decode("utf-8").strip() if len(sub.children) > 2 else None
                    fields.append(
                        PythonField(
                            name=name,
                            annotation=None,
                            value=val,
                            location=extract_location(sub),
                        )
                    )
                elif sub.type == "type_alias":
                    left = sub.children[0]
                    name = left.text.decode("utf-8").strip()
                    fields.append(
                        PythonField(
                            name=name,
                            annotation=None,
                            value=None,
                            location=extract_location(sub),
                        )
                    )

        i += 1


def extract_python_module(root_node: Any) -> PythonModule:
    """Walk root module node of Python AST and extract structural elements."""
    imports: list[PythonImport] = []
    classes: list[PythonClass] = []
    functions: list[PythonFunction] = []

    for child in root_node.children:
        if child.type in ("import_statement", "import_from_statement"):
            imp = extract_import(child)
            if imp:
                imports.append(imp)
        elif child.type == "decorated_definition":
            dec_list: list[PythonDecorator] = []
            def_node = None
            for sub in child.children:
                if sub.type == "decorator":
                    dec = extract_decorator(sub)
                    if dec:
                        dec_list.append(dec)
                elif sub.type in (
                    "function_definition",
                    "async_function_definition",
                    "class_definition",
                ):
                    def_node = sub

            if def_node:
                if def_node.type in ("function_definition", "async_function_definition"):
                    fn = extract_function(def_node, decorators=dec_list, is_method=False)
                    if fn:
                        functions.append(fn)
                elif def_node.type == "class_definition":
                    cls = extract_class(def_node, decorators=dec_list)
                    if cls:
                        classes.append(cls)
        elif child.type in ("function_definition", "async_function_definition"):
            fn = extract_function(child, is_method=False)
            if fn:
                functions.append(fn)
        elif child.type == "class_definition":
            cls = extract_class(child)
            if cls:
                classes.append(cls)

    return PythonModule(
        imports=imports,
        classes=classes,
        functions=functions,
    )
