# backend/services/index_version_manager.py
import uuid

from sqlalchemy.orm import Session

from backend.db.models.index_version import IndexVersion
from backend.db.models.repository import Repository


class IndexVersionManager:
    """Manages the lifecycle of Index Versions for repositories, ensuring consistency."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_version(
        self, repository_id: uuid.UUID, job_id: uuid.UUID, commit_sha: str, kind: str
    ) -> IndexVersion:
        """Create a new logical version in BUILDING state."""
        version = IndexVersion(
            repository_id=repository_id,
            job_id=job_id,
            commit_sha=commit_sha,
            kind=kind,
            status="building",
        )
        self.session.add(version)
        self.session.flush()
        return version

    def set_ready(self, version_id: uuid.UUID) -> IndexVersion:
        """Mark as READY and point the Repository's active retrieval index to this version."""
        version = self.session.get(IndexVersion, version_id)
        if not version:
            raise ValueError(f"IndexVersion {version_id} not found.")

        version.status = "ready"

        repo = self.session.get(Repository, version.repository_id)
        if repo:
            repo.active_index_version_id = version.id

        self.session.flush()
        return version

    def set_failed(self, version_id: uuid.UUID) -> IndexVersion:
        """Mark as FAILED. Never expose as the active retrieval version."""
        version = self.session.get(IndexVersion, version_id)
        if not version:
            raise ValueError(f"IndexVersion {version_id} not found.")

        version.status = "failed"
        self.session.flush()
        return version

    def get_active_commit_sha(self, repository_id: uuid.UUID) -> str | None:
        """Get the commit SHA of the currently active, READY index version."""
        repo = self.session.get(Repository, repository_id)
        if not repo or not repo.active_index_version_id:
            return None

        active_version = self.session.get(IndexVersion, repo.active_index_version_id)
        if not active_version or active_version.status != "ready":
            return None

        return active_version.commit_sha
