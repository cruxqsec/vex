async def test_health(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert isinstance(body["pid"], int)


async def test_root_redirects_to_docs(client):
    resp = await client.get("/")

    assert resp.status_code == 307
    assert resp.headers["location"] == "/docs"
