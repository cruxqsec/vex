from uuid import uuid4

import pytest

from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import RequestSummaryORM, ResponseSummaryORM, ScopeORM
from vex_cli.models.pydantic import FlowSummary, Scope


def test_res_cols_excludes_correct_columns(summary_db: SummariesDatabase):
    res_col_names = {col.key for col in summary_db._res_cols}

    assert "id" not in res_col_names
    assert "flow_id" not in res_col_names
    assert "timestamp" not in res_col_names


def test_res_cols_contains_remaining_columns(summary_db):
    res_col_names = {col.key for col in summary_db._res_cols}
    expected = {
        c.name
        for c in ResponseSummaryORM.__table__.columns
        if c.name not in {"id", "flow_id", "timestamp"}
    }

    assert res_col_names == expected


@pytest.mark.asyncio
async def test_get_full_summary(summary_db, request_summary_orm, response_summary_orm):
    flow_id1, flow_id2 = uuid4(), uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id1))
    await summary_db.create(response_summary_orm(flow_id=flow_id1))

    await summary_db.create(request_summary_orm(flow_id=flow_id2))
    await summary_db.create(response_summary_orm(flow_id=flow_id2))

    result = await summary_db.get_full_summaries(skip=0, size=10)
    req_summary_keys = [
        "flow_id",
        "host",
        "method",
        "path",
        "request_size",
        "is_tls",
        "query",
        "file_extension",
        "timestamp",
    ]
    res_summary_keys = [
        "status_code",
        "response_size",
        "mime",
        "http_title",
        "cookie",
        "duration_ms",
    ]

    assert hasattr(result[0], "id")
    assert hasattr(result[1], "id")

    # check the presence of all the req and res summary keys
    for k in req_summary_keys:
        assert hasattr(result[0], k)
        assert hasattr(result[1], k)

    for k in res_summary_keys:
        assert hasattr(result[0], k)
        assert hasattr(result[1], k)


@pytest.mark.asyncio
async def test_get_full_summaries_id_is_request_id(summary_db, request_summary_orm, response_summary_orm):
    request = await summary_db.create(request_summary_orm())

    flow_id = uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id))
    await summary_db.create(response_summary_orm(flow_id=flow_id))

    result = await summary_db.get_full_summaries(skip=0, size=10)

    assert len(result) == 2
    assert result[-1].id == 2
    assert result[-1].id != request.id


@pytest.mark.asyncio
async def test_get_full_summaries_if_just_requests(summary_db, request_summary_orm):
    await summary_db.create(request_summary_orm())
    await summary_db.create(request_summary_orm())

    result = await summary_db.get_full_summaries(skip=0, size=10)

    assert len(result) == 2
    assert result[0].status_code is None
    assert result[1].status_code is None

    assert result[0].response_size is None
    assert result[1].response_size is None

    assert result[0].mime is None
    assert result[1].mime is None

@pytest.mark.asyncio
async def test_get_full_summaries_empty(summary_db):
    result = await summary_db.get_full_summaries(skip=0, size=10)

    assert result == []


@pytest.mark.asyncio
async def test_get_full_summary_by_id_returns_correct(summary_db, request_summary_orm):
    flow_id = uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id))

    result = await summary_db.get_full_summary_by_id(flow_id)

    assert type(result) is FlowSummary
    assert result.flow_id == flow_id


@pytest.mark.asyncio
async def test_get_full_summary_by_id_with_response(
    summary_db,
    request_summary_orm,
    response_summary_orm
):
    flow_id = uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id))
    await summary_db.create(response_summary_orm(flow_id=flow_id))

    result = await summary_db.get_full_summary_by_id(flow_id)

    req_summary_keys = [
        "flow_id",
        "host",
        "method",
        "path",
        "request_size",
        "is_tls",
        "query",
        "file_extension",
        "timestamp",
    ]
    res_summary_keys = [
        "status_code",
        "response_size",
        "mime",
        "http_title",
        "cookie",
        "duration_ms",
    ]

    assert type(result) is FlowSummary
    assert hasattr(result, "id")

    # check the presence of all the req and res summary keys
    for k in req_summary_keys:
        assert hasattr(result, k)

    for k in res_summary_keys:
        assert hasattr(result, k)


