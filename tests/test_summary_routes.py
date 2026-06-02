import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from vex_cli.app import create_app
from vex_cli.dependencies import get_raw_db, get_summaries_db
from vex_cli.errors import DatabaseError, NotFoundError
from vex_cli.models.orm import (
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
)
from vex_cli.models.pydantic import RequestSummary, ResponseSummary


def make_request_summary(
    flow_id: str | None = None,
    host: str = "example.com",
    method: str = "GET",
    path: str = "/test",
):
    return RequestSummary(
        flow_id=uuid4() if flow_id is None else flow_id,
        host=host,
        method=method,
        path=path,
        request_size=100,
        is_tls=False,
        query=None,
        file_extension=None,
        timestamp=datetime.timestamp(datetime.now()),
    )


def make_response_summary(
    flow_id: str | None = None,
    status_code: int = 200,
    mime: str = "text/html",
    http_title: str = "Example",
    cookie: str = "",
):
    return ResponseSummary(
        flow_id=uuid4() if flow_id is None else flow_id,
        status_code=status_code,
        response_size=500,
        mime=mime,
        http_title=http_title,
        cookie=cookie,
        duration_ms=100,
        timestamp=datetime.timestamp(datetime.now()),
    )


@pytest_asyncio.fixture
async def mock_summaries_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(mock_summaries_db):
    app = create_app()
    app.dependency_overrides[get_summaries_db] = lambda: mock_summaries_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c
    app.dependency_overrides.clear()


# --- REQUEST SUMMARY ENDPOINTS ---


