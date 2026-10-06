import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from vex_cli.app import create_app
from vex_cli.dependencies import get_summaries_db, get_flow_scope
from vex_cli.models.orm import ScopeORM
from vex_cli.models.pydantic import Scope
from vex_cli.errors import NotFoundError


def make_scope_orm(
    id: int = 1,
    name: str = "Test Scope",
    definitions: str = '{"allow": ["192.168.1.1"], "deny": ["10.0.0.1"]}',
):
    scope = ScopeORM()
    scope.id = id
    scope.name = name
    scope.definitions = definitions
    return scope


def make_scope(
    id: int = 1,
    name: str = "Test Scope",
    allow: list = ["192.168.1.1"],
    deny: list = ["10.0.0.1"],
):
    return Scope(id=id, name=name, allow_endpoints=allow, deny_endpoints=deny)


@pytest_asyncio.fixture
async def mock_scope_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def mock_flow_scope():
    return MagicMock()


@pytest_asyncio.fixture
async def client(mock_scope_db, mock_flow_scope):
    app = create_app()
    app.dependency_overrides[get_summaries_db] = lambda: mock_scope_db
    app.dependency_overrides[get_flow_scope] = lambda: mock_flow_scope
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# --- GET /scope/ ---


@pytest.mark.asyncio
async def test_get_all_scopes_returns_200(client, mock_scope_db):
    mock_scope_db.get_all.return_value = [make_scope_orm()]

    response = await client.get("/api/scope/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["allow_endpoints"] == ["192.168.1.1"]
    assert response.json()[0]["deny_endpoints"] == ["10.0.0.1"]
    mock_scope_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_scopes_returns_empty_list(client, mock_scope_db):
    mock_scope_db.get_all.return_value = []

    response = await client.get("/api/scope/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_scopes_rejects_invalid_size(client, mock_scope_db):
    response = await client.get("/api/scope/?size=999")

    assert response.status_code == 422


# --- GET /scope/{id} ---


@pytest.mark.asyncio
async def test_get_scope_returns_200(client, mock_scope_db):
    mock_scope_db.get.return_value = make_scope_orm(id=1)

    response = await client.get("/api/scope/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["allow_endpoints"] == ["192.168.1.1"]
    assert response.json()["deny_endpoints"] == ["10.0.0.1"]
    mock_scope_db.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_scope_not_found(client, mock_scope_db):
    mock_scope_db.get.side_effect = NotFoundError("Scope not found")

    response = await client.get("/api/scope/99")

    assert response.status_code == 404


# --- POST /scope/ ---


@pytest.mark.asyncio
async def test_create_scope_returns_201(client, mock_scope_db):
    mock_scope_db.create.return_value = make_scope_orm(id=1)
    payload = {
        "name": "Test Scope",
        "allow_endpoints": ["192.168.1.1"],
        "deny_endpoints": ["10.0.0.1"],
    }

    response = await client.post("/api/scope/", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Test Scope"
    assert response.json()["allow_endpoints"] == ["192.168.1.1"]
    assert response.json()["deny_endpoints"] == ["10.0.0.1"]
    mock_scope_db.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_scope_invalid_payload(client, mock_scope_db):
    response = await client.post("/api/scope/", json={"bad": "data"})

    assert response.status_code == 422


# --- PUT /scope/ ---


@pytest.mark.asyncio
async def test_update_scope_returns_202(client, mock_scope_db):
    mock_scope_db.update.return_value = None
    payload = {
        "id": 1,
        "name": "Updated Scope",
        "allow_endpoints": ["192.168.1.1"],
        "deny_endpoints": [],
    }

    response = await client.put("/api/scope/", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_update_scope_not_found(client, mock_scope_db):
    mock_scope_db.update.side_effect = NotFoundError("Not found")

    payload = {
        "id": 99,
        "name": "Not Found",
        "allow_endpoints": [],
        "deny_endpoints": [],
    }
    response = await client.put("/api/scope/", json=payload)

    assert response.status_code == 404


# --- DELETE /scope/{id} ---


@pytest.mark.asyncio
async def test_delete_scope_returns_202(client, mock_scope_db):
    mock_scope_db.delete.return_value = None

    response = await client.delete("/api/scope/1")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_scope_not_found(client, mock_scope_db):
    mock_scope_db.delete.side_effect = NotFoundError("Not found")

    response = await client.delete("/api/scope/99")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_active_scope_clears_it(client, mock_scope_db, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = make_scope(id=5)

    response = await client.delete("/api/scope/5")

    assert response.status_code == 202
    mock_flow_scope.set_active_scope.assert_called_once_with(None)


@pytest.mark.asyncio
async def test_delete_inactive_scope_keeps_active(client, mock_scope_db, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = make_scope(id=2)

    response = await client.delete("/api/scope/1")

    assert response.status_code == 202
    mock_flow_scope.set_active_scope.assert_not_called()


@pytest.mark.asyncio
async def test_delete_scope_no_active_is_noop(client, mock_scope_db, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = None

    response = await client.delete("/api/scope/1")

    assert response.status_code == 202
    mock_flow_scope.set_active_scope.assert_not_called()


@pytest.mark.asyncio
async def test_update_active_scope_updates_it(client, mock_scope_db, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = make_scope(id=1)
    payload = {
        "id": 1,
        "name": "Renamed",
        "allow_endpoints": [],
        "deny_endpoints": [],
    }

    response = await client.put("/api/scope/", json=payload)

    assert response.status_code == 202
    mock_flow_scope.set_active_scope.assert_called_once()
    updated = mock_flow_scope.set_active_scope.call_args[0][0]
    assert updated.name == "Renamed"


@pytest.mark.asyncio
async def test_update_inactive_scope_leaves_active(client, mock_scope_db, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = make_scope(id=2)
    payload = {
        "id": 1,
        "name": "Renamed",
        "allow_endpoints": [],
        "deny_endpoints": [],
    }

    response = await client.put("/api/scope/", json=payload)

    assert response.status_code == 202
    mock_flow_scope.set_active_scope.assert_not_called()


# --- POST /scope/set/{id} ---


@pytest.mark.asyncio
async def test_set_scope_returns_202(client, mock_scope_db, mock_flow_scope):
    mock_scope_db.get.return_value = make_scope_orm(id=1)

    response = await client.post("/api/scope/set/1")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"
    mock_flow_scope.set_active_scope.assert_called_once()


@pytest.mark.asyncio
async def test_set_scope_not_found_returns_failure(client, mock_scope_db):
    mock_scope_db.get.side_effect = NotFoundError("Not found")

    response = await client.post("/api/scope/set/99")

    assert response.status_code == 404


# --- POST /scope/unset/ ---


@pytest.mark.asyncio
async def test_unset_scope_returns_202(client, mock_flow_scope):
    response = await client.post("/api/scope/unset/")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"
    mock_flow_scope.set_active_scope.assert_called_once_with(None)


# --- GET /scope/active/{id} ---


@pytest.mark.asyncio
async def test_get_active_scope_returns_200(client, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = Scope(
        id=1, name="Active Scope", allow_endpoints=["192.168.1.1"], deny_endpoints=[]
    )

    response = await client.get("/api/scope/active/")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_active_scope_returns_none_when_unset(client, mock_flow_scope):
    mock_flow_scope.get_active_scope.return_value = None

    response = await client.get("/api/scope/active/")

    assert response.status_code == 200
    assert response.json() is None


# --- GET /api/scope/count ---


@pytest.mark.asyncio
async def test_count_scopes_returns_count(client, mock_scope_db):
    mock_scope_db.count.return_value = 3

    response = await client.get("/api/scope/count")

    assert response.status_code == 200
    assert response.json() == {"count": 3}
    mock_scope_db.count.assert_called_once()


@pytest.mark.asyncio
async def test_count_scopes_empty_returns_zero(client, mock_scope_db):
    mock_scope_db.count.return_value = 0

    response = await client.get("/api/scope/count")

    assert response.status_code == 200
    assert response.json() == {"count": 0}
