import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from os import getpid

from vex_cli.app import create_app


@pytest_asyncio.fixture
async def client():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health_check_returns_200(client):
    response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_returns_healthy_status(client):
    response = await client.get("/health")

    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_returns_process_id(client):
    response = await client.get("/health")

    data = response.json()
    assert "pid" in data
    assert isinstance(data["pid"], int)
    assert data["pid"] == getpid()


@pytest.mark.asyncio
async def test_health_check_returns_version(client):
    response = await client.get("/health")

    data = response.json()
    assert "version" in data
    assert isinstance(data["version"], str)


@pytest.mark.asyncio
async def test_swagger_docs_redirect_returns_307(client):
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307


@pytest.mark.asyncio
async def test_swagger_docs_redirect_points_to_docs(client):
    response = await client.get("/", follow_redirects=False)

    assert response.headers["location"] == "/docs"


@pytest.mark.asyncio
async def test_swagger_docs_redirect_follows_to_docs(client):
    response = await client.get("/", follow_redirects=True)

    assert response.status_code == 200
