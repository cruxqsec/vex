import pytest

LIST_ROUTES = [
    "/api/raw/request/",
    "/api/raw/response/",
    "/api/scope/",
    "/api/summary/",
    "/api/summary/request/",
    "/api/summary/response/",
]
DB_ROUTES = LIST_ROUTES + ["/api/summary/count", "/api/scope/count"]


@pytest.mark.parametrize("path", DB_ROUTES)
async def test_returns_409_without_active_project(client, db_manager, path):
    db_manager._summaries_db = None
    db_manager._raw_db = None

    resp = await client.get(path)

    assert resp.status_code == 409
    assert resp.json()["error"] == "NoProjectActiveError"


@pytest.mark.parametrize("path", LIST_ROUTES)
@pytest.mark.parametrize("params", [{"skip": -1}, {"size": 0}, {"size": 51}])
async def test_rejects_bad_pagination(client, path, params):
    resp = await client.get(path, params=params)

    assert resp.status_code == 422
