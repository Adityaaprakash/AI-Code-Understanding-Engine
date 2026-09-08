import logging
import subprocess
from pathlib import Path

from backend.git.contracts import GitDiffEngineContract
from backend.git.exceptions import GitError, InvalidCommitError, InvalidRepositoryError
from backend.git.models import ChangedFile, ChangeType, GitDiffResult

logger = logging.getLogger(__name__)


class GitDiffEngine(GitDiffEngineContract):
    """Implementation of GitDiffEngineContract using git subprocess."""

    def _get_change_type(self, status: str) -> ChangeType:
        if status.startswith("A"):
            return ChangeType.ADDED
        if status.startswith("M"):
            return ChangeType.MODIFIED
        if status.startswith("D"):
            return ChangeType.DELETED
        if status.startswith("R"):
            return ChangeType.RENAMED
        if status.startswith("T"):
            return ChangeType.TYPE_CHANGED
        raise GitError(f"Unsupported Git change status: {status}")

    def _resolve_commit(self, repo_path: str, commit_ref: str) -> str:
        """Fully resolve a commit ref to its full SHA to ensure determinism and validation."""
        cmd = ["git", "rev-parse", "-q", "--verify", f"{commit_ref}^{{commit}}"]
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            raise GitError(f"Failed to execute git rev-parse: {e}") from e

        if result.returncode != 0:
            raise InvalidCommitError(f"Commit '{commit_ref}' is invalid or does not exist.")

        return result.stdout.strip()

    def _check_repo(self, repo_path: str) -> None:
        """Verify the path is a valid git repository."""
        path = Path(repo_path)
        if not path.is_dir():
            raise InvalidRepositoryError(f"Directory does not exist: {repo_path}")

        cmd = ["git", "rev-parse", "--is-inside-work-tree"]
        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as e:
            raise GitError(f"Failed to check git repository: {e}") from e

        if result.returncode != 0:
            raise InvalidRepositoryError(f"Not a valid git repository: {repo_path}")

    def get_diff(self, repository_path: str, base_commit: str, target_commit: str) -> GitDiffResult:
        self._check_repo(repository_path)

        base_sha = self._resolve_commit(repository_path, base_commit)
        target_sha = self._resolve_commit(repository_path, target_commit)

        if base_sha == target_sha:
            return GitDiffResult(
                repository_path=repository_path,
                base_commit=base_sha,
                target_commit=target_sha,
                changed_files=[],
            )

        cmd = ["git", "diff-tree", "-r", "-z", "--raw", "-M", base_sha, target_sha]

        try:
            result = subprocess.run(
                cmd,
                cwd=repository_path,
                capture_output=True,
                text=False,
                check=False,
            )
        except Exception as e:
            raise GitError(f"Failed to execute git diff-tree: {e}") from e

        if result.returncode != 0:
            err = result.stderr.decode("utf-8", "replace")
            raise GitError(f"Git diff-tree failed with code {result.returncode}: {err}")

        changed_files = self._parse_diff_tree_z(result.stdout)

        # Sort files to ensure absolute determinism as requested
        changed_files = sorted(changed_files, key=lambda f: f.path)

        return GitDiffResult(
            repository_path=repository_path,
            base_commit=base_sha,
            target_commit=target_sha,
            changed_files=changed_files,
        )

    def _parse_diff_tree_z(self, stdout_bytes: bytes) -> list[ChangedFile]:
        tokens = stdout_bytes.split(b"\0")

        if not tokens or not tokens[0]:
            return []

        changed_files = []
        i = 0
        while i < len(tokens):
            meta = tokens[i].decode("utf-8", "replace")
            # If the output ends with \0, the last token is an empty string
            if not meta:
                break

            # diff-tree raw output entries start with a colon (e.g. :100644 100644 ...).
            # If the format contains any unexpected leading data, we advance until we find the start of a record.
            if not meta.startswith(":"):
                idx = meta.find(":")
                if idx != -1:
                    meta = meta[idx:]
                else:
                    i += 1
                    continue

            parts = meta.split(" ")
            if len(parts) < 5:
                # Malformed meta
                i += 1
                continue

            old_blob = parts[2]
            new_blob = parts[3]
            status_code = parts[4]

            # The path is the NEXT token
            i += 1
            if i >= len(tokens):
                break

            path1 = tokens[i].decode("utf-8", "replace")

            change_type = self._get_change_type(status_code)

            final_old_blob = None if old_blob.startswith("0000000") else old_blob
            final_new_blob = None if new_blob.startswith("0000000") else new_blob

            if status_code.startswith("R") or status_code.startswith("C"):
                # Renamed or copied -> there is a second path expected
                i += 1
                if i >= len(tokens):
                    break
                path2 = tokens[i].decode("utf-8", "replace")

                changed_files.append(
                    ChangedFile(
                        path=path2,
                        change_type=change_type,
                        previous_path=path1,
                        old_blob_id=final_old_blob,
                        new_blob_id=final_new_blob,
                    )
                )
            else:
                changed_files.append(
                    ChangedFile(
                        path=path1,
                        change_type=change_type,
                        previous_path=None,
                        old_blob_id=final_old_blob,
                        new_blob_id=final_new_blob,
                    )
                )

            i += 1

        return changed_files
