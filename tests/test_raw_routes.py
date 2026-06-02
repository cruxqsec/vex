import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

from vex_cli.app import create_app
from vex_cli.dependencies import get_raw_db
from vex_cli.models.orm import RawRequestORM, RawResponseORM
from vex_cli.models.pydantic import RawRequest, RawResponse
from vex_cli.errors import NotFoundError


def make_raw_request(id: UUID | None = None):
    return RawRequest(
        id=uuid4() if id is None else id,
        data=b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n",
    )


def make_raw_response(id: UUID | None = None):
    return RawResponse(
        id=uuid4() if id is None else id,
        data=b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>",
    )


def make_raw_request_orm(id: UUID | None = None):
    orm = RawRequestORM()
    orm.id = uuid4() if id is None else id
    orm.data = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
    return orm


def make_raw_response_orm(id: UUID | None = None):
    orm = RawResponseORM()
    orm.id = uuid4() if id is None else id
    orm.data = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>"
    return orm


@pytest_asyncio.fixture
async def mock_raw_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(mock_raw_db):
    app = create_app()
    app.dependency_overrides[get_raw_db] = lambda: mock_raw_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# --- GET /raw/request/ ---


@pytest.mark.asyncio
async def test_get_all_raw_requests_returns_200(client, mock_raw_db):
    mock_raw_db.get_all.return_value = [make_raw_request()]

    response = await client.get("/api/raw/request/")

    assert response.status_code == 200
    mock_raw_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_raw_requests_returns_empty_list(client, mock_raw_db):
    mock_raw_db.get_all.return_value = []

    response = await client.get("/api/raw/request/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_raw_requests_with_pagination(client, mock_raw_db):
    mock_raw_db.get_all.return_value = [make_raw_request()]

    response = await client.get("/api/raw/request/?skip=10&size=20")

    assert response.status_code == 200
    mock_raw_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_raw_requests_rejects_invalid_size(client, mock_raw_db):
    response = await client.get("/api/raw/request/?size=999")

    assert response.status_code == 422


# --- GET /raw/request/{id} ---


@pytest.mark.asyncio
async def test_get_raw_request_by_id_returns_200(client, mock_raw_db):
    flow_id = uuid4()
    mock_raw_db.get.return_value = make_raw_request(id=flow_id)

    response = await client.get(f"/api/raw/request/{flow_id}")

    assert response.status_code == 200
    mock_raw_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_raw_request_by_id_not_found(client, mock_raw_db):
    flow_id = uuid4()
    mock_raw_db.get.side_effect = NotFoundError("Not found")

    response = await client.get(f"/api/raw/request/{flow_id}")

    assert response.status_code == 404


# --- GET /raw/response/ ---


@pytest.mark.asyncio
async def test_get_all_raw_responses_returns_200(client, mock_raw_db):
    mock_raw_db.get_all.return_value = [make_raw_response()]

    response = await client.get("/api/raw/response/")

    assert response.status_code == 200
    mock_raw_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_raw_responses_returns_empty_list(client, mock_raw_db):
    mock_raw_db.get_all.return_value = []

    response = await client.get("/api/raw/response/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_raw_responses_with_pagination(client, mock_raw_db):
    mock_raw_db.get_all.return_value = [make_raw_response()]

    response = await client.get("/api/raw/response/?skip=10&size=20")

    assert response.status_code == 200
    mock_raw_db.get_all.assert_called_once()


# --- GET /raw/response/{id} ---


@pytest.mark.asyncio
async def test_get_raw_response_by_id_returns_200(client, mock_raw_db):
    flow_id = uuid4()
    mock_raw_db.get.return_value = make_raw_response(id=flow_id)

    response = await client.get(f"/api/raw/response/{flow_id}")

    assert response.status_code == 200
    mock_raw_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_raw_response_by_id_not_found(client, mock_raw_db):
    flow_id = uuid4()
    mock_raw_db.get.side_effect = NotFoundError("Not found")

    response = await client.get(f"/api/raw/response/{flow_id}")

    assert response.status_code == 404
