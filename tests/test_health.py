# tests/test_health.py
"""Health endpoint smoke test suite using reusable fixtures."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
@pytest.mark.unit
async def test_health_endpoint_async(async_client: AsyncClient) -> None:
    """Async test verifying GET /health returns HTTP 200 and status ok."""
    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


@pytest.mark.api
@pytest.mark.unit
def test_health_endpoint_sync(sync_client: TestClient) -> None:
    """Sync test verifying GET /health returns HTTP 200 and status ok."""
    response = sync_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}
