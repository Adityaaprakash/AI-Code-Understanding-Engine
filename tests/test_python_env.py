# tests/test_python_env.py
"""
TASK-1B — Python environment smoke test.

Verifies that:
- The Python runtime is the expected version (3.12).
- Key runtime dependencies are importable (they are installed).
- The backend package itself is importable.

This test file contains no application logic — it exists only to confirm
that the development environment is correctly set up.
Application tests will be added once application code exists (TASK-1D+).
"""

import sys

import pytest


@pytest.mark.unit
def test_python_version_is_312() -> None:
    """The project requires Python 3.12 as defined in .python-version and pyproject.toml."""
    assert sys.version_info.major == 3, "Expected Python 3"
    assert sys.version_info.minor == 12, (
        f"Expected Python 3.12, got 3.{sys.version_info.minor}. "
        "Ensure you are running tests inside the uv-managed virtual environment."
    )


def test_fastapi_importable() -> None:
    """fastapi must be installed and importable."""
    import fastapi

    assert fastapi.__version__, "fastapi version string should be non-empty"


def test_pydantic_importable() -> None:
    """pydantic v2 must be installed and importable."""
    import pydantic

    assert int(pydantic.__version__.split(".")[0]) >= 2, "pydantic >= 2 required"


def test_sqlalchemy_importable() -> None:
    """sqlalchemy must be installed and importable."""
    import sqlalchemy

    assert sqlalchemy.__version__, "sqlalchemy version string should be non-empty"


def test_alembic_importable() -> None:
    """alembic must be installed and importable."""
    import alembic

    assert alembic.__version__, "alembic version string should be non-empty"


def test_asyncpg_importable() -> None:
    """asyncpg must be installed and importable."""
    import asyncpg

    assert asyncpg.__version__, "asyncpg version string should be non-empty"


def test_httpx_importable() -> None:
    """httpx must be installed and importable."""
    import httpx

    assert httpx.__version__, "httpx version string should be non-empty"


def test_backend_package_importable() -> None:
    """The backend package must be importable as a proper Python package."""
    import backend

    # The package exists; __file__ points to backend/__init__.py
    assert backend.__file__ is not None
