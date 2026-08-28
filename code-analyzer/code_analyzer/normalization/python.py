"""Python AST to Canonical Code IR normalizer."""

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
    Function,
    Method,
    Module,
    Parameter,
    Reference,
    ReferenceKind,
    Symbol,
    Variable,
    generate_entity_id,
)
from code_analyzer.normalization.base import ASTNormalizer
from code_analyzer.normalization.location_helper import to_ir_source_location
from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.normalization.type_helper import parse_type_representation
from code_analyzer.parsers.models import Language
from code_analyzer.parsers.python_ast import PythonClass, PythonField, PythonFunction, PythonModule


def _file_path_to_module_qname(file_path: str) -> str:
    """Derive Python module qualified name from file path (e.g. services/user.py -> services.user)."""
    norm_path = file_path.replace("\\", "/").strip("/")
    if norm_path.endswith(".py"):
        norm_path = norm_path[:-3]
    if norm_path.endswith("/__init__"):
        norm_path = norm_path[:-9]
    parts = [p for p in norm_path.split("/") if p and p != "."]
    return ".".join(parts) if parts else "module"


class PythonNormalizer(ASTNormalizer[PythonModule]):
    """Normalizes PythonModule AST models into Canonical Code IR."""

    def normalize(
        self,
        ast: PythonModule,
        repository_id: str,
        file_path: str,
        language: Language = Language.PYTHON,
        content_hash: str | None = None,
        loc: int = 0,
    ) -> NormalizationResult:
        """Normalize PythonModule into a canonical NormalizationResult."""
        file_id = generate_entity_id(EntityKind.FILE, file_path, file_path, parent_id=repository_id)

        modules: list[Module] = []
        classes: list[Class] = []
        functions: list[Function] = []
        methods: list[Method] = []
        variables: list[Variable] = []
        parameters: list[Parameter] = []
        references: list[Reference] = []
        symbols: list[Symbol] = []
        symbol_ids: list[str] = []
        reference_ids: list[str] = []
        module_ids: list[str] = []

        mod_qname = _file_path_to_module_qname(file_path)
        mod_name = mod_qname.split(".")[-1]
        mod_id = generate_entity_id(EntityKind.MODULE, file_path, mod_qname, parent_id=file_id)
        module_ids.append(mod_id)

        modules.append(
            Module(
                id=mod_id,
                file_id=file_id,
                name=mod_name,
                qualified_name=mod_qname,
            )
        )

        # Normalize imports
        for imp in ast.imports:
            ref_loc = to_ir_source_location(imp.location, file_path)
            loc_key = f"{ref_loc.start_line}:{ref_loc.start_column}" if ref_loc else ""

            if imp.is_from_import and imp.module:
                for name in imp.names:
                    imp_target = f"{imp.module}.{name}"
                    ref_id = generate_entity_id(
                        EntityKind.REFERENCE,
                        file_path,
                        imp_target,
                        parent_id=file_id,
                        location_str=loc_key,
                    )
                    reference_ids.append(ref_id)
                    references.append(
                        Reference(
                            id=ref_id,
                            ref_kind=ReferenceKind.IMPORT,
                            source_file_id=file_id,
                            source_location=ref_loc,
                            target_qualified_name=imp_target,
                        )
                    )
            else:
                for name in imp.names:
                    ref_id = generate_entity_id(
                        EntityKind.REFERENCE,
                        file_path,
                        name,
                        parent_id=file_id,
                        location_str=loc_key,
                    )
                    reference_ids.append(ref_id)
                    references.append(
                        Reference(
                            id=ref_id,
                            ref_kind=ReferenceKind.IMPORT,
                            source_file_id=file_id,
                            source_location=ref_loc,
                            target_qualified_name=name,
                        )
                    )

        # Normalize module-level functions
        def process_function_node(
            fn_ast: PythonFunction, parent_qname: str, parent_id: str, is_inside_class: bool
        ) -> str:
            fn_qname = f"{parent_qname}.{fn_ast.name}" if parent_qname else fn_ast.name
            fn_loc = to_ir_source_location(fn_ast.location, file_path)

            dec_exprs = [d.expression for d in fn_ast.decorators]
            is_static_dec = "staticmethod" in dec_exprs or "classmethod" in dec_exprs

            if is_inside_class or fn_ast.is_method:
                m_id = generate_entity_id(
                    EntityKind.METHOD, file_path, fn_qname, parent_id=parent_id
                )
                symbol_ids.append(m_id)

                param_entities: list[Parameter] = []
                for idx, p_ast in enumerate(fn_ast.parameters):
                    p_qname = f"{fn_qname}.{p_ast.name}"
                    p_loc = to_ir_source_location(p_ast.location, file_path)
                    p_id = generate_entity_id(
                        EntityKind.PARAMETER, file_path, p_qname, parent_id=m_id
                    )
                    param_entity = Parameter(
                        id=p_id,
                        parent_callable_id=m_id,
                        name=p_ast.name,
                        declared_type=parse_type_representation(p_ast.annotation),
                        default_value=p_ast.default_value,
                        position=idx,
                        location=p_loc,
                    )
                    param_entities.append(param_entity)
                    parameters.append(param_entity)

                metadata_dict = {"decorators": dec_exprs} if dec_exprs else {}

                methods.append(
                    Method(
                        id=m_id,
                        file_id=file_id,
                        class_id=parent_id,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        parameters=param_entities,
                        return_type=parse_type_representation(fn_ast.return_type),
                        is_async=fn_ast.is_async,
                        is_static=is_static_dec,
                        is_constructor=fn_ast.name == "__init__",
                        location=fn_loc,
                        metadata=metadata_dict,
                    )
                )

                symbols.append(
                    Symbol(
                        id=m_id,
                        symbol_kind=EntityKind.METHOD,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        language=Language.PYTHON,
                        file_id=file_id,
                        location=fn_loc,
                    )
                )
                return m_id
            else:
                f_id = generate_entity_id(
                    EntityKind.FUNCTION, file_path, fn_qname, parent_id=parent_id
                )
                symbol_ids.append(f_id)

                param_entities = []
                for idx, p_ast in enumerate(fn_ast.parameters):
                    p_qname = f"{fn_qname}.{p_ast.name}"
                    p_loc = to_ir_source_location(p_ast.location, file_path)
                    p_id = generate_entity_id(
                        EntityKind.PARAMETER, file_path, p_qname, parent_id=f_id
                    )
                    param_entity = Parameter(
                        id=p_id,
                        parent_callable_id=f_id,
                        name=p_ast.name,
                        declared_type=parse_type_representation(p_ast.annotation),
                        default_value=p_ast.default_value,
                        position=idx,
                        location=p_loc,
                    )
                    param_entities.append(param_entity)
                    parameters.append(param_entity)

                metadata_dict = {"decorators": dec_exprs} if dec_exprs else {}

                functions.append(
                    Function(
                        id=f_id,
                        file_id=file_id,
                        module_id=mod_id,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        parameters=param_entities,
                        return_type=parse_type_representation(fn_ast.return_type),
                        is_async=fn_ast.is_async,
                        parent_id=parent_id,
                        location=fn_loc,
                        metadata=metadata_dict,
                    )
                )

                symbols.append(
                    Symbol(
                        id=f_id,
                        symbol_kind=EntityKind.FUNCTION,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        language=Language.PYTHON,
                        file_id=file_id,
                        location=fn_loc,
                    )
                )
                return f_id

        def process_field_node(f_ast: PythonField, parent_qname: str, parent_id: str) -> str:
            f_qname = f"{parent_qname}.{f_ast.name}"
            f_loc = to_ir_source_location(f_ast.location, file_path)
            f_id = generate_entity_id(EntityKind.VARIABLE, file_path, f_qname, parent_id=parent_id)
            symbol_ids.append(f_id)

            variables.append(
                Variable(
                    id=f_id,
                    file_id=file_id,
                    parent_id=parent_id,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    declared_type=parse_type_representation(f_ast.annotation),
                    initializer=f_ast.value,
                    location=f_loc,
                )
            )

            symbols.append(
                Symbol(
                    id=f_id,
                    symbol_kind=EntityKind.VARIABLE,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    language=Language.PYTHON,
                    file_id=file_id,
                    location=f_loc,
                )
            )
            return f_id

        def process_class_node(cls_ast: PythonClass, parent_qname: str, parent_id: str) -> str:
            c_qname = f"{parent_qname}.{cls_ast.name}" if parent_qname else cls_ast.name
            c_loc = to_ir_source_location(cls_ast.location, file_path)
            c_id = generate_entity_id(EntityKind.CLASS, file_path, c_qname, parent_id=parent_id)
            symbol_ids.append(c_id)

            # Base classes references
            base_refs: list[Reference] = []
            for base_name in cls_ast.bases:
                loc_key = f"extends:{base_name}"
                b_ref_id = generate_entity_id(
                    EntityKind.REFERENCE, file_path, base_name, location_str=loc_key
                )
                reference_ids.append(b_ref_id)
                b_ref = Reference(
                    id=b_ref_id,
                    ref_kind=ReferenceKind.EXTENDS,
                    source_file_id=file_id,
                    source_location=c_loc,
                    target_qualified_name=base_name,
                )
                references.append(b_ref)
                base_refs.append(b_ref)

            method_ids_in_cls: list[str] = []
            field_ids_in_cls: list[str] = []
            nested_ids_in_cls: list[str] = []

            for m_ast in cls_ast.methods:
                m_id = process_function_node(m_ast, c_qname, c_id, is_inside_class=True)
                method_ids_in_cls.append(m_id)

            for f_ast in cls_ast.fields:
                f_id = process_field_node(f_ast, c_qname, c_id)
                field_ids_in_cls.append(f_id)

            for n_ast in cls_ast.nested_classes:
                n_id = process_class_node(n_ast, c_qname, c_id)
                nested_ids_in_cls.append(n_id)

            dec_exprs = [d.expression for d in cls_ast.decorators]
            metadata_dict = {"decorators": dec_exprs} if dec_exprs else {}
            super_ref = base_refs[0] if base_refs else None

            classes.append(
                Class(
                    id=c_id,
                    file_id=file_id,
                    module_id=mod_id,
                    name=cls_ast.name,
                    qualified_name=c_qname,
                    parent_id=parent_id,
                    superclass_ref=super_ref,
                    method_ids=method_ids_in_cls,
                    field_ids=field_ids_in_cls,
                    nested_class_ids=nested_ids_in_cls,
                    location=c_loc,
                    metadata=metadata_dict,
                )
            )

            symbols.append(
                Symbol(
                    id=c_id,
                    symbol_kind=EntityKind.CLASS,
                    name=cls_ast.name,
                    qualified_name=c_qname,
                    language=Language.PYTHON,
                    file_id=file_id,
                    location=c_loc,
                )
            )
            return c_id

        for fn_ast in ast.functions:
            process_function_node(fn_ast, mod_qname, file_id, is_inside_class=False)

        for cls_ast in ast.classes:
            process_class_node(cls_ast, mod_qname, file_id)

        file_entity = File(
            id=file_id,
            repository_id=repository_id,
            path=file_path,
            language=Language.PYTHON,
            content_hash=content_hash,
            loc=loc,
            module_ids=module_ids,
            symbol_ids=symbol_ids,
            reference_ids=reference_ids,
        )

        return NormalizationResult(
            file=file_entity,
            modules=modules,
            classes=classes,
            interfaces=[],
            functions=functions,
            methods=methods,
            variables=variables,
            parameters=parameters,
            references=references,
            symbols=symbols,
            diagnostics=[],
        )
