from uuid import uuid4

import pytest_asyncio

from vex_cli.models.orm import (
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
)


@pytest_asyncio.fixture
async def stored_flow(
    summary_db,
    raw_db,
    request_summary_orm,
    response_summary_orm,
    raw_request_orm,
    raw_response_orm,
):
    flow_id = uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id))
    await summary_db.create(response_summary_orm(flow_id=flow_id))
    await raw_db.create(raw_request_orm(id=flow_id))
    await raw_db.create(raw_response_orm(id=flow_id))
    return flow_id


# ---------- request summaries ----------


async def test_get_all_request_summaries(client, summary_db, request_summary_orm):
    for _ in range(3):
        await summary_db.create(request_summary_orm())

    resp = await client.get("/api/summary/request/")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_get_request_summary_by_flow_id(client, summary_db, request_summary_orm):
    saved = await summary_db.create(request_summary_orm())

    resp = await client.get(f"/api/summary/request/{saved.flow_id}")

    assert resp.status_code == 200
    assert resp.json()["flow_id"] == str(saved.flow_id)


async def test_get_unknown_request_summary_returns_404(client):
    resp = await client.get(f"/api/summary/request/{uuid4()}")

    assert resp.status_code == 404


async def test_create_request_summary(client, summary_db, request_summary):
    payload = request_summary().model_dump(mode="json")

    resp = await client.post("/api/summary/request/", json=payload)

    assert resp.status_code == 201
    assert resp.json()["id"] is not None
    assert await summary_db.count(RequestSummaryORM) == 1


async def test_create_request_summary_duplicate_flow_id(client, request_summary):
    payload = request_summary().model_dump(mode="json")
    await client.post("/api/summary/request/", json=payload)

    resp = await client.post("/api/summary/request/", json=payload)

    assert resp.status_code == 409
    assert resp.json()["error"] == "ConflictError"


async def test_update_request_summary(
    client, summary_db, request_summary_orm, request_summary
):
    saved = await summary_db.create(request_summary_orm(host="old.com"))
    updated = request_summary(id=saved.id, flow_id=saved.flow_id, host="new.com")

    resp = await client.put(
        "/api/summary/request/", json=updated.model_dump(mode="json")
    )

    assert resp.status_code == 202
    assert (await summary_db.get(RequestSummaryORM, saved.id)).host == "new.com"


async def test_update_unknown_request_summary_returns_404(client, request_summary):
    payload = request_summary(id=999).model_dump(mode="json")

    resp = await client.put("/api/summary/request/", json=payload)

    assert resp.status_code == 404


async def test_delete_request_summary(client, summary_db, request_summary_orm):
    saved = await summary_db.create(request_summary_orm())

    resp = await client.delete(f"/api/summary/request/{saved.id}")

    assert resp.status_code == 202
    assert await summary_db.count(RequestSummaryORM) == 0


async def test_delete_unknown_request_summary_returns_404(client):
    resp = await client.delete("/api/summary/request/999")

    assert resp.status_code == 404


# ---------- response summaries ----------


async def test_get_response_summary_by_flow_id(
    client, summary_db, response_summary_orm
):
    saved = await summary_db.create(response_summary_orm())

    resp = await client.get(f"/api/summary/response/{saved.flow_id}")

    assert resp.status_code == 200
    assert resp.json()["status_code"] == 200


async def test_create_response_summary(client, summary_db, response_summary):
    payload = response_summary().model_dump(mode="json")

    resp = await client.post("/api/summary/response/", json=payload)

    assert resp.status_code == 201
    assert await summary_db.count(ResponseSummaryORM) == 1


async def test_update_response_summary(
    client, summary_db, response_summary_orm, response_summary
):
    saved = await summary_db.create(response_summary_orm(status_code=200))
    updated = response_summary(id=saved.id, flow_id=saved.flow_id, status_code=404)

    resp = await client.put(
        "/api/summary/response/", json=updated.model_dump(mode="json")
    )

    assert resp.status_code == 202
    assert (await summary_db.get(ResponseSummaryORM, saved.id)).status_code == 404


async def test_delete_response_summary(client, summary_db, response_summary_orm):
    saved = await summary_db.create(response_summary_orm())

    resp = await client.delete(f"/api/summary/response/{saved.id}")

    assert resp.status_code == 202
    assert await summary_db.count(ResponseSummaryORM) == 0


# ---------- full flow summaries ----------


async def test_get_all_full_summaries(client, stored_flow):
    resp = await client.get("/api/summary/")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["flow_id"] == str(stored_flow)
    assert body[0]["status_code"] == 200


async def test_get_full_summary_without_response(
    client, summary_db, request_summary_orm
):
    saved = await summary_db.create(request_summary_orm())

    resp = await client.get(f"/api/summary/{saved.flow_id}")

    assert resp.status_code == 200
    assert resp.json()["status_code"] is None


async def test_get_full_summary_by_id(client, stored_flow):
    resp = await client.get(f"/api/summary/{stored_flow}")

    assert resp.status_code == 200
    assert resp.json()["flow_id"] == str(stored_flow)


async def test_get_unknown_full_summary_returns_404(client):
    resp = await client.get(f"/api/summary/{uuid4()}")

    assert resp.status_code == 404


async def test_count_flows(client, stored_flow):
    resp = await client.get("/api/summary/count")

    assert resp.status_code == 200
    assert resp.json() == {"count": 1}


async def test_delete_flow_removes_everything(client, summary_db, raw_db, stored_flow):
    resp = await client.delete(f"/api/summary/{stored_flow}")

    assert resp.status_code == 202
    assert await summary_db.count(RequestSummaryORM) == 0
    assert await summary_db.count(ResponseSummaryORM) == 0
    assert await raw_db.count(RawRequestORM) == 0
    assert await raw_db.count(RawResponseORM) == 0


async def test_delete_flow_with_only_request(client, summary_db, request_summary_orm):
    saved = await summary_db.create(request_summary_orm())

    resp = await client.delete(f"/api/summary/{saved.flow_id}")

    assert resp.status_code == 202
    assert await summary_db.count(RequestSummaryORM) == 0


async def test_delete_unknown_flow_returns_404(client):
    resp = await client.delete(f"/api/summary/{uuid4()}")

    assert resp.status_code == 404


async def test_delete_all_flows(client, summary_db, raw_db, stored_flow):
    resp = await client.delete("/api/summary/")

    assert resp.status_code == 202
    assert await summary_db.count(RequestSummaryORM) == 0
    assert await summary_db.count(ResponseSummaryORM) == 0
    assert await raw_db.count(RawRequestORM) == 0
    assert await raw_db.count(RawResponseORM) == 0
