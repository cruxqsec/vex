from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import RequestSummaryORM, ResponseSummaryORM, ScopeORM
from vex_cli.models.pydantic import FlowSummary, Scope


@pytest_asyncio.fixture
async def db(tmp_path: Path):
    database = SummariesDatabase(db_path=tmp_path / "summaries.db")
    await database.initialize()
    yield database
    await database.close()


def make_request_summary(**kwargs):
    defaults = {
        "flow_id": uuid4(),
        "host": "example.com",
        "method": "GET",
        "path": "/test/path",
        "request_size": 123,
        "is_tls": True,
        "query": "?test=queryparam",
        "file_extension": ".php",
        "timestamp": 5034566.34,
    }
    return RequestSummaryORM(**{**defaults, **kwargs})


def make_response_summary(**kwargs):
    defaults = {
        "flow_id": uuid4(),
        "status_code": 200,
        "response_size": 2134,
        "mime": "html/text",
        "http_title": "Example title",
        "cookie": "test_cookie=value",
        "duration_ms": 345,
        "timestamp": 324569.43,
    }
    return ResponseSummaryORM(**{**defaults, **kwargs})


def test_res_cols_excludes_correct_columns(db):
    """id, flow_id, timestamp should be excluded from response cols."""
    res_col_names = {col.key for col in db._res_cols}

    assert "flow_id" not in res_col_names
    assert "timestamp" not in res_col_names


def test_res_cols_contains_remaining_columns(db):
    """All other ResponseSummaryORM columns should still be present."""
    res_col_names = {col.key for col in db._res_cols}
    expected = {
        c.name
        for c in ResponseSummaryORM.__table__.columns
        if c.name not in {"flow_id", "timestamp"}
    }

    assert res_col_names == expected


@pytest.mark.asyncio
async def test_get_full_summary(db):
    flow_id1, flow_id2 = uuid4(), uuid4()
    await db.create(make_request_summary(flow_id=flow_id1))
    await db.create(make_response_summary(flow_id=flow_id1))

    await db.create(make_request_summary(flow_id=flow_id2))
    await db.create(make_response_summary(flow_id=flow_id2))

    result = await db.get_full_summaries(skip=0, size=10)
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
async def test_get_full_summaries_if_just_requests(db):
    await db.create(make_request_summary())
    await db.create(make_request_summary())

    result = await db.get_full_summaries(skip=0, size=10)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_full_summaries_empty(db):
    result = await db.get_full_summaries(skip=0, size=10)

    assert result == []


@pytest.mark.asyncio
async def test_get_full_summary_by_id_returns_correct(db):
    flow_id = uuid4()
    await db.create(make_request_summary(flow_id=flow_id))

    result = await db.get_full_summary_by_id(flow_id)

    assert type(result) is FlowSummary
    assert result.flow_id == flow_id


@pytest.mark.asyncio
async def test_get_full_summary_by_id_with_response(db):
    flow_id = uuid4()
    await db.create(make_request_summary(flow_id=flow_id))
    await db.create(make_response_summary(flow_id=flow_id))

    result = await db.get_full_summary_by_id(flow_id)

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
async def test_get_full_summary_by_id_not_found(db):
    with pytest.raises(NotFoundError):
        await db.get_full_summary_by_id(uuid4())


# --- ScopeORM tests ---


@pytest.mark.asyncio
async def test_scope_orm_default_definitions(db):
    scope = await db.create(ScopeORM(name="Default Scope"))
    assert scope.id is not None
    assert scope.name == "Default Scope"
    assert scope.definitions == '{"allow":[],"deny":[]}'

    result = await db.get(ScopeORM, scope.id)
    assert result.name == "Default Scope"
    assert result.definitions == '{"allow":[],"deny":[]}'


@pytest.mark.asyncio
async def test_scope_orm_custom_definitions(db):
    scope = await db.create(
        ScopeORM(name="My Scope", definitions='{"allow": ["example.com"], "deny": []}')
    )
    assert scope.name == "My Scope"
    assert scope.definitions == '{"allow": ["example.com"], "deny": []}'

    result = await db.get(ScopeORM, scope.id)
    assert result.name == "My Scope"
    assert result.definitions == '{"allow": ["example.com"], "deny": []}'


