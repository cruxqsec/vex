from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio

from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import RequestSummaryORM, ResponseSummaryORM


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
        "has_cookie_set": False,
        "duration_ms": 345,
        "timestamp": 324569.43,
    }
    return ResponseSummaryORM(**{**defaults, **kwargs})


def test_res_cols_excludes_correct_columns(db):
    """id, flow_id, timestamp should be excluded from response cols."""
    res_col_names = {col.key for col in db._res_cols}

    assert "id" not in res_col_names
    assert "flow_id" not in res_col_names
    assert "timestamp" not in res_col_names


def test_res_cols_contains_remaining_columns(db):
    """All other ResponseSummaryORM columns should still be present."""
    res_col_names = {col.key for col in db._res_cols}
    expected = {
        c.name
        for c in ResponseSummaryORM.__table__.columns
        if c.name not in {"id", "flow_id", "timestamp"}
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
        "has_cookie_set",
        "duration_ms",
    ]

    assert len(result) == 2
    assert "id" in result[0]
    assert "id" in result[1]

    # check the presence of all the req and res summary keys
    for k in req_summary_keys:
        assert k in result[0]
        assert k in result[1]

    for k in res_summary_keys:
        assert k in result[0]
        assert k in result[1]


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

    assert result is not None
    assert result["flow_id"] == flow_id


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
        "has_cookie_set",
        "duration_ms",
    ]

    assert type(result) is dict
    assert "id" in result

    # check the presence of all the req and res summary keys
    for k in req_summary_keys:
        assert k in result

    for k in res_summary_keys:
        assert k in result


@pytest.mark.asyncio
async def test_get_full_summary_by_id_not_found(db):
    with pytest.raises(NotFoundError):
        await db.get_full_summary_by_id(uuid4())
