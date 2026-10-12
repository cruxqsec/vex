from vex_cli.models.orm import ScopeORM
from vex_cli.models.pydantic import Scope


async def test_get_all_scopes(client, summary_db, scope_orm):
    for _ in range(3):
        await summary_db.create(scope_orm())

    resp = await client.get("/api/scope/")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_count_scopes(client, summary_db, scope_orm):
    for _ in range(2):
        await summary_db.create(scope_orm())

    resp = await client.get("/api/scope/count")

    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


async def test_get_scope(client, summary_db, scope_orm):
    saved = await summary_db.create(scope_orm(name="prod"))

    resp = await client.get(f"/api/scope/{saved.id}")

    assert resp.status_code == 200
    assert resp.json()["name"] == "prod"
    assert resp.json()["allow_endpoints"] == []


async def test_get_unknown_scope_returns_404(client):
    resp = await client.get("/api/scope/999")

    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


async def test_create_scope(client, summary_db, scope_create):
    resp = await client.post("/api/scope/", json=scope_create.model_dump())

    assert resp.status_code == 201
    body = resp.json()
    assert body["allow_endpoints"] == ["192.168.1.1"]
    row = await summary_db.get(ScopeORM, body["id"])
    assert row.name == "New Scope"


async def test_create_scope_invalid_endpoint(client):
    payload = {
        "name": "bad",
        "allow_endpoints": ["https://evil.com"],
        "deny_endpoints": [],
    }

    resp = await client.post("/api/scope/", json=payload)

    assert resp.status_code == 422


async def test_update_scope(client, summary_db, scope_orm):
    saved = await summary_db.create(scope_orm(name="old"))
    updated = Scope.from_orm(saved).model_copy(update={"name": "new"})

    resp = await client.put("/api/scope/", json=updated.model_dump())

    assert resp.status_code == 202
    assert (await summary_db.get(ScopeORM, saved.id)).name == "new"


async def test_update_scope_syncs_active_scope(
    client, summary_db, scope_orm, flow_scope
):
    saved = await summary_db.create(scope_orm(name="old"))
    active = Scope.from_orm(saved)
    flow_scope.set_active_scope(active)
    updated = active.model_copy(update={"name": "new"})

    await client.put("/api/scope/", json=updated.model_dump())

    assert flow_scope.get_active_scope().name == "new"


async def test_update_scope_leaves_other_active_alone(
    client, summary_db, scope_orm, flow_scope, scope
):
    saved = await summary_db.create(scope_orm())
    flow_scope.set_active_scope(scope)
    updated = Scope.from_orm(saved).model_copy(update={"name": "new"})

    await client.put("/api/scope/", json=updated.model_dump())

    assert flow_scope.get_active_scope().id == scope.id
    assert flow_scope.get_active_scope().name == "Production Scope"


async def test_update_unknown_scope_returns_404(client, scope):
    resp = await client.put("/api/scope/", json=scope.model_dump())

    assert resp.status_code == 404


async def test_delete_active_scope_unsets_it(
    client, summary_db, scope_orm, flow_scope
):
    saved = await summary_db.create(scope_orm())
    flow_scope.set_active_scope(Scope.from_orm(saved))

    resp = await client.delete(f"/api/scope/{saved.id}")

    assert resp.status_code == 202
    assert flow_scope.get_active_scope() is None
    assert await summary_db.count(ScopeORM) == 0


async def test_delete_other_scope_keeps_active(
    client, summary_db, scope_orm, flow_scope, scope
):
    saved = await summary_db.create(scope_orm())
    flow_scope.set_active_scope(scope)

    resp = await client.delete(f"/api/scope/{saved.id}")

    assert resp.status_code == 202
    assert flow_scope.get_active_scope().id == scope.id


async def test_delete_unknown_scope_returns_404(client):
    resp = await client.delete("/api/scope/999")

    assert resp.status_code == 404


async def test_set_scope(client, summary_db, scope_orm, flow_scope):
    saved = await summary_db.create(scope_orm())

    resp = await client.post(f"/api/scope/set/{saved.id}")

    assert resp.status_code == 202
    assert flow_scope.get_active_scope().id == saved.id


async def test_set_unknown_scope_returns_404(client):
    resp = await client.post("/api/scope/set/999")

    assert resp.status_code == 404


async def test_unset_scope(client, flow_scope, scope):
    flow_scope.set_active_scope(scope)

    resp = await client.post("/api/scope/unset/")

    assert resp.status_code == 202
    assert flow_scope.get_active_scope() is None


async def test_active_scope_none(client):
    resp = await client.get("/api/scope/active/")

    assert resp.status_code == 200
    assert resp.json() is None


async def test_active_scope_set(client, flow_scope, scope):
    flow_scope.set_active_scope(scope)

    resp = await client.get("/api/scope/active/")

    assert resp.status_code == 200
    assert resp.json()["name"] == "Production Scope"
    assert resp.json()["id"] == scope.id
