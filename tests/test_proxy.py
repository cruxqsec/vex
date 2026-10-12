from uuid import UUID

import pytest_asyncio
import pytest

from vex_cli.models.orm import (
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
)
from vex_cli.models.pydantic import (
    CaptureErrorEvent,
    RequestSummary,
    ResponseSummary,
    Scope,
)
from vex_cli.proxy import VexCapture


@pytest_asyncio.fixture
async def capture(state, flow_scope, allow_only_scope, project):
    flow_scope.set_active_scope(allow_only_scope)
    await state.set_active_project(project())
    return VexCapture(state)


@pytest.fixture
def events(flow_history):
    return flow_history.subscribe()


def drain(queue):
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


async def test_request_is_saved_and_broadcast(
    capture, req_res_flow, summary_db, raw_db, events
):
    await capture.request(req_res_flow)

    assert await summary_db.count(RequestSummaryORM) == 1
    assert await raw_db.count(RawRequestORM) == 1
    (event,) = drain(events)
    assert isinstance(event, RequestSummary)
    assert event.id is not None
    assert event.host == "example.com"


async def test_request_strips_cache_validators(capture, req_res_flow):
    req_res_flow.request.headers["If-None-Match"] = '"abc"'
    req_res_flow.request.headers["If-Modified-Since"] = "Wed, 21 Oct 2015 07:28:00 GMT"

    await capture.request(req_res_flow)

    assert "If-None-Match" not in req_res_flow.request.headers
    assert "If-Modified-Since" not in req_res_flow.request.headers


async def test_response_is_saved_and_broadcast(
    capture, req_res_flow, summary_db, raw_db, events
):
    await capture.request(req_res_flow)
    await capture.response(req_res_flow)

    assert await summary_db.count(ResponseSummaryORM) == 1
    assert await raw_db.count(RawResponseORM) == 1
    request_event, response_event = drain(events)
    assert isinstance(response_event, ResponseSummary)
    assert response_event.flow_id == request_event.flow_id
    assert response_event.status_code == 200


async def test_out_of_scope_flow_is_ignored(
    capture, flow_scope, req_res_flow, summary_db, raw_db, events
):
    flow_scope.set_active_scope(
        Scope(id=7, name="other", allow_endpoints=["other.com"], deny_endpoints=[])
    )

    await capture.request(req_res_flow)
    await capture.response(req_res_flow)

    assert await summary_db.count(RequestSummaryORM) == 0
    assert await summary_db.count(ResponseSummaryORM) == 0
    assert await raw_db.count(RawRequestORM) == 0
    assert drain(events) == []


async def test_nothing_is_captured_without_active_project(
    capture, state, req_res_flow, summary_db, events
):
    await state.set_active_project(None)

    await capture.request(req_res_flow)

    assert await summary_db.count(RequestSummaryORM) == 0
    assert drain(events) == []


async def test_summary_is_rolled_back_when_raw_save_fails(
    capture, req_res_flow, summary_db, raw_db, raw_request_orm, events
):
    await raw_db.create(raw_request_orm(id=UUID(req_res_flow.id)))

    await capture.request(req_res_flow)

    assert await summary_db.count(RequestSummaryORM) == 0
    (event,) = drain(events)
    assert isinstance(event, CaptureErrorEvent)
    assert event.kind == "database"


async def test_unexpected_error_is_broadcast_and_does_not_escape(
    capture, req_res_flow, events, monkeypatch
):
    def boom(flow):
        raise ValueError("boom")

    monkeypatch.setattr("vex_cli.proxy.flow_to_raw_request", boom)

    await capture.request(req_res_flow)

    (event,) = drain(events)
    assert event.kind == "unknown"
    assert event.host == "example.com"


async def test_captured_flow_is_visible_through_the_api(capture, client, req_res_flow):
    await capture.request(req_res_flow)
    await capture.response(req_res_flow)

    resp = await client.get("/api/summary/")

    (flow,) = resp.json()
    assert flow["host"] == "example.com"
    assert flow["status_code"] == 200
