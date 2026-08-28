"""TypeScript AST to Canonical Code IR normalizer."""

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
    Symbol,
    Variable,
    Visibility,
    generate_entity_id,
)
from code_analyzer.normalization.base import ASTNormalizer
from code_analyzer.normalization.location_helper import to_ir_source_location
from code_analyzer.normalization.result import NormalizationResult
from code_analyzer.normalization.type_helper import parse_type_representation
from code_analyzer.parsers.models import Language
from code_analyzer.parsers.typescript_ast import (
    TypeScriptClass,
    TypeScriptField,
    TypeScriptFunction,
    TypeScriptInterface,
    TypeScriptStructure,
    TypeScriptType,
)


def _extract_ts_visibility(modifiers: list[str]) -> Visibility | None:
    """Helper to map TypeScript modifier keywords to canonical Visibility enum."""
    if "public" in modifiers:
        return Visibility.PUBLIC
    if "protected" in modifiers:
        return Visibility.PROTECTED
    if "private" in modifiers:
        return Visibility.PRIVATE
    return None


class TypeScriptNormalizer(ASTNormalizer[TypeScriptStructure]):
    """Normalizes TypeScriptStructure AST models into Canonical Code IR."""

    def normalize(
        self,
        ast: TypeScriptStructure,
        repository_id: str,
        file_path: str,
        language: Language = Language.TYPESCRIPT,
        content_hash: str | None = None,
        loc: int = 0,
    ) -> NormalizationResult:
        """Normalize TypeScriptStructure into a canonical NormalizationResult."""
        file_id = generate_entity_id(EntityKind.FILE, file_path, file_path, parent_id=repository_id)

        modules: list[Module] = []
        classes: list[Class] = []
        interfaces: list[Interface] = []
        functions: list[Function] = []
        methods: list[Method] = []
        variables: list[Variable] = []
        parameters: list[Parameter] = []
        references: list[Reference] = []
        symbols: list[Symbol] = []
        symbol_ids: list[str] = []
        reference_ids: list[str] = []
        module_ids: list[str] = []

        mod_name = file_path.replace("\\", "/").split("/")[-1].split(".")[0]
        mod_id = generate_entity_id(EntityKind.MODULE, file_path, mod_name, parent_id=file_id)
        module_ids.append(mod_id)

        modules.append(
            Module(
                id=mod_id,
                file_id=file_id,
                name=mod_name,
                qualified_name=mod_name,
            )
        )

        # Normalize imports
        for imp in ast.imports:
            ref_loc = to_ir_source_location(imp.location, file_path)
            loc_key = f"{ref_loc.start_line}:{ref_loc.start_column}" if ref_loc else ""

            if imp.imported_names:
                for name in imp.imported_names:
                    target_qname = f"{imp.module_path}.{name}"
                    ref_id = generate_entity_id(
                        EntityKind.REFERENCE,
                        file_path,
                        target_qname,
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
                            target_qualified_name=target_qname,
                        )
                    )
            else:
                ref_id = generate_entity_id(
                    EntityKind.REFERENCE,
                    file_path,
                    imp.module_path,
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
                        target_qualified_name=imp.module_path,
                    )
                )

        # Export metadata tracking
        export_meta_map: dict[str, bool] = {}
        for exp in ast.exports:
            for exp_name in exp.exported_names:
                export_meta_map[exp_name] = True
            if exp.default_export:
                export_meta_map[exp.default_export] = True

        def process_function_node(
            fn_ast: TypeScriptFunction,
            parent_qname: str,
            parent_id: str,
            is_inside_class: bool,
            is_constructor: bool = False,
        ) -> str:
            fn_qname = f"{parent_qname}.{fn_ast.name}" if parent_qname else fn_ast.name
            fn_loc = to_ir_source_location(fn_ast.location, file_path)
            visibility = _extract_ts_visibility(fn_ast.modifiers)

            is_exported = fn_ast.is_exported or export_meta_map.get(fn_ast.name, False)
            meta = {"is_exported": True} if is_exported else {}

            if is_inside_class:
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
                        declared_type=parse_type_representation(p_ast.type_annotation),
                        position=idx,
                        is_optional=p_ast.is_optional,
                        location=p_loc,
                    )
                    param_entities.append(param_entity)
                    parameters.append(param_entity)

                methods.append(
                    Method(
                        id=m_id,
                        file_id=file_id,
                        class_id=parent_id,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        parameters=param_entities,
                        return_type=parse_type_representation(fn_ast.return_type),
                        type_parameters=fn_ast.type_parameters,
                        modifiers=fn_ast.modifiers,
                        is_async=fn_ast.is_async,
                        is_static="static" in fn_ast.modifiers,
                        is_abstract="abstract" in fn_ast.modifiers,
                        is_constructor=is_constructor,
                        visibility=visibility,
                        location=fn_loc,
                        metadata=meta,
                    )
                )

                symbols.append(
                    Symbol(
                        id=m_id,
                        symbol_kind=EntityKind.METHOD,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        language=Language.TYPESCRIPT,
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
                        declared_type=parse_type_representation(p_ast.type_annotation),
                        position=idx,
                        is_optional=p_ast.is_optional,
                        location=p_loc,
                    )
                    param_entities.append(param_entity)
                    parameters.append(param_entity)

                functions.append(
                    Function(
                        id=f_id,
                        file_id=file_id,
                        module_id=mod_id,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        parameters=param_entities,
                        return_type=parse_type_representation(fn_ast.return_type),
                        type_parameters=fn_ast.type_parameters,
                        modifiers=fn_ast.modifiers,
                        is_async=fn_ast.is_async,
                        visibility=visibility,
                        parent_id=parent_id,
                        location=fn_loc,
                        metadata=meta,
                    )
                )

                symbols.append(
                    Symbol(
                        id=f_id,
                        symbol_kind=EntityKind.FUNCTION,
                        name=fn_ast.name,
                        qualified_name=fn_qname,
                        language=Language.TYPESCRIPT,
                        file_id=file_id,
                        location=fn_loc,
                    )
                )
                return f_id

        def process_field_node(f_ast: TypeScriptField, parent_qname: str, parent_id: str) -> str:
            f_qname = f"{parent_qname}.{f_ast.name}"
            f_loc = to_ir_source_location(f_ast.location, file_path)
            visibility = _extract_ts_visibility(f_ast.modifiers)
            f_id = generate_entity_id(EntityKind.VARIABLE, file_path, f_qname, parent_id=parent_id)
            symbol_ids.append(f_id)

            variables.append(
                Variable(
                    id=f_id,
                    file_id=file_id,
                    parent_id=parent_id,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    declared_type=parse_type_representation(f_ast.type_annotation),
                    modifiers=f_ast.modifiers,
                    visibility=visibility,
                    location=f_loc,
                )
            )

            symbols.append(
                Symbol(
                    id=f_id,
                    symbol_kind=EntityKind.VARIABLE,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    language=Language.TYPESCRIPT,
                    file_id=file_id,
                    location=f_loc,
                )
            )
            return f_id

        def process_class_node(cls_ast: TypeScriptClass, parent_qname: str, parent_id: str) -> str:
            c_qname = f"{parent_qname}.{cls_ast.name}" if parent_qname else cls_ast.name
            c_loc = to_ir_source_location(cls_ast.location, file_path)
            c_id = generate_entity_id(EntityKind.CLASS, file_path, c_qname, parent_id=parent_id)
            symbol_ids.append(c_id)
            visibility = _extract_ts_visibility(cls_ast.modifiers)

            # Extends reference
            super_ref: Reference | None = None
            if cls_ast.extends_clause:
                loc_key = f"extends:{cls_ast.extends_clause}"
                s_ref_id = generate_entity_id(
                    EntityKind.REFERENCE, file_path, cls_ast.extends_clause, location_str=loc_key
                )
                reference_ids.append(s_ref_id)
                super_ref = Reference(
                    id=s_ref_id,
                    ref_kind=ReferenceKind.EXTENDS,
                    source_file_id=file_id,
                    source_location=c_loc,
                    target_qualified_name=cls_ast.extends_clause,
                )
                references.append(super_ref)

            # Implements references
            iface_refs: list[Reference] = []
            for iface_name in cls_ast.implements_clause:
                loc_key = f"implements:{iface_name}"
                i_ref_id = generate_entity_id(
                    EntityKind.REFERENCE, file_path, iface_name, location_str=loc_key
                )
                reference_ids.append(i_ref_id)
                i_ref = Reference(
                    id=i_ref_id,
                    ref_kind=ReferenceKind.IMPLEMENTS,
                    source_file_id=file_id,
                    source_location=c_loc,
                    target_qualified_name=iface_name,
                )
                references.append(i_ref)
                iface_refs.append(i_ref)

            method_ids_in_cls: list[str] = []
            field_ids_in_cls: list[str] = []
            nested_ids_in_cls: list[str] = []

            for ctor_ast in cls_ast.constructors:
                ctor_id = process_function_node(
                    ctor_ast, c_qname, c_id, is_inside_class=True, is_constructor=True
                )
                method_ids_in_cls.append(ctor_id)

            for m_ast in cls_ast.methods:
                m_id = process_function_node(m_ast, c_qname, c_id, is_inside_class=True)
                method_ids_in_cls.append(m_id)

            for f_ast in cls_ast.fields:
                f_id = process_field_node(f_ast, c_qname, c_id)
                field_ids_in_cls.append(f_id)

            for n_ast in cls_ast.nested_classes:
                n_id = process_class_node(n_ast, c_qname, c_id)
                nested_ids_in_cls.append(n_id)

            is_exported = cls_ast.is_exported or export_meta_map.get(cls_ast.name, False)
            meta = {"is_exported": True} if is_exported else {}

            classes.append(
                Class(
                    id=c_id,
                    file_id=file_id,
                    module_id=mod_id,
                    name=cls_ast.name,
                    qualified_name=c_qname,
                    modifiers=cls_ast.modifiers,
                    type_parameters=cls_ast.type_parameters,
                    parent_id=parent_id,
                    superclass_ref=super_ref,
                    interface_refs=iface_refs,
                    method_ids=method_ids_in_cls,
                    field_ids=field_ids_in_cls,
                    nested_class_ids=nested_ids_in_cls,
                    is_abstract="abstract" in cls_ast.modifiers,
                    visibility=visibility,
                    location=c_loc,
                    metadata=meta,
                )
            )

            symbols.append(
                Symbol(
                    id=c_id,
                    symbol_kind=EntityKind.CLASS,
                    name=cls_ast.name,
                    qualified_name=c_qname,
                    language=Language.TYPESCRIPT,
                    file_id=file_id,
                    location=c_loc,
                )
            )
            return c_id

        def process_interface_node(
            iface_ast: TypeScriptInterface, parent_qname: str, parent_id: str
        ) -> str:
            if_qname = f"{parent_qname}.{iface_ast.name}" if parent_qname else iface_ast.name
            if_loc = to_ir_source_location(iface_ast.location, file_path)
            if_id = generate_entity_id(
                EntityKind.INTERFACE, file_path, if_qname, parent_id=parent_id
            )
            symbol_ids.append(if_id)

            extends_refs: list[Reference] = []
            if iface_ast.extends_clause:
                loc_key = f"extends:{iface_ast.extends_clause}"
                e_ref_id = generate_entity_id(
                    EntityKind.REFERENCE, file_path, iface_ast.extends_clause, location_str=loc_key
                )
                reference_ids.append(e_ref_id)
                e_ref = Reference(
                    id=e_ref_id,
                    ref_kind=ReferenceKind.EXTENDS,
                    source_file_id=file_id,
                    source_location=if_loc,
                    target_qualified_name=iface_ast.extends_clause,
                )
                references.append(e_ref)
                extends_refs.append(e_ref)

            method_ids_in_iface: list[str] = []
            field_ids_in_iface: list[str] = []

            for m_ast in iface_ast.methods:
                m_id = process_function_node(m_ast, if_qname, if_id, is_inside_class=True)
                method_ids_in_iface.append(m_id)

            for f_ast in iface_ast.fields:
                f_id = process_field_node(f_ast, if_qname, if_id)
                field_ids_in_iface.append(f_id)

            is_exported = iface_ast.is_exported or export_meta_map.get(iface_ast.name, False)
            meta = {"is_exported": True} if is_exported else {}

            interfaces.append(
                Interface(
                    id=if_id,
                    file_id=file_id,
                    module_id=mod_id,
                    name=iface_ast.name,
                    qualified_name=if_qname,
                    type_parameters=iface_ast.type_parameters,
                    parent_id=parent_id,
                    extends_refs=extends_refs,
                    method_ids=method_ids_in_iface,
                    field_ids=field_ids_in_iface,
                    location=if_loc,
                    metadata=meta,
                )
            )

            symbols.append(
                Symbol(
                    id=if_id,
                    symbol_kind=EntityKind.INTERFACE,
                    name=iface_ast.name,
                    qualified_name=if_qname,
                    language=Language.TYPESCRIPT,
                    file_id=file_id,
                    location=if_loc,
                )
            )
            return if_id

        def process_type_alias_node(
            t_ast: TypeScriptType, parent_qname: str, parent_id: str
        ) -> str:
            t_qname = f"{parent_qname}.{t_ast.name}" if parent_qname else t_ast.name
            t_loc = to_ir_source_location(t_ast.location, file_path)
            t_id = generate_entity_id(EntityKind.VARIABLE, file_path, t_qname, parent_id=parent_id)
            symbol_ids.append(t_id)

            is_exported = t_ast.is_exported or export_meta_map.get(t_ast.name, False)
            meta = {
                "is_type_alias": True,
                "definition": t_ast.definition,
                "type_parameters": t_ast.type_parameters,
            }
            if is_exported:
                meta["is_exported"] = True

            variables.append(
                Variable(
                    id=t_id,
                    file_id=file_id,
                    parent_id=parent_id,
                    name=t_ast.name,
                    qualified_name=t_qname,
                    declared_type=parse_type_representation(t_ast.definition),
                    is_constant=True,
                    location=t_loc,
                    metadata=meta,
                )
            )

            symbols.append(
                Symbol(
                    id=t_id,
                    symbol_kind=EntityKind.VARIABLE,
                    name=t_ast.name,
                    qualified_name=t_qname,
                    language=Language.TYPESCRIPT,
                    file_id=file_id,
                    location=t_loc,
                )
            )
            return t_id

        # Normalize module-level elements
        for fn_ast in ast.functions:
            process_function_node(fn_ast, mod_name, file_id, is_inside_class=False)

        for cls_ast in ast.classes:
            process_class_node(cls_ast, mod_name, file_id)

        for iface_ast in ast.interfaces:
            process_interface_node(iface_ast, mod_name, file_id)

        for type_ast in ast.types:
            process_type_alias_node(type_ast, mod_name, file_id)

        file_entity = File(
            id=file_id,
            repository_id=repository_id,
            path=file_path,
            language=Language.TYPESCRIPT,
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
            interfaces=interfaces,
            functions=functions,
            methods=methods,
            variables=variables,
            parameters=parameters,
            references=references,
            symbols=symbols,
            diagnostics=[],
        )
