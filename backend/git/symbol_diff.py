import subprocess
from typing import Any

from backend.git.models import (
    ChangedFile,
    ChangedSymbol,
    ChangedSymbolResult,
    ChangeType,
    GitDiffResult,
    OpaqueFile,
    OpaqueFileFallbackReason,
    SymbolChangeType,
)
from code_analyzer.ir import Symbol
from code_analyzer.normalization import NormalizationResult, normalize_parse_result
from code_analyzer.parsers import JavaParser, Language, PythonParser, TypeScriptParser


class ChangedSymbolDetector:
    """Detects semantic symbol changes between commits based on GitDiffResult."""

    def detect_changes(self, diff_result: GitDiffResult) -> ChangedSymbolResult:
        changed_symbols: list[ChangedSymbol] = []
        opaque_files: list[OpaqueFile] = []

        for cf in diff_result.changed_files:
            syms, opaque = self._process_file_change(cf, diff_result.repository_path, diff_result.base_commit, diff_result.target_commit)
            changed_symbols.extend(syms)
            if opaque:
                opaque_files.append(opaque)

        # Sort output deterministically
        changed_symbols = sorted(changed_symbols, key=lambda s: (s.file_path, s.qualified_name))

        return ChangedSymbolResult(
            repository_path=diff_result.repository_path,
            base_commit=diff_result.base_commit,
            target_commit=diff_result.target_commit,
            changed_symbols=changed_symbols,
            opaque_files=opaque_files,
        )

    def _process_file_change(
        self,
        changed_file: ChangedFile,
        repo_path: str,
        base_commit: str,
        target_commit: str,
    ) -> tuple[list[ChangedSymbol], OpaqueFile | None]:
        lang_before = self._infer_language(changed_file.previous_path or changed_file.path)
        lang_after = self._infer_language(changed_file.path)

        # If it's not a supported language file, we cannot detect symbol level changes.
        if lang_before is None and lang_after is None:
            return [], OpaqueFile(
                path=changed_file.path,
                reason=OpaqueFileFallbackReason.UNSUPPORTED_LANGUAGE,
                change_type=changed_file.change_type,
            )

        before_symbols: dict[str, tuple[Symbol, str]] = {}
        after_symbols: dict[str, tuple[Symbol, str]] = {}

        if changed_file.change_type in (ChangeType.MODIFIED, ChangeType.DELETED, ChangeType.RENAMED):
            if lang_before is not None:
                orig_path = changed_file.previous_path or changed_file.path
                before_code = self._get_file_at_commit(repo_path, base_commit, orig_path)
                if before_code is not None:
                    norm, reason = self._parse_and_normalize(repo_path, before_code, orig_path, lang_before)
                    if norm:
                        before_symbols = self._get_symbols_map(norm, before_code)
                    else:
                        return [], OpaqueFile(
                            path=changed_file.path,
                            reason=reason or OpaqueFileFallbackReason.PARSER_FAILURE,
                            change_type=changed_file.change_type,
                        )
                else:
                    return [], OpaqueFile(
                        path=changed_file.path,
                        reason=OpaqueFileFallbackReason.SOURCE_UNAVAILABLE,
                        change_type=changed_file.change_type,
                    )

        if changed_file.change_type in (ChangeType.ADDED, ChangeType.MODIFIED, ChangeType.RENAMED):
            if lang_after is not None:
                after_code = self._get_file_at_commit(repo_path, target_commit, changed_file.path)
                if after_code is not None:
                    norm, reason = self._parse_and_normalize(repo_path, after_code, changed_file.path, lang_after)
                    if norm:
                        after_symbols = self._get_symbols_map(norm, after_code)
                    else:
                        return [], OpaqueFile(
                            path=changed_file.path,
                            reason=reason or OpaqueFileFallbackReason.PARSER_FAILURE,
                            change_type=changed_file.change_type,
                        )
                else:
                    return [], OpaqueFile(
                        path=changed_file.path,
                        reason=OpaqueFileFallbackReason.SOURCE_UNAVAILABLE,
                        change_type=changed_file.change_type,
                    )

        return self._compare_symbols(before_symbols, after_symbols, changed_file), None

    def _compare_symbols(
        self,
        before_symbols: dict[str, tuple[Symbol, str]],
        after_symbols: dict[str, tuple[Symbol, str]],
        changed_file: ChangedFile,
    ) -> list[ChangedSymbol]:
        result = []
        old_path = changed_file.previous_path or changed_file.path
        new_path = changed_file.path

        before_qnames = set(before_symbols.keys())
        after_qnames = set(after_symbols.keys())

        # If RENAMED but content didn't fundamentally change its logical paths, we can match on qualified names.
        # Commonly, qualified names often change if the file path changes (e.g. Java package, Python module).
        # We rely on matching by qualified_name. If qualified_name changes, it's ADDED/DELETED.

        # 1. Check DELETED/RENAMED OUT (exists in before, not in after)
        for b_qname, (b_sym, _) in before_symbols.items():
            if b_qname not in after_symbols:
                result.append(ChangedSymbol(
                    symbol_id=b_sym.id,
                    change_type=SymbolChangeType.DELETED,
                    name=b_sym.name,
                    qualified_name=b_sym.qualified_name,
                    kind=b_sym.symbol_kind,
                    file_path=old_path,
                    previous_file_path=None,
                    previous_qualified_name=None,
                ))

        # 2. Check ADDED (exists in after, not in before)
        for a_qname, (a_sym, _) in after_symbols.items():
            if a_qname not in before_symbols:
                change_type = SymbolChangeType.ADDED

                # If it's a file rename, and we have the exact same qname (extremely rare in Python/Java, but possible in TS),
                # it would have been matched below. But if qnames are different, we cannot trivially pair them without semantic fuzzing,
                # which the prompt disallowed: "DO NOT implement a sophisticated fuzzy semantic matcher in 8B... explicitly document that limitation."
                # We do check if there is an exact literal match in renamed files if we stripped prefixes, but for strict determinism we treat them as ADDED/DELETED.

                result.append(ChangedSymbol(
                    symbol_id=a_sym.id,
                    change_type=change_type,
                    name=a_sym.name,
                    qualified_name=a_sym.qualified_name,
                    kind=a_sym.symbol_kind,
                    file_path=new_path,
                    previous_file_path=old_path if changed_file.change_type == ChangeType.RENAMED else None,
                    previous_qualified_name=None,
                ))

        # 3. Check MODIFIED / UNCHANGED (exists in both)
        for qname in before_qnames.intersection(after_qnames):
            b_sym, b_body = before_symbols[qname]
            a_sym, a_body = after_symbols[qname]

            # Since the CodeChunker extracts exact text including whitespace/comments for meaning,
            # any difference in the extracted method text implies the indexed chunk is mechanically mutating.
            if b_body != a_body:
                result.append(ChangedSymbol(
                    symbol_id=a_sym.id,
                    change_type=SymbolChangeType.MODIFIED,
                    name=a_sym.name,
                    qualified_name=a_sym.qualified_name,
                    kind=a_sym.symbol_kind,
                    file_path=new_path,
                    previous_symbol_id=b_sym.id,
                    previous_file_path=old_path if changed_file.change_type == ChangeType.RENAMED else None,
                    previous_qualified_name=b_sym.qualified_name if b_sym.qualified_name != a_sym.qualified_name else None,
                ))
            elif b_sym.id != a_sym.id or b_sym.location != a_sym.location:
                result.append(ChangedSymbol(
                    symbol_id=a_sym.id,
                    change_type=SymbolChangeType.IDENTITY_ONLY,
                    name=a_sym.name,
                    qualified_name=a_sym.qualified_name,
                    kind=a_sym.symbol_kind,
                    file_path=new_path,
                    previous_symbol_id=b_sym.id,
                    previous_file_path=old_path if changed_file.change_type == ChangeType.RENAMED else None,
                    previous_qualified_name=b_sym.qualified_name if b_sym.qualified_name != a_sym.qualified_name else None,
                ))

        return result

    def _infer_language(self, path: str) -> Language | None:
        path_lower = path.lower()
        if path_lower.endswith(".py"):
            return Language.PYTHON
        if path_lower.endswith(".java"):
            return Language.JAVA
        if path_lower.endswith((".ts", ".tsx", ".js", ".jsx")):
            return Language.TYPESCRIPT
        return None

    def _get_file_at_commit(self, repo_path: str, commit_sha: str, file_path: str) -> str | None:
        cmd = ["git", "show", f"{commit_sha}:{file_path}"]
        try:
            res = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                check=False,
            )
            if res.returncode != 0:
                return None
            return res.stdout.decode("utf-8", "replace")
        except Exception:
            return None

    def _parse_and_normalize(self, repo_path: str, source_code: str, file_path: str, lang: Language) -> tuple[NormalizationResult | None, OpaqueFileFallbackReason | None]:
        parser: Any = None
        if lang == Language.PYTHON:
            parser = PythonParser()
        elif lang == Language.JAVA:
            parser = JavaParser()
        elif lang == Language.TYPESCRIPT:
            parser = TypeScriptParser()
        else:
            return None, OpaqueFileFallbackReason.UNSUPPORTED_LANGUAGE

        try:
            parse_res = parser.parse(source_code, source_path=file_path)
            if not parse_res.success:
                return None, OpaqueFileFallbackReason.PARSER_FAILURE
            norm = normalize_parse_result(parse_res, repository_id=repo_path, file_path=file_path)
            return norm, None
        except Exception:
            return None, OpaqueFileFallbackReason.PARSER_FAILURE

    def _get_symbols_map(self, norm_res: NormalizationResult, source_code: str) -> dict[str, tuple[Symbol, str]]:
        sym_map = {}
        lines = source_code.splitlines(keepends=True)
        for sym in norm_res.symbols:
            loc = sym.location
            if not loc:
                continue

            # loc is 1-indexed for lines, 0-indexed for columns
            start_line_idx = loc.start_line - 1
            end_line_idx = loc.end_line - 1

            if start_line_idx < 0 or start_line_idx >= len(lines):
                continue

            if start_line_idx == end_line_idx:
                body = lines[start_line_idx][loc.start_column:loc.end_column]
            else:
                first_line = lines[start_line_idx][loc.start_column:]

                mid_lines = lines[start_line_idx + 1:end_line_idx]

                if end_line_idx < len(lines):
                    last_line = lines[end_line_idx][:loc.end_column]
                else:
                    last_line = ""

                body = first_line + "".join(mid_lines) + last_line

            sym_map[sym.qualified_name] = (sym, body)
        return sym_map
