# tests/test_fastapi_app.py
"""TASK-1D verification suite for FastAPI foundation."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from backend.core.errors import AppException
from backend.db.session import get_db_session
from backend.main import app, create_app


@pytest.fixture
def client() -> TestClient:
    """TestClient fixture for FastAPI application testing."""
    return TestClient(app)


def test_app_imports_and_instantiates() -> None:
    """Application factory produces a valid FastAPI application instance."""
    test_app = create_app()
    assert isinstance(test_app, FastAPI)
    assert test_app.title == "CodeLens AI — AI Code Understanding Engine"
    assert test_app.version == "0.1.0"


def test_health_endpoint(client: TestClient) -> None:
    """GET /health returns HTTP 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_api_v1_router_registration(client: TestClient) -> None:
    """The /api/v1 router is registered and responds to root GET request."""
    response = client.get("/api/v1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "CodeLens AI API v1"
    assert data["status"] == "active"
    assert data["version"] == "v1"


def test_openapi_schema(client: TestClient) -> None:
    """Application exposes valid OpenAPI schema at /openapi.json."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["info"]["title"] == "CodeLens AI — AI Code Understanding Engine"
    assert "/health" in schema["paths"]
    assert "/api/v1" in schema["paths"]


def test_docs_and_redoc_endpoints(client: TestClient) -> None:
    """Application exposes Swagger /docs and ReDoc /redoc UI pages."""
    docs_response = client.get("/docs")
    assert docs_response.status_code == status.HTTP_200_OK
    assert "swagger-ui" in docs_response.text.lower()

    redoc_response = client.get("/redoc")
    assert redoc_response.status_code == status.HTTP_200_OK
    assert "redoc" in redoc_response.text.lower()


def test_cors_headers(client: TestClient) -> None:
    """CORS middleware attaches headers for configured origins."""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_custom_app_exception_handler() -> None:
    """Custom AppException is handled and formatted into standardized error response."""
    test_app = create_app()

    @test_app.get("/test-error")
    async def trigger_error() -> None:
        raise AppException(
            message="Item not found",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"item_id": 123},
        )

    test_client = TestClient(test_app)
    response = test_client.get("/test-error")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Item not found",
            "details": {"item_id": 123},
        }
    }


def test_unhandled_exception_handler() -> None:
    """Unhandled server exceptions return HTTP 500 without leaking tracebacks."""
    test_app = create_app()

    @test_app.get("/test-500")
    async def trigger_crash() -> None:
        raise RuntimeError("Secret database crash details")

    test_client = TestClient(test_app, raise_server_exceptions=False)
    response = test_client.get("/test-500")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "An unexpected internal server error occurred"
    assert data["error"]["details"] is None
    assert "Secret database crash" not in response.text


def test_database_session_dependency_injection_boundary() -> None:
    """Verify get_db_session can be referenced as a FastAPI dependency."""
    test_app = create_app()

    @test_app.get("/test-db-dep")
    async def dummy_endpoint(_session: AsyncGenerator = Depends(get_db_session)) -> dict[str, str]:
        return {"status": "wired"}

    # Route definition and dependency inspection check
    route = next(r for r in test_app.routes if getattr(r, "path", None) == "/test-db-dep")
    assert route is not None