@pytest.mark.asyncio
async def test_get_all_request_summaries_returns_200(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = [make_request_summary()]

    response = await client.get("/api/summary/request/")

    assert response.status_code == 200
    mock_summaries_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_request_summaries_returns_empty_list(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = []

    response = await client.get("/api/summary/request/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_request_summaries_with_pagination(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = [make_request_summary()]

    response = await client.get("/api/summary/request/?skip=10&size=20")

    assert response.status_code == 200
    mock_summaries_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_request_summaries_rejects_invalid_size(
    client, mock_summaries_db
):
    response = await client.get("/api/summary/request/?size=999")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_request_summary_by_flow_id_returns_200(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_by_flow_id.return_value = make_request_summary(
        flow_id=flow_id
    )

    response = await client.get(f"/api/summary/request/{flow_id}")

    assert response.status_code == 200
    mock_summaries_db.get_by_flow_id.assert_called_once()


@pytest.mark.asyncio
async def test_get_request_summary_by_flow_id_not_found(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_by_flow_id.side_effect = NotFoundError("Not found")

    response = await client.get(f"/api/summary/request/{flow_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_request_summary_returns_201(client, mock_summaries_db):
    flow_id = uuid4()
    req_summary = make_request_summary(flow_id=flow_id)
    mock_summaries_db.create.return_value = req_summary

    payload = {
        "flow_id": str(flow_id),
        "host": "example.com",
        "method": "GET",
        "path": "/test",
        "request_size": 100,
        "is_tls": False,
        "query": None,
        "file_extension": None,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.post("/api/summary/request/", json=payload)

    assert response.status_code == 201
    mock_summaries_db.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_request_summary_invalid_payload(client, mock_summaries_db):
    response = await client.post("/api/summary/request/", json={"bad": "data"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_request_summary_returns_202(client, mock_summaries_db):
    flow_id = uuid4()
    req_summary = make_request_summary(flow_id=flow_id)
    mock_summaries_db.update.return_value = None

    payload = {
        "flow_id": str(flow_id),
        "host": "example.com",
        "method": "GET",
        "path": "/test",
        "request_size": 100,
        "is_tls": False,
        "query": None,
        "file_extension": None,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.put("/api/summary/request/", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_update_request_summary_not_found(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.update.side_effect = NotFoundError("Not found")

    payload = {
        "flow_id": str(flow_id),
        "host": "example.com",
        "method": "GET",
        "path": "/test",
        "request_size": 100,
        "is_tls": False,
        "query": None,
        "file_extension": None,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.put("/api/summary/request/", json=payload)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_request_summary_returns_202(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.delete.return_value = None

    response = await client.delete(f"/api/summary/request/{flow_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_request_summary_not_found(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.delete.side_effect = NotFoundError("Not found")

    response = await client.delete(f"/api/summary/request/{flow_id}")

    assert response.status_code == 404


# --- RESPONSE SUMMARY ENDPOINTS ---


@pytest.mark.asyncio
async def test_get_all_response_summaries_returns_200(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = [make_response_summary()]

    response = await client.get("/api/summary/response/")

    assert response.status_code == 200
    mock_summaries_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_response_summaries_returns_empty_list(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = []

    response = await client.get("/api/summary/response/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_all_response_summaries_with_pagination(client, mock_summaries_db):
    mock_summaries_db.get_all.return_value = [make_response_summary()]

    response = await client.get("/api/summary/response/?skip=10&size=20")

    assert response.status_code == 200
    mock_summaries_db.get_all.assert_called_once()


@pytest.mark.asyncio
async def test_get_response_summary_by_flow_id_returns_200(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_by_flow_id.return_value = make_response_summary(
        flow_id=flow_id
    )

    response = await client.get(f"/api/summary/response/{flow_id}")

    assert response.status_code == 200
    mock_summaries_db.get_by_flow_id.assert_called_once()


@pytest.mark.asyncio
async def test_get_response_summary_by_flow_id_not_found(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_by_flow_id.side_effect = NotFoundError("Not found")

    response = await client.get(f"/api/summary/response/{flow_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_response_summary_returns_201(client, mock_summaries_db):
    flow_id = uuid4()
    res_summary = make_response_summary(flow_id=flow_id)
    mock_summaries_db.create.return_value = res_summary

    payload = {
        "flow_id": str(flow_id),
        "status_code": 200,
        "response_size": 500,
        "mime": "text/html",
        "http_title": "Example",
        "cookie": "",
        "duration_ms": 100,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.post("/api/summary/response/", json=payload)

    assert response.status_code == 201
    mock_summaries_db.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_response_summary_invalid_payload(client, mock_summaries_db):
    response = await client.post("/api/summary/response/", json={"bad": "data"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_response_summary_returns_202(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.update.return_value = None

    payload = {
        "flow_id": str(flow_id),
        "status_code": 200,
        "response_size": 500,
        "mime": "text/html",
        "http_title": "Example",
        "cookie": "",
        "duration_ms": 100,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.put("/api/summary/response/", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_response_summary_returns_202(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.delete.return_value = None

    response = await client.delete(f"/api/summary/response/{flow_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


# --- FULL SUMMARY ENDPOINTS ---


@pytest.mark.asyncio
async def test_get_all_full_summaries_returns_200(client, mock_summaries_db):
    mock_summaries_db.get_full_summaries.return_value = [
        {
            "id": 1,
            "flow_id": str(uuid4()),
            "host": "example.com",
            "method": "GET",
            "path": "/test",
            "request_size": 100,
            "is_tls": False,
            "query": None,
            "file_extension": None,
            "status_code": 200,
            "response_size": 500,
            "mime": "text/html",
            "http_title": "Example",
            "cookie": "",
            "duration_ms": 100,
            "timestamp": datetime.timestamp(datetime.now()),
        }
    ]

    response = await client.get("/api/summary/")

    assert response.status_code == 200
    mock_summaries_db.get_full_summaries.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_full_summaries_returns_empty_list(client, mock_summaries_db):
    mock_summaries_db.get_full_summaries.return_value = []

    response = await client.get("/api/summary/")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_full_summary_by_id_returns_200(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_full_summary_by_id.return_value = {
        "id": 1,
        "flow_id": str(flow_id),
        "host": "example.com",
        "method": "GET",
        "path": "/test",
        "request_size": 100,
        "is_tls": False,
        "query": None,
        "file_extension": None,
        "status_code": 200,
        "response_size": 500,
        "mime": "text/html",
        "http_title": "Example",
        "cookie": "",
        "duration_ms": 100,
        "timestamp": datetime.timestamp(datetime.now()),
    }

    response = await client.get(f"/api/summary/{flow_id}")

    assert response.status_code == 200
    mock_summaries_db.get_full_summary_by_id.assert_called_once()


@pytest.mark.asyncio
async def test_get_full_summary_by_id_not_found(client, mock_summaries_db):
    flow_id = uuid4()
    mock_summaries_db.get_full_summary_by_id.side_effect = NotFoundError("Not found")

    response = await client.get(f"/api/summary/{flow_id}")

    assert response.status_code == 404


# --- DELETE /api/summary/{flow_id} ---


@pytest_asyncio.fixture
async def mock_raw_db():
    return AsyncMock()


@pytest_asyncio.fixture
async def delete_client(mock_summaries_db, mock_raw_db):
    app = create_app()
    app.dependency_overrides[get_summaries_db] = lambda: mock_summaries_db
    app.dependency_overrides[get_raw_db] = lambda: mock_raw_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_flow_deletes_all_records(
    delete_client, mock_summaries_db, mock_raw_db
):
    flow_id = uuid4()

    response = await delete_client.delete(f"/api/summary/{flow_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"
    mock_summaries_db.delete_by_flow_id.assert_any_call(RequestSummaryORM, flow_id)
    mock_summaries_db.delete_by_flow_id.assert_any_call(ResponseSummaryORM, flow_id)
    mock_raw_db.delete.assert_any_call(RawRequestORM, flow_id)
    mock_raw_db.delete.assert_any_call(RawResponseORM, flow_id)


@pytest.mark.asyncio
async def test_delete_flow_request_summary_not_found(
    delete_client, mock_summaries_db, mock_raw_db
):
    flow_id = uuid4()
    mock_summaries_db.delete_by_flow_id.side_effect = NotFoundError("Not found")

    response = await delete_client.delete(f"/api/summary/{flow_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_flow_raw_request_not_found(
    delete_client, mock_summaries_db, mock_raw_db
):
    flow_id = uuid4()
    mock_summaries_db.delete_by_flow_id.return_value = None
    mock_raw_db.delete.side_effect = NotFoundError("Not found")

    response = await delete_client.delete(f"/api/summary/{flow_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_flow_skips_missing_response_summary(
    delete_client, mock_summaries_db, mock_raw_db
):
    flow_id = uuid4()

    def delete_by_flow_id_side_effect(model, fid):
        if model is ResponseSummaryORM:
            raise NotFoundError("Not found")
        return None

    mock_summaries_db.delete_by_flow_id.side_effect = delete_by_flow_id_side_effect

    response = await delete_client.delete(f"/api/summary/{flow_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_flow_skips_missing_raw_response(
    delete_client, mock_summaries_db, mock_raw_db
):
    flow_id = uuid4()

    def raw_delete_side_effect(model, fid):
        if model is RawResponseORM:
            raise NotFoundError("Not found")
        return None

    mock_raw_db.delete.side_effect = raw_delete_side_effect

    response = await delete_client.delete(f"/api/summary/{flow_id}")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


# --- DELETE /api/summary/ (delete all flows) ---


@pytest.mark.asyncio
async def test_delete_all_flows_deletes_all_tables(
    delete_client, mock_summaries_db, mock_raw_db
):
    response = await delete_client.delete("/api/summary/")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"
    mock_summaries_db.delete_all.assert_any_call(RequestSummaryORM)
    mock_summaries_db.delete_all.assert_any_call(ResponseSummaryORM)
    mock_raw_db.delete_all.assert_any_call(RawRequestORM)
    mock_raw_db.delete_all.assert_any_call(RawResponseORM)


@pytest.mark.asyncio
async def test_delete_all_flows_empty_is_ok(
    delete_client, mock_summaries_db, mock_raw_db
):
    response = await delete_client.delete("/api/summary/")

    assert response.status_code == 202
    assert response.json()["status"] == "Success"


@pytest.mark.asyncio
async def test_delete_all_flows_partial_error_returns_500(
    delete_client, mock_summaries_db, mock_raw_db
):
    mock_summaries_db.delete_all.side_effect = DatabaseError("boom")

    response = await delete_client.delete("/api/summary/")

    assert response.status_code == 500


# --- GET /api/summary/count ---


@pytest.mark.asyncio
async def test_count_flows_returns_count(client, mock_summaries_db):
    mock_summaries_db.count.return_value = 5

    response = await client.get("/api/summary/count")

    assert response.status_code == 200
    assert response.json() == {"count": 5}
    mock_summaries_db.count.assert_called_once()


@pytest.mark.asyncio
async def test_count_flows_empty_returns_zero(client, mock_summaries_db):
    mock_summaries_db.count.return_value = 0

    response = await client.get("/api/summary/count")

    assert response.status_code == 200
    assert response.json() == {"count": 0}