@pytest.mark.asyncio
async def test_scope_orm_roundtrip_via_from_orm(db):
    scope_orm = await db.create(
        ScopeORM(
            name="Prod Scope",
            definitions='{"allow": ["10.0.0.1"], "deny": ["evil.com"]}',
        )
    )
    scope = Scope.from_orm(scope_orm)

    assert scope.id == scope_orm.id
    assert scope.name == "Prod Scope"
    assert scope.allow_endpoints == ["10.0.0.1"]
    assert scope.deny_endpoints == ["evil.com"]


@pytest.mark.asyncio
async def test_scope_orm_default_roundtrip_via_from_orm(db):
    scope_orm = await db.create(ScopeORM(name="Empty Scope"))
    scope = Scope.from_orm(scope_orm)

    assert scope.id == scope_orm.id
    assert scope.name == "Empty Scope"
    assert scope.allow_endpoints == []
    assert scope.deny_endpoints == []


# --- delete_by_flow_id tests ---


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_request_summary(db):
    flow_id = uuid4()
    req = make_request_summary(flow_id=flow_id)
    await db.create(req)

    await db.delete_by_flow_id(RequestSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await db.get_by_flow_id(RequestSummaryORM, flow_id)


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_response_summary(db):
    flow_id = uuid4()
    res = make_response_summary(flow_id=flow_id)
    await db.create(res)

    await db.delete_by_flow_id(ResponseSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await db.get_by_flow_id(ResponseSummaryORM, flow_id)


@pytest.mark.asyncio
async def test_delete_by_flow_id_does_not_affect_other_flows(db):
    flow_id1, flow_id2 = uuid4(), uuid4()
    await db.create(make_request_summary(flow_id=flow_id1))
    await db.create(make_request_summary(flow_id=flow_id2))

    await db.delete_by_flow_id(RequestSummaryORM, flow_id1)

    result = await db.get_by_flow_id(RequestSummaryORM, flow_id2)
    assert result.flow_id == flow_id2


@pytest.mark.asyncio
async def test_delete_by_flow_id_not_found_raises(db):
    flow_id = uuid4()
    await db.create(make_request_summary(flow_id=flow_id))

    with pytest.raises(NotFoundError):
        await db.delete_by_flow_id(RequestSummaryORM, uuid4())


@pytest.mark.asyncio
async def test_delete_by_flow_id_removes_only_target_model(db):
    flow_id = uuid4()
    req = make_request_summary(flow_id=flow_id)
    res = make_response_summary(flow_id=flow_id)
    await db.create(req)
    await db.create(res)

    await db.delete_by_flow_id(RequestSummaryORM, flow_id)

    with pytest.raises(NotFoundError):
        await db.get_by_flow_id(RequestSummaryORM, flow_id)

    result = await db.get_by_flow_id(ResponseSummaryORM, flow_id)
    assert result.flow_id == flow_id


@pytest.mark.asyncio
async def test_get_full_summaries_paginates_in_timestamp_order(db):
    """Pages must come back in deterministic (timestamp, id) order with no
    skipped or repeated flows, even with ties on timestamp."""
    stamps_and_flow_ids = [
        (50.0, uuid4()),
        (10.0, uuid4()),
        (40.0, uuid4()),
        (20.0, uuid4()),
        (30.0, uuid4()),
        (40.0, uuid4()),  # tie on timestamp; lower id (inserted first) wins
    ]
    for ts, fid in stamps_and_flow_ids:
        await db.create(make_request_summary(flow_id=fid, timestamp=ts))

    pages = [
        await db.get_full_summaries(skip=skip, size=2) for skip in (0, 2, 4)
    ]
    rows = [row for page in pages for row in page]

    assert len(rows) == 6
    assert len({row.flow_id for row in rows}) == 6

    expected = [
        fid for _, fid in sorted(stamps_and_flow_ids, key=lambda t: t[0])
    ]
    assert [row.flow_id for row in rows] == expected
