import uuid

from sqlalchemy.orm import Session

from backend.db.models.job import Job
from backend.db.models.repository import Repository
from backend.services.index_version_manager import IndexVersionManager


def test_index_version_manager_lifecycle(db_session: Session) -> None:
    manager = IndexVersionManager(db_session)

    # 1. Setup repository and job
    repo_id = uuid.uuid4()
    job_id = uuid.uuid4()
    repo = Repository(id=repo_id, name="test-repo", source_type="local")
    job = Job(id=job_id, repository_id=repo_id, kind="full_index")
    db_session.add(repo)
    db_session.add(job)
    db_session.flush()

    # 2. Check no active version initially
    assert manager.get_active_commit_sha(repo_id) is None

    # 3. Create a BUILDING version
    commit_sha = "abc123def456"
    version_1 = manager.create_version(
        repository_id=repo_id, job_id=job_id, commit_sha=commit_sha, kind="full"
    )

    # Still shouldn't be active since it's building
    assert manager.get_active_commit_sha(repo_id) is None
    assert version_1.status == "building"

    # 4. Fail the version
    manager.set_failed(version_1.id)
    assert version_1.status == "failed"
    assert manager.get_active_commit_sha(repo_id) is None

    # 5. Create a new version for same commit?
    # Wait, the unique constraint would block creating a second version for the exact same repository_id and commit_sha.
    # The requirement is: "There must not be two simultaneously valid logical versions for Repository A + abc123".
    # So we must use a different commit_sha or assume that `kind="incremental"` might reuse the same commit_sha?
    # Actually wait, `IndexVersion` table has a `UniqueConstraint("repository_id", "commit_sha")`.
    # Therefore, you cannot simply retry indexing the exact same commit_sha in a new version record without deleting the old one. We will create for a new commit.
    commit_sha_2 = "def456ghi789"
    version_2 = manager.create_version(
        repository_id=repo_id, job_id=job_id, commit_sha=commit_sha_2, kind="full"
    )

    # 6. Set ready
    manager.set_ready(version_2.id)

    # Now it should be active
    assert version_2.status == "ready"
    assert manager.get_active_commit_sha(repo_id) == commit_sha_2

    # Check repository state directly
    repo_reloaded = db_session.get(Repository, repo_id)
    assert repo_reloaded is not None
    assert repo_reloaded.active_index_version_id == version_2.id
