# tests/test_fastapi_app.py
"""TASK-1D verification suite for FastAPI foundation."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from backend.core.errors import AppException
from backend.db.session import get_db_session
from backend.main import create_app


@pytest.mark.unit
def test_app_imports_and_instantiates() -> None:
    """Application factory produces a valid FastAPI application instance."""
    test_app = create_app()
    assert isinstance(test_app, FastAPI)
    assert test_app.title == "CodeLens AI — AI Code Understanding Engine"
    assert test_app.version == "0.1.0"


@pytest.mark.api
@pytest.mark.unit
def test_health_endpoint(sync_client: TestClient) -> None:
    """GET /health returns HTTP 200 and {'status': 'ok'}."""
    response = sync_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.api
@pytest.mark.unit
def test_api_v1_router_registration(sync_client: TestClient) -> None:
    """The /api/v1 router is registered and responds to root GET request."""
    response = sync_client.get("/api/v1")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "CodeLens AI API v1"
    assert data["status"] == "active"
    assert data["version"] == "v1"


@pytest.mark.api
@pytest.mark.unit
def test_openapi_schema(sync_client: TestClient) -> None:
    """Application exposes valid OpenAPI schema at /openapi.json."""
    response = sync_client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["info"]["title"] == "CodeLens AI — AI Code Understanding Engine"
    assert "/health" in schema["paths"]
    assert "/api/v1" in schema["paths"]


@pytest.mark.api
@pytest.mark.unit
def test_docs_and_redoc_endpoints(sync_client: TestClient) -> None:
    """Application exposes Swagger /docs and ReDoc /redoc UI pages."""
    docs_response = sync_client.get("/docs")
    assert docs_response.status_code == status.HTTP_200_OK
    assert "swagger-ui" in docs_response.text.lower()

    redoc_response = sync_client.get("/redoc")
    assert redoc_response.status_code == status.HTTP_200_OK
    assert "redoc" in redoc_response.text.lower()


@pytest.mark.api
@pytest.mark.unit
def test_cors_headers(sync_client: TestClient) -> None:
    """CORS middleware attaches headers for configured origins."""
    response = sync_client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
def test_database_session_dependency_injection_boundary() -> None:
    """Verify get_db_session can be referenced as a FastAPI dependency."""
    test_app = create_app()

    @test_app.get("/test-db-dep")
    async def dummy_endpoint(_session: AsyncGenerator = Depends(get_db_session)) -> dict[str, str]:
        return {"status": "wired"}

    # Route definition and dependency inspection check
    route = next(r for r in test_app.routes if getattr(r, "path", None) == "/test-db-dep")
    assert route is not None
