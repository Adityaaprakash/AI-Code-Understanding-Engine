import subprocess
from pathlib import Path

import pytest

from backend.git.diff_engine import GitDiffEngine
from backend.git.exceptions import GitError, InvalidCommitError, InvalidRepositoryError
from backend.git.models import ChangeType


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Creates a temporary Git repository and returns its path."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Initialize repository
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


def run_git(repo_path: Path, *args: str) -> str:
    """Helper to run git commands in the test repo."""
    res = subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def commit_file(repo_path: Path, path: str, content: str, message: str) -> str:
    """Helper to write a file and commit it, returning the commit SHA."""
    file_path = repo_path / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    run_git(repo_path, "add", path)
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def delete_file_and_commit(repo_path: Path, path: str, message: str) -> str:
    """Helper to delete a file and commit."""
    file_path = repo_path / path
    file_path.unlink()

    run_git(repo_path, "add", path)
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def test_invalid_repository(tmp_path: Path) -> None:
    engine = GitDiffEngine()
    with pytest.raises(InvalidRepositoryError):
        engine.get_diff(str(tmp_path), "HEAD", "HEAD")


def test_invalid_base_commit(temp_git_repo: Path) -> None:
    commit_file(temp_git_repo, "test.txt", "hello", "init")
    target_sha = run_git(temp_git_repo, "rev-parse", "HEAD")

    engine = GitDiffEngine()
    with pytest.raises(InvalidCommitError):
        engine.get_diff(str(temp_git_repo), "invalid_sha", target_sha)


def test_invalid_target_commit(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "test.txt", "hello", "init")

    engine = GitDiffEngine()
    with pytest.raises(InvalidCommitError):
        engine.get_diff(str(temp_git_repo), base_sha, "invalid_sha")


def test_same_commit(temp_git_repo: Path) -> None:
    commit_sha = commit_file(temp_git_repo, "test.txt", "hello", "init")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), commit_sha, commit_sha)

    assert result.changed_files == []
    assert result.base_commit == commit_sha
    assert result.target_commit == commit_sha


def test_one_added_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.txt", "A", "first")
    target_sha = commit_file(temp_git_repo, "b.txt", "B", "second")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "b.txt"
    assert result.changed_files[0].change_type == ChangeType.ADDED
    assert result.changed_files[0].previous_path is None


def test_one_modified_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.txt", "A", "first")
    target_sha = commit_file(temp_git_repo, "a.txt", "A modified", "second")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "a.txt"
    assert result.changed_files[0].change_type == ChangeType.MODIFIED
    assert result.changed_files[0].previous_path is None


def test_one_deleted_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.txt", "A", "first")
    target_sha = delete_file_and_commit(temp_git_repo, "a.txt", "delete")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "a.txt"
    assert result.changed_files[0].change_type == ChangeType.DELETED
    assert result.changed_files[0].previous_path is None


def test_one_renamed_file(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "old.txt", "hello rename", "first")

    run_git(temp_git_repo, "mv", "old.txt", "new.txt")
    run_git(temp_git_repo, "commit", "-m", "rename")
    target_sha = run_git(temp_git_repo, "rev-parse", "HEAD")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "new.txt"
    assert result.changed_files[0].change_type == ChangeType.RENAMED
    assert result.changed_files[0].previous_path == "old.txt"


def test_multiple_simultaneous_changes_and_ordering(temp_git_repo: Path) -> None:
    commit_file(temp_git_repo, "to_delete.txt", "D", "init D")
    commit_file(temp_git_repo, "to_modify.txt", "M1", "init M")
    base_sha = commit_file(
        temp_git_repo, "to_rename.txt", "long content to force rename detection in git", "init R"
    )

    # Target commit: A added, D deleted, M modified, R renamed
    (temp_git_repo / "to_delete.txt").unlink()
    (temp_git_repo / "to_add.txt").write_text("A")
    (temp_git_repo / "to_modify.txt").write_text("M2")
    run_git(temp_git_repo, "mv", "to_rename.txt", "renamed.txt")
    run_git(temp_git_repo, "add", "-A")
    run_git(temp_git_repo, "commit", "-m", "multi")
    target_sha = run_git(temp_git_repo, "rev-parse", "HEAD")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 4

    # Test deterministic ordering by path
    paths = [f.path for f in result.changed_files]
    assert paths == ["renamed.txt", "to_add.txt", "to_delete.txt", "to_modify.txt"]

    f_renamed = result.changed_files[0]
    assert f_renamed.path == "renamed.txt"
    assert f_renamed.change_type == ChangeType.RENAMED

    f_added = result.changed_files[1]
    assert f_added.path == "to_add.txt"
    assert f_added.change_type == ChangeType.ADDED

    f_deleted = result.changed_files[2]
    assert f_deleted.path == "to_delete.txt"
    assert f_deleted.change_type == ChangeType.DELETED

    f_modified = result.changed_files[3]
    assert f_modified.path == "to_modify.txt"
    assert f_modified.change_type == ChangeType.MODIFIED


def test_nested_paths(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "src/main/java/Main.java", "class Main {}", "first")
    target_sha = commit_file(temp_git_repo, "src/main/java/Utils.java", "class Utils {}", "second")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "src/main/java/Utils.java"


def test_paths_containing_spaces(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "file with spaces.txt", "spaces", "first")
    target_sha = commit_file(temp_git_repo, "file with spaces.txt", "spaces modified", "second")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    assert result.changed_files[0].path == "file with spaces.txt"
    assert result.changed_files[0].change_type == ChangeType.MODIFIED


def test_unicode_paths(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "résumé.txt", "cv", "first")
    target_sha = commit_file(temp_git_repo, "résumé.txt", "cv modified", "second")

    engine = GitDiffEngine()
    result = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert len(result.changed_files) == 1
    # Note: git might quote unicode paths depending on core.quotePath config.
    # The -z option outputs everything literally (no quotes, no escapes) in diff-tree.
    assert result.changed_files[0].path == "résumé.txt"


def test_unsupported_git_status() -> None:
    engine = GitDiffEngine()
    with pytest.raises(GitError, match="Unsupported Git change status: X"):
        engine._get_change_type("X")


def test_determinism_repeated_calls(temp_git_repo: Path) -> None:
    base_sha = commit_file(temp_git_repo, "a.txt", "A", "first")
    target_sha = commit_file(temp_git_repo, "a.txt", "B", "second")

    engine = GitDiffEngine()
    result1 = engine.get_diff(str(temp_git_repo), base_sha, target_sha)
    result2 = engine.get_diff(str(temp_git_repo), base_sha, target_sha)

    assert result1 == result2
    assert result1.changed_files[0].path == "a.txt"
    # test no UUIDs or random timestamps were included in equality check
