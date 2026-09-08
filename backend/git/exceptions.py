from backend.core.errors import AppException


class GitError(AppException):
    """Base exception for Git operations."""

    def __init__(
        self,
        message: str,
        code: str = "GIT_ERROR",
        status_code: int = 500,
        details: dict | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code, details=details)


class InvalidRepositoryError(GitError):
    """Raised when the specified path is not a valid Git repository."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="INVALID_REPOSITORY", status_code=400, details=details)


class InvalidCommitError(GitError):
    """Raised when a specified commit does not exist or is invalid."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, code="INVALID_COMMIT", status_code=400, details=details)
