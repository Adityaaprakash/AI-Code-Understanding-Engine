from abc import ABC, abstractmethod

from backend.git.models import GitDiffResult


class GitDiffEngineContract(ABC):
    """Abstract contract for computing file-level differences between two Git commits."""

    @abstractmethod
    def get_diff(self, repository_path: str, base_commit: str, target_commit: str) -> GitDiffResult:
        """
        Compute the diff between base_commit and target_commit.

        Args:
            repository_path: The filesystem path to the Git repository.
            base_commit: The starting commit SHA (or ref).
            target_commit: The ending commit SHA (or ref).

        Returns:
            GitDiffResult detailing exactly what files changed, their types, and blob metadata.

        Raises:
            InvalidRepositoryError: If the repository_path is not a valid Git repository.
            InvalidCommitError: If either commit reference cannot be resolved.
            GitError: If the diff operation fails for another reason.
        """
        pass