@pytest.mark.asyncio
async def test_get_full_summary_by_id_not_found(summary_db):
    with pytest.raises(NotFoundError):
        await summary_db.get_full_summary_by_id(uuid4())


@pytest.mark.asyncio
async def test_scope_orm_default_definitions(summary_db, empty_scope: Scope):
    scope = await summary_db.create(empty_scope.to_orm())
    assert scope.id is not None
    assert scope.name == "Empty Scope"
    assert scope.definitions == '{"allow": [], "deny": []}'

    result = await summary_db.get(ScopeORM, scope.id)
    assert result.name == "Empty Scope"
    assert result.definitions == '{"allow": [], "deny": []}'


@pytest.mark.asyncio
async def test_scope_orm_custom_definitions(summary_db, allow_only_scope: Scope):
    scope = await summary_db.create(allow_only_scope.to_orm())
    assert scope.name == "Allow Only"
    assert scope.definitions == '{"allow": ["example.com", "127.0.0.1"], "deny": []}'

    result = await summary_db.get(ScopeORM, scope.id)
    assert result.name == "Allow Only"
    assert result.definitions == '{"allow": ["example.com", "127.0.0.1"], "deny": []}'


@pytest.mark.asyncio
async def test_scope_orm_roundtrip_via_from_orm(summary_db, scope: Scope):
    scope_orm = await summary_db.create(scope.to_orm())
    from_orm = Scope.from_orm(scope_orm)

    assert from_orm.id == scope_orm.id
    assert from_orm.name == "Production Scope"
    assert from_orm.allow_endpoints == ["192.168.1.1"]
    assert from_orm.deny_endpoints == ["10.0.0.1", "evil.com"]


@pytest.mark.asyncio
async def test_scope_orm_default_roundtrip_via_from_orm(summary_db, empty_scope: Scope):
    scope_orm = await summary_db.create(empty_scope.to_orm())
    from_orm = Scope.from_orm(scope_orm)

    assert from_orm.id == scope_orm.id
    assert from_orm.name == "Empty Scope"
    assert from_orm.allow_endpoints == []
    assert from_orm.deny_endpoints == []


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_request_summary(summary_db, request_summary_orm):
    flow_id = uuid4()
    req = request_summary_orm(flow_id=flow_id)
    await summary_db.create(req)

    await summary_db.delete_by_flow_id(RequestSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await summary_db.get_by_flow_id(RequestSummaryORM, flow_id)


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_response_summary(summary_db, response_summary_orm):
    flow_id = uuid4()
    res = response_summary_orm(flow_id=flow_id)
    await summary_db.create(res)

    await summary_db.delete_by_flow_id(ResponseSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await summary_db.get_by_flow_id(ResponseSummaryORM, flow_id)


@pytest.mark.asyncio
async def test_delete_by_flow_id_does_not_affect_other_flows(summary_db, request_summary_orm):
    flow_id1, flow_id2 = uuid4(), uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id1))
    await summary_db.create(request_summary_orm(flow_id=flow_id2))

    await summary_db.delete_by_flow_id(RequestSummaryORM, flow_id1)

    result = await summary_db.get_by_flow_id(RequestSummaryORM, flow_id2)
    assert result.flow_id == flow_id2


@pytest.mark.asyncio
async def test_delete_by_flow_id_not_found_raises(summary_db, request_summary_orm):
    flow_id = uuid4()
    await summary_db.create(request_summary_orm(flow_id=flow_id))

    with pytest.raises(NotFoundError):
        await summary_db.delete_by_flow_id(RequestSummaryORM, uuid4())


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_only_target_model(
    summary_db, request_summary_orm, response_summary_orm
):
    flow_id = uuid4()
    req = request_summary_orm(flow_id=flow_id)
    res = response_summary_orm(flow_id=flow_id)
    await summary_db.create(req)
    await summary_db.create(res)

    await summary_db.delete_by_flow_id(RequestSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await summary_db.get_by_flow_id(RequestSummaryORM, flow_id)

    result = await summary_db.get_by_flow_id(ResponseSummaryORM, flow_id)
    assert result.flow_id == flow_id
