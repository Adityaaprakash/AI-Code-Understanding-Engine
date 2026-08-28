"""Helper functions for converting type annotations into canonical TypeRepresentation models."""

import re

from code_analyzer.ir import TypeRepresentation


def parse_type_representation(type_str: str | None) -> TypeRepresentation | None:
    """Parse a source language type string into a canonical TypeRepresentation model.

    Handles generic type expressions across Java (List<String>), Python (list[str]),
    and TypeScript (Promise<User>).

    Args:
        type_str: Type annotation string from source code parser.

    Returns:
        Canonical TypeRepresentation object or None if type_str is empty.
    """
    if not type_str or not type_str.strip():
        return None

    raw_type = type_str.strip()

    # Match generic signatures: Base<Arg1, Arg2> or Base[Arg1, Arg2]
    match = re.match(r"^([a-zA-Z0-9_\.]+)\s*[<\[](.+)[>\]]$", raw_type)
    if not match:
        return TypeRepresentation(
            display_name=raw_type,
            normalized_name=raw_type,
            type_arguments=[],
        )

    base_name = match.group(1).strip()
    args_raw = match.group(2).strip()

    # Split args by comma respecting nested brackets
    args: list[TypeRepresentation] = []
    depth = 0
    current_arg = []

    for char in args_raw:
        if char in ("<", "["):
            depth += 1
            current_arg.append(char)
        elif char in (">", "]"):
            depth -= 1
            current_arg.append(char)
        elif char == "," and depth == 0:
            arg_str = "".join(current_arg).strip()
            if arg_str:
                parsed_sub = parse_type_representation(arg_str)
                if parsed_sub:
                    args.append(parsed_sub)
            current_arg = []
        else:
            current_arg.append(char)

    if current_arg:
        arg_str = "".join(current_arg).strip()
        if arg_str:
            parsed_sub = parse_type_representation(arg_str)
            if parsed_sub:
                args.append(parsed_sub)

    return TypeRepresentation(
        display_name=raw_type,
        normalized_name=base_name,
        type_arguments=args,
    )
