import subprocess
from pathlib import Path

import pytest

from backend.git.diff_engine import GitDiffEngine
from backend.git.models import ChangedSymbolResult, OpaqueFileFallbackReason, SymbolChangeType
from backend.git.symbol_diff import ChangedSymbolDetector


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
    return repo_path


def run_git(repo_path: Path, *args: str) -> str:
    res = subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def commit_file(repo_path: Path, path: str, content: str, message: str) -> str:
    file_path = repo_path / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    run_git(repo_path, "add", path)
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def delete_file_and_commit(repo_path: Path, path: str, message: str) -> str:
    file_path = repo_path / path
    file_path.unlink()
    run_git(repo_path, "add", path)
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def rename_file_and_commit(repo_path: Path, old_path: str, new_path: str, message: str) -> str:
    run_git(repo_path, "mv", old_path, new_path)
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def get_changed_symbols(repo_path: Path, base_commit: str, target_commit: str) -> ChangedSymbolResult:
    engine = GitDiffEngine()
    diff_result = engine.get_diff(str(repo_path), base_commit, target_commit)
    detector = ChangedSymbolDetector()
    return detector.detect_changes(diff_result)


def test_modified_file_single_symbol_change(temp_git_repo: Path) -> None:
    code_before = """
def func_a():
    return 1

def func_b():
    return 2
"""
    code_after = """
def func_a():
    return 1

def func_b():
    return 3
"""
    base_sha = commit_file(temp_git_repo, "test.py", code_before, "first")
    target_sha = commit_file(temp_git_repo, "test.py", code_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert len(result.changed_symbols) == 1
    sym = result.changed_symbols[0]
    assert sym.name == "func_b"
    assert sym.change_type == SymbolChangeType.MODIFIED
    # func_a is UNCHANGED and should not be returned.


def test_added_symbol(temp_git_repo: Path) -> None:
    code_before = """
def func_a():
    return 1
"""
    code_after = """
def func_a():
    return 1

def func_c():
    return 3
"""
    base_sha = commit_file(temp_git_repo, "test.py", code_before, "first")
    target_sha = commit_file(temp_git_repo, "test.py", code_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert len(result.changed_symbols) == 1
    sym = result.changed_symbols[0]
    assert sym.name == "func_c"
    assert sym.change_type == SymbolChangeType.ADDED


def test_deleted_symbol(temp_git_repo: Path) -> None:
    code_before = """
def func_a(): return 1
def func_b(): return 2
"""
    code_after = """
def func_a(): return 1
"""
    base_sha = commit_file(temp_git_repo, "test.py", code_before, "first")
    target_sha = commit_file(temp_git_repo, "test.py", code_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert len(result.changed_symbols) == 1
    sym = result.changed_symbols[0]
    assert sym.name == "func_b"
    assert sym.change_type == SymbolChangeType.DELETED


def test_added_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.py", "def a(): pass", "a")
    target_sha = commit_file(temp_git_repo, "b.py", "def b(): pass", "b")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert len(result.changed_symbols) == 1
    assert result.changed_symbols[0].name == "b"
    assert result.changed_symbols[0].change_type == SymbolChangeType.ADDED


def test_deleted_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "del.py", "def deleted_func(): pass", "init")
    target_sha = delete_file_and_commit(temp_git_repo, "del.py", "delete")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert len(result.changed_symbols) == 1
    assert result.changed_symbols[0].name == "deleted_func"
    assert result.changed_symbols[0].change_type == SymbolChangeType.DELETED


def test_renamed_file(temp_git_repo: Path) -> None:
    # A renamed file without symbol modifications inside should NOT return any MODIFIED symbols.
    # We map by qualified name when possible. However, the qualified name of a class in Java/Python might change.
    # In Python, our qualified name is based on the file path. E.g. 'old.foo'.
    # Since qname changes to 'new.foo', it comes up as DELETED old.foo and ADDED new.foo.
    base_sha = commit_file(temp_git_repo, "old_name.py", "def foo(): pass", "first")
    target_sha = rename_file_and_commit(temp_git_repo, "old_name.py", "new_name.py", "rename")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    # 1 DELETED due to old module path, 1 ADDED due to new module path
    assert len(result.changed_symbols) == 2
    change_types = {s.change_type for s in result.changed_symbols}
    assert change_types == {SymbolChangeType.DELETED, SymbolChangeType.ADDED}

    # No MODIFIED symbols.
    assert SymbolChangeType.MODIFIED not in change_types


def test_unchanged_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.py", "def a(): pass", "a")
    # We just run diff against itself or commit something else unrelated
    target_sha = commit_file(temp_git_repo, "b.py", "def b(): pass", "b")

    # If we diff A to B it includes added file B, but no changes in A.
    engine = GitDiffEngine()
    diff_result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    # ensure "a.py" is not in changed files
    assert not any(f.path == "a.py" for f in diff_result.changed_files)

    detector = ChangedSymbolDetector()
    result = detector.detect_changes(diff_result)

    assert len(result.changed_symbols) == 1
    assert result.changed_symbols[0].name == "b"


def test_java_symbol_changes(temp_git_repo: Path) -> None:
    java_before = """
package com.example;
public class MyClass {
    public void myMethod() {
        System.out.println("Hello");
    }
}
"""
    java_after = """
package com.example;
public class MyClass {
    public void myMethod() {
        System.out.println("World");
    }
}
"""
    base_sha = commit_file(temp_git_repo, "MyClass.java", java_before, "first")
    target_sha = commit_file(temp_git_repo, "MyClass.java", java_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    # MyClass is unchanged conceptually, but its method body changed.
    # Wait, the class itself didn't change (no fields added).
    # Its extracted text body MIGHT change if the class body spans it.
    # Actually, the Class node text includes all methods!
    # So `MyClass` text also changes, leading to TWO modified symbols (MyClass, myMethod).
    # Let's verify standard expectation. The important part is myMethod is returned.
    names = {s.name for s in result.changed_symbols}
    assert "myMethod" in names

    my_meth = next(s for s in result.changed_symbols if s.name == "myMethod")
    assert my_meth.change_type == SymbolChangeType.MODIFIED


def test_typescript_symbol_changes(temp_git_repo: Path) -> None:
    ts_before = """
export class MyClass {
    public method(): string { return "a"; }
}
"""
    ts_after = """
export class MyClass {
    public method(): string { return "b"; }
}
"""
    base_sha = commit_file(temp_git_repo, "MyClass.ts", ts_before, "first")
    target_sha = commit_file(temp_git_repo, "MyClass.ts", ts_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    names = {s.name for s in result.changed_symbols}
    assert "method" in names

    meth = next(s for s in result.changed_symbols if s.name == "method")
    assert meth.change_type == SymbolChangeType.MODIFIED


def test_deterministic_repeated_comparison(temp_git_repo: Path) -> None:
    c_before = "def foo(): pass"
    c_after = "def foo(): print('hi')"

    base_sha = commit_file(temp_git_repo, "a.py", c_before, "first")
    target_sha = commit_file(temp_git_repo, "a.py", c_after, "second")

    r1 = get_changed_symbols(temp_git_repo, base_sha, target_sha)
    r2 = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    assert r1 == r2


def test_unsupported_language_fallback(temp_git_repo: Path) -> None:
    # Adding a text file shouldn't break the detector and shouldn't report parsed symbols
    base_sha = commit_file(temp_git_repo, "abc.txt", "hello", "first")
    target_sha = commit_file(temp_git_repo, "abc.txt", "world", "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)
    assert len(result.changed_symbols) == 0
    assert len(result.opaque_files) == 1
    assert result.opaque_files[0].reason == OpaqueFileFallbackReason.UNSUPPORTED_LANGUAGE

def test_parser_failure_fallback(temp_git_repo: Path) -> None:
    # A malformed python file
    base_sha = commit_file(temp_git_repo, "bad.py", "def foo(): pass", "first")
    target_sha = commit_file(temp_git_repo, "bad.py", "def foo():\n  pass\nthis is clearly not python syntax!!", "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)
    assert len(result.changed_symbols) == 0
    assert len(result.opaque_files) == 1
    assert result.opaque_files[0].reason == OpaqueFileFallbackReason.PARSER_FAILURE


def test_pure_formatting_changes(temp_git_repo: Path) -> None:
    # Formatting changes inside a symbol body WILL be detected as MODIFIED
    # because of our explicit fallback to chunk-aligned extraction for semantics.
    code_before = """
def add(a, b):
    return a+b

def sub(a, b):
    return a-b
"""
    # we add a line before `sub` which shifts lines, but `sub` internal text shouldn't change
    code_after = """
def add(a, b):
    return a+b


def sub(a, b):
    return a-b
"""
    base_sha = commit_file(temp_git_repo, "c.py", code_before, "first")
    target_sha = commit_file(temp_git_repo, "c.py", code_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)

    # `add` remains identical in location and body.
    # `sub` has identical body, but moved location, producing new UUID.
    assert len(result.changed_symbols) == 1
    assert result.changed_symbols[0].name == "sub"
    assert result.changed_symbols[0].change_type == SymbolChangeType.IDENTITY_ONLY
    assert result.changed_symbols[0].previous_symbol_id is not None
    # Depending on Phase 2 implementation, symbol UUID might not incorporate loc,
    # so we just assert IDENTITY_ONLY correctly propagated.

def test_location_movement_and_body_modification(temp_git_repo: Path) -> None:
    code_before = """
def myfunc():
    return 1
"""
    code_after = """
# some header

def myfunc():
    return 2
"""
    base_sha = commit_file(temp_git_repo, "d.py", code_before, "first")
    target_sha = commit_file(temp_git_repo, "d.py", code_after, "second")

    result = get_changed_symbols(temp_git_repo, base_sha, target_sha)
    assert len(result.changed_symbols) == 1
    sym = result.changed_symbols[0]
    assert sym.change_type == SymbolChangeType.MODIFIED
    assert sym.previous_symbol_id is not None
