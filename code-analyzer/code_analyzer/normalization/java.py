"""Java AST to Canonical Code IR normalizer."""

from code_analyzer.ir import (
    Class,
    EntityKind,
    File,
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
from code_analyzer.parsers.java_ast import (
    JavaClass,
    JavaField,
    JavaMethod,
    JavaStructure,
)
from code_analyzer.parsers.models import Language


def _extract_visibility(modifiers: list[str]) -> Visibility:
    """Helper to map modifier keywords to canonical Visibility enum."""
    if "public" in modifiers:
        return Visibility.PUBLIC
    if "protected" in modifiers:
        return Visibility.PROTECTED
    if "private" in modifiers:
        return Visibility.PRIVATE
    return Visibility.PACKAGE


class JavaNormalizer(ASTNormalizer[JavaStructure]):
    """Normalizes JavaStructure AST models into Canonical Code IR."""

    def normalize(
        self,
        ast: JavaStructure,
        repository_id: str,
        file_path: str,
        language: Language = Language.JAVA,
        content_hash: str | None = None,
        loc: int = 0,
    ) -> NormalizationResult:
        """Normalize JavaStructure into a canonical NormalizationResult."""
        file_id = generate_entity_id(EntityKind.FILE, file_path, file_path, parent_id=repository_id)

        modules: list[Module] = []
        classes: list[Class] = []
        interfaces: list[Interface] = []
        methods: list[Method] = []
        variables: list[Variable] = []
        parameters: list[Parameter] = []
        references: list[Reference] = []
        symbols: list[Symbol] = []
        symbol_ids: list[str] = []
        reference_ids: list[str] = []
        module_ids: list[str] = []

        pkg_qname = ""
        if ast.package:
            pkg_qname = ast.package.name
            simple_mod_name = pkg_qname.split(".")[-1]
            mod_id = generate_entity_id(EntityKind.MODULE, file_path, pkg_qname, parent_id=file_id)
            module_ids.append(mod_id)

            mod_loc = to_ir_source_location(ast.package.location, file_path)
            modules.append(
                Module(
                    id=mod_id,
                    file_id=file_id,
                    name=simple_mod_name,
                    qualified_name=pkg_qname,
                    location=mod_loc,
                )
            )

        # Normalize imports
        for imp in ast.imports:
            ref_loc = to_ir_source_location(imp.location, file_path)
            loc_key = f"{ref_loc.start_line}:{ref_loc.start_column}" if ref_loc else ""
            ref_id = generate_entity_id(
                EntityKind.REFERENCE, file_path, imp.path, parent_id=file_id, location_str=loc_key
            )
            reference_ids.append(ref_id)
            references.append(
                Reference(
                    id=ref_id,
                    ref_kind=ReferenceKind.IMPORT,
                    source_file_id=file_id,
                    source_location=ref_loc,
                    target_qualified_name=imp.path,
                )
            )

        # Process classes and interfaces recursively
        def process_class_node(cls_ast: JavaClass, parent_qname: str, parent_id: str) -> str:
            qname = f"{parent_qname}.{cls_ast.name}" if parent_qname else cls_ast.name
            cls_loc = to_ir_source_location(cls_ast.location, file_path)
            visibility = _extract_visibility(cls_ast.modifiers)

            method_ids_in_cls: list[str] = []
            field_ids_in_cls: list[str] = []
            nested_ids_in_cls: list[str] = []

            # Superclass reference
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
                    source_location=cls_loc,
                    target_qualified_name=cls_ast.extends_clause,
                )
                references.append(super_ref)

            # Interface references
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
                    source_location=cls_loc,
                    target_qualified_name=iface_name,
                )
                references.append(i_ref)
                iface_refs.append(i_ref)

            if cls_ast.is_interface:
                if_id = generate_entity_id(
                    EntityKind.INTERFACE, file_path, qname, parent_id=file_id
                )
                symbol_ids.append(if_id)

                # Process methods
                for m_ast in cls_ast.methods:
                    m_id = process_method_node(m_ast, qname, if_id)
                    method_ids_in_cls.append(m_id)

                # Process fields
                for f_ast in cls_ast.fields:
                    f_id = process_field_node(f_ast, qname, if_id)
                    field_ids_in_cls.append(f_id)

                # Process nested classes
                for n_ast in cls_ast.nested_classes:
                    n_id = process_class_node(n_ast, qname, if_id)
                    nested_ids_in_cls.append(n_id)

                extends_iface_refs = [super_ref] if super_ref else []

                interfaces.append(
                    Interface(
                        id=if_id,
                        file_id=file_id,
                        name=cls_ast.name,
                        qualified_name=qname,
                        modifiers=cls_ast.modifiers,
                        type_parameters=cls_ast.type_parameters,
                        parent_id=parent_id,
                        extends_refs=extends_iface_refs,
                        method_ids=method_ids_in_cls,
                        field_ids=field_ids_in_cls,
                        visibility=visibility,
                        location=cls_loc,
                    )
                )

                symbols.append(
                    Symbol(
                        id=if_id,
                        symbol_kind=EntityKind.INTERFACE,
                        name=cls_ast.name,
                        qualified_name=qname,
                        language=Language.JAVA,
                        file_id=file_id,
                        location=cls_loc,
                    )
                )
                return if_id
            else:
                c_id = generate_entity_id(EntityKind.CLASS, file_path, qname, parent_id=file_id)
                symbol_ids.append(c_id)

                # Process methods
                for m_ast in cls_ast.methods:
                    m_id = process_method_node(m_ast, qname, c_id)
                    method_ids_in_cls.append(m_id)

                # Process fields
                for f_ast in cls_ast.fields:
                    f_id = process_field_node(f_ast, qname, c_id)
                    field_ids_in_cls.append(f_id)

                # Process nested classes
                for n_ast in cls_ast.nested_classes:
                    n_id = process_class_node(n_ast, qname, c_id)
                    nested_ids_in_cls.append(n_id)

                classes.append(
                    Class(
                        id=c_id,
                        file_id=file_id,
                        name=cls_ast.name,
                        qualified_name=qname,
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
                        location=cls_loc,
                    )
                )

                symbols.append(
                    Symbol(
                        id=c_id,
                        symbol_kind=EntityKind.CLASS,
                        name=cls_ast.name,
                        qualified_name=qname,
                        language=Language.JAVA,
                        file_id=file_id,
                        location=cls_loc,
                    )
                )
                return c_id

        def process_method_node(m_ast: JavaMethod, parent_qname: str, class_id: str) -> str:
            m_qname = f"{parent_qname}.{m_ast.name}"
            m_loc = to_ir_source_location(m_ast.location, file_path)
            m_visibility = _extract_visibility(m_ast.modifiers)
            m_id = generate_entity_id(EntityKind.METHOD, file_path, m_qname, parent_id=class_id)
            symbol_ids.append(m_id)

            param_entities: list[Parameter] = []
            for idx, p_ast in enumerate(m_ast.parameters):
                p_qname = f"{m_qname}.{p_ast.name}"
                p_loc = to_ir_source_location(p_ast.location, file_path)
                p_id = generate_entity_id(EntityKind.PARAMETER, file_path, p_qname, parent_id=m_id)
                param_entity = Parameter(
                    id=p_id,
                    parent_callable_id=m_id,
                    name=p_ast.name,
                    declared_type=parse_type_representation(p_ast.type_name),
                    position=idx,
                    modifiers=p_ast.modifiers,
                    location=p_loc,
                )
                param_entities.append(param_entity)
                parameters.append(param_entity)

            methods.append(
                Method(
                    id=m_id,
                    file_id=file_id,
                    class_id=class_id,
                    name=m_ast.name,
                    qualified_name=m_qname,
                    parameters=param_entities,
                    return_type=parse_type_representation(m_ast.return_type),
                    type_parameters=m_ast.type_parameters,
                    modifiers=m_ast.modifiers,
                    is_async=False,
                    is_static="static" in m_ast.modifiers,
                    is_abstract="abstract" in m_ast.modifiers,
                    is_constructor=m_ast.is_constructor,
                    visibility=m_visibility,
                    location=m_loc,
                )
            )

            symbols.append(
                Symbol(
                    id=m_id,
                    symbol_kind=EntityKind.METHOD,
                    name=m_ast.name,
                    qualified_name=m_qname,
                    language=Language.JAVA,
                    file_id=file_id,
                    location=m_loc,
                )
            )
            return m_id

        def process_field_node(f_ast: JavaField, parent_qname: str, parent_id: str) -> str:
            f_qname = f"{parent_qname}.{f_ast.name}"
            f_loc = to_ir_source_location(f_ast.location, file_path)
            f_visibility = _extract_visibility(f_ast.modifiers)
            f_id = generate_entity_id(EntityKind.VARIABLE, file_path, f_qname, parent_id=parent_id)
            symbol_ids.append(f_id)

            is_const = "final" in f_ast.modifiers and "static" in f_ast.modifiers

            variables.append(
                Variable(
                    id=f_id,
                    file_id=file_id,
                    parent_id=parent_id,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    declared_type=parse_type_representation(f_ast.type_name),
                    modifiers=f_ast.modifiers,
                    is_constant=is_const,
                    visibility=f_visibility,
                    location=f_loc,
                )
            )

            symbols.append(
                Symbol(
                    id=f_id,
                    symbol_kind=EntityKind.VARIABLE,
                    name=f_ast.name,
                    qualified_name=f_qname,
                    language=Language.JAVA,
                    file_id=file_id,
                    location=f_loc,
                )
            )
            return f_id

        for cls_ast in ast.classes:
            process_class_node(cls_ast, pkg_qname, file_id)

        file_entity = File(
            id=file_id,
            repository_id=repository_id,
            path=file_path,
            language=Language.JAVA,
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
            functions=[],
            methods=methods,
            variables=variables,
            parameters=parameters,
            references=references,
            symbols=symbols,
            diagnostics=[],
        )
