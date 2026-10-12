from uuid import uuid4


async def test_get_all_raw_requests(client, raw_db, raw_request_orm):
    for _ in range(3):
        await raw_db.create(raw_request_orm())

    resp = await client.get("/api/raw/request/")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_get_raw_request(client, raw_db, raw_request_orm):
    saved = await raw_db.create(raw_request_orm())

    resp = await client.get(f"/api/raw/request/{saved.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(saved.id)
    assert body["data"] == saved.data.decode("latin-1")


async def test_get_unknown_raw_request_returns_404(client):
    resp = await client.get(f"/api/raw/request/{uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFoundError"


async def test_get_all_raw_responses(client, raw_db, raw_response_orm):
    for _ in range(3):
        await raw_db.create(raw_response_orm())

    resp = await client.get("/api/raw/response/")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_get_raw_response(client, raw_db, raw_response_orm):
    saved = await raw_db.create(raw_response_orm())

    resp = await client.get(f"/api/raw/response/{saved.id}")

    assert resp.status_code == 200
    assert resp.json()["data"] == saved.data.decode("latin-1")


async def test_get_raw_response_without_data(client, raw_db, raw_response_orm):
    saved = await raw_db.create(raw_response_orm(data=None))

    resp = await client.get(f"/api/raw/response/{saved.id}")

    assert resp.status_code == 200
    assert resp.json()["data"] is None


async def test_get_unknown_raw_response_returns_404(client):
    resp = await client.get(f"/api/raw/response/{uuid4()}")

    assert resp.status_code == 404
