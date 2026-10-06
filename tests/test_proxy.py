import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from vex_cli.errors import DatabaseError
from vex_cli.errors import ValidationError as VexValidationError
from vex_cli.flow_scope import FlowScope
from vex_cli.models.pydantic import (
    CaptureErrorEvent,
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
    VexServerInfo,
)
from vex_cli.proxy import VexCapture, start_proxy


@pytest.fixture
def mock_app_state():
    server_info = VexServerInfo(
        server_address="127.0.0.1", proxy_port=8080, api_port=8081
    )
    state = MagicMock()
    state.is_project_active = True
    state.get_server_info.return_value = server_info
    state.get_flow_history.return_value = AsyncMock()
    state.get_flow_scope.return_value = MagicMock(spec=FlowScope)
    db_manager = MagicMock()
    db_manager.active_databases.return_value = (
        db_manager.summaries_db,
        db_manager.raw_db,
    )
    db_manager.summaries_db.create = AsyncMock()
    db_manager.summaries_db.delete_by_flow_id = AsyncMock()
    db_manager.raw_db.create = AsyncMock()
    state.get_db_manager.return_value = db_manager
    return state


@pytest.fixture
def capture(mock_app_state):
    return VexCapture(mock_app_state)


@pytest.fixture
def mock_flow():
    flow = MagicMock()
    flow.request.headers = {
        "If-Modified-Since": "some-date",
        "If-None-Match": "some-etag",
    }
    flow.request.pretty_host = "example.com"
    return flow


def error_events(capture) -> list[CaptureErrorEvent]:
    return [
        c.args[0]
        for c in capture.flow_history.broadcast.call_args_list
        if isinstance(c.args[0], CaptureErrorEvent)
    ]


def test_init_sets_app_state(mock_app_state):
    capture = VexCapture(mock_app_state)

    assert capture.app_state is mock_app_state


def test_init_gets_flow_history(mock_app_state):
    capture = VexCapture(mock_app_state)

    assert capture.flow_history is mock_app_state.get_flow_history()


def test_init_gets_db_manager(mock_app_state):
    capture = VexCapture(mock_app_state)

    assert capture.db_manager is mock_app_state.get_db_manager()


def test_init_gets_flow_scope(mock_app_state):
    capture = VexCapture(mock_app_state)

    assert capture.flow_scope is mock_app_state.get_flow_scope()


@pytest.mark.asyncio
async def test_request_does_nothing_if_no_active_project(capture, mock_flow):
    capture.app_state.is_project_active = False

    await capture.request(mock_flow)

    capture.flow_history.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_request_calls_save_and_broadcast(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)
    mocker.patch("vex_cli.proxy.flow_to_raw_request", return_value=b"raw request bytes")
    mocker.patch("vex_cli.proxy.RequestSummary.from_flow", return_value=mock_summary)
    mocker.patch("vex_cli.proxy.RawRequest.from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_flow, mock_summary, mock_raw)


@pytest.mark.asyncio
async def test_request_does_not_raise_on_exception(capture, mock_flow, mocker):
    mocker.patch(
        "vex_cli.proxy.flow_to_raw_request", side_effect=Exception("unexpected")
    )

    await capture.request(mock_flow)

    errors = error_events(capture)
    assert len(errors) == 1
    assert errors[0].kind == "unknown"
    assert errors[0].message == "Exception: unexpected"


@pytest.mark.asyncio
async def test_request_sets_in_scope_metadata(capture, mock_flow, mocker):
    mock_flow.request.pretty_host = "example.com"
    mock_flow.metadata = {}
    capture.flow_scope.apply_scope.return_value = True
    mocker.patch("vex_cli.proxy.flow_to_raw_request", return_value=b"raw")
    mocker.patch("vex_cli.proxy.RequestSummary.from_flow", return_value=MagicMock())
    mocker.patch("vex_cli.proxy.RawRequest.from_flow", return_value=MagicMock())
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    capture.flow_scope.apply_scope.assert_called_once_with("example.com")
    assert mock_flow.metadata["in_scope"] is True


@pytest.mark.asyncio
async def test_request_skips_out_of_scope(capture, mock_flow, mocker):
    mock_flow.request.pretty_host = "evil.com"
    mock_flow.metadata = {}
    capture.flow_scope.apply_scope.return_value = False
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    # Should not try to create summary if out of scope
    capture._save_and_broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_response_does_nothing_if_no_active_project(capture, mock_flow):
    capture.app_state.is_project_active = False

    await capture.response(mock_flow)

    capture.flow_history.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_response_calls_save_and_broadcast(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=ResponseSummary)
    mock_raw = MagicMock(spec=RawResponse)
    mocker.patch("vex_cli.proxy.flow_to_raw_response", return_value=b"raw response bytes")
    mocker.patch("vex_cli.proxy.ResponseSummary.from_flow", return_value=mock_summary)
    mocker.patch("vex_cli.proxy.RawResponse.from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_flow, mock_summary, mock_raw)


@pytest.mark.asyncio
async def test_response_does_not_raise_on_exception(capture, mock_flow, mocker):
    mocker.patch(
        "vex_cli.proxy.flow_to_raw_response", side_effect=Exception("unexpected")
    )

    await capture.response(mock_flow)  # should not raise

    errors = error_events(capture)
    assert len(errors) == 1
    assert errors[0].kind == "unknown"
    assert errors[0].message == "Exception: unexpected"


@pytest.mark.asyncio
async def test_response_returns_early_when_not_in_scope(capture, mock_flow):
    mock_flow.metadata = {"in_scope": False}
    capture.flow_history.broadcast = AsyncMock()
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    # Should not try to create summary if out of scope
    capture._save_and_broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_response_processes_in_scope_flows(capture, mock_flow, mocker):
    mock_flow.metadata = {"in_scope": True}

    mock_summary = MagicMock(spec=ResponseSummary)
    mock_raw = MagicMock(spec=RawResponse)
    mocker.patch("vex_cli.proxy.flow_to_raw_response", return_value=b"raw")
    mocker.patch("vex_cli.proxy.ResponseSummary.from_flow", return_value=mock_summary)
    mocker.patch("vex_cli.proxy.RawResponse.from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_flow, mock_summary, mock_raw)


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", ["request", "response"])
@pytest.mark.parametrize(
    ("exc", "expected_kind"),
    [
        (DatabaseError("db down"), "database"),
        (VexValidationError("Record already exists"), "database"),
        (ValueError("bad value"), "parse"),
        (TypeError("bad type"), "parse"),
        (RuntimeError("unexpected"), "unknown"),
    ],
)
async def test_capture_error_classification(
    capture, mock_flow, mocker, handler, exc, expected_kind
):
    if handler == "request":
        mocker.patch("vex_cli.proxy.flow_to_raw_request", side_effect=exc)
    else:
        mocker.patch("vex_cli.proxy.flow_to_raw_response", side_effect=exc)

    await getattr(capture, handler)(mock_flow)

    errors = error_events(capture)
    assert len(errors) == 1
    assert errors[0].kind == expected_kind
    assert errors[0].host == "example.com"
    assert not any(
        isinstance(c.args[0], (RequestSummary, ResponseSummary))
        for c in capture.flow_history.broadcast.call_args_list
    )


@pytest.mark.asyncio
async def test_save_and_broadcast_saves_to_summaries_db(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    capture.db_manager.summaries_db.create.assert_called_once_with(
        mock_summary.to_orm()
    )


@pytest.mark.asyncio
async def test_save_and_broadcast_saves_to_raw_db(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    capture.db_manager.raw_db.create.assert_called_once_with(mock_raw.to_orm())


@pytest.mark.asyncio
async def test_save_and_broadcast_broadcasts_summary(capture, mock_flow):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    capture.flow_history.broadcast.assert_called_once_with(mock_summary)


@pytest.mark.asyncio
async def test_save_and_broadcast_skips_when_no_active_project(capture, mock_flow):
    capture.db_manager.active_databases.return_value = None
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    capture.db_manager.summaries_db.create.assert_not_called()
    capture.db_manager.raw_db.create.assert_not_called()
    capture.flow_history.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_save_and_broadcast_uses_snapshot_databases(capture, mock_flow):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)
    summaries_db, raw_db = capture.db_manager.active_databases.return_value

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    summaries_db.create.assert_called_once()
    raw_db.create.assert_called_once()


@pytest.mark.asyncio
async def test_save_and_broadcast_writes_summaries_before_raw(capture, mock_flow):
    """The summary must be durable before the raw write starts, so a raw
    failure has something to roll back."""
    calls = []

    async def create_summary(orm):
        calls.append("summary")
        return orm

    async def create_raw(orm):
        calls.append("raw")
        return orm

    capture.db_manager.summaries_db.create = AsyncMock(side_effect=create_summary)
    capture.db_manager.raw_db.create = AsyncMock(side_effect=create_raw)

    await capture._save_and_broadcast(
        mock_flow, 
        MagicMock(spec=RequestSummary), MagicMock(spec=RawRequest)
    )

    assert calls == ["summary", "raw"]


@pytest.mark.asyncio
async def test_save_and_broadcast_sets_summary_id_before_broadcast(capture, mock_flow):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)
    capture.db_manager.summaries_db.create.return_value.id = 42

    await capture._save_and_broadcast(mock_flow, mock_summary, mock_raw)

    assert mock_summary.id == 42
    capture.flow_history.broadcast.assert_called_once_with(mock_summary)


@pytest.mark.asyncio
async def test_save_and_broadcast_propagates_summary_create_failure(capture, mock_flow):
    capture.db_manager.summaries_db.create = AsyncMock(
        side_effect=DatabaseError("summary write failed")
    )
    mock_summary = MagicMock(spec=RequestSummary)

    with pytest.raises(DatabaseError):
        await capture._save_and_broadcast(
            mock_flow, mock_summary, MagicMock(spec=RawRequest)
        )

    capture.db_manager.raw_db.create.assert_not_called()
    capture.db_manager.summaries_db.delete_by_flow_id.assert_not_called()
    capture.flow_history.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_request_reports_database_error_when_summary_create_fails(
    capture, mock_flow, mocker
):
    mocker.patch("vex_cli.proxy.flow_to_raw_request", return_value=b"raw")
    mocker.patch("vex_cli.proxy.RequestSummary.from_flow", return_value=MagicMock())
    mocker.patch("vex_cli.proxy.RawRequest.from_flow", return_value=MagicMock())
    capture.db_manager.summaries_db.create = AsyncMock(
        side_effect=VexValidationError("Record already exists")
    )

    await capture.request(mock_flow)

    errors = error_events(capture)
    assert len(errors) == 1
    assert errors[0].kind == "database"
    assert errors[0].message == "ValidationError: Record already exists"
    assert not any(
        isinstance(c.args[0], (RequestSummary, ResponseSummary))
        for c in capture.flow_history.broadcast.call_args_list
    )


@pytest.mark.asyncio
async def test_save_and_broadcast_rolls_back_summary_when_raw_fails(capture, mock_flow):
    capture.db_manager.raw_db.create = AsyncMock(
        side_effect=DatabaseError("raw db failed")
    )
    mock_summary = MagicMock(spec=RequestSummary)
    mock_summary.flow_id = uuid4()  # pydantic fields aren't visible to spec
    created = capture.db_manager.summaries_db.create.return_value

    await capture._save_and_broadcast(mock_flow, mock_summary, MagicMock(spec=RawRequest))

    capture.db_manager.summaries_db.delete_by_flow_id.assert_called_once_with(
        type(created), mock_summary.flow_id
    )
    errors = error_events(capture)
    assert len(errors) == 1
    assert errors[0].kind == "database"
    assert errors[0].host == "example.com"
    assert errors[0].message == "DatabaseError: raw db failed"
    assert not any(
        isinstance(c.args[0], (RequestSummary, ResponseSummary))
        for c in capture.flow_history.broadcast.call_args_list
    )


@pytest.mark.asyncio
async def test_save_and_broadcast_survives_rollback_failure(capture, mock_flow):
    """If the rollback itself fails, the flow is dropped (no summary broadcast)
    and the error is contained."""
    capture.db_manager.raw_db.create = AsyncMock(
        side_effect=DatabaseError("raw db failed")
    )
    capture.db_manager.summaries_db.delete_by_flow_id = AsyncMock(
        side_effect=DatabaseError("database is locked")
    )
    mock_summary = MagicMock(spec=RequestSummary)
    mock_summary.flow_id = uuid4()  # pydantic fields aren't visible to spec

    await capture._save_and_broadcast(mock_flow, mock_summary, MagicMock(spec=RawRequest))

    events = [c.args[0] for c in capture.flow_history.broadcast.call_args_list]
    errors = error_events(capture)

    assert len(errors) == 2
    assert {e.message for e in errors} == {
        "DatabaseError: raw db failed",
        "DatabaseError: database is locked",
    }
    assert not any(isinstance(e, (RequestSummary, ResponseSummary)) for e in events)


@pytest.mark.asyncio
async def test_capture_error_method_passes(capture, mock_flow):
    # Just ensures it doesn't raise
    await capture.error(mock_flow)


@pytest.mark.asyncio
async def test_report_capture_error_builds_event(capture, mocker):
    mocker.patch("vex_cli.proxy.time.time", return_value=123.456)

    await capture._report_capture_error(
        "example.com", DatabaseError("db down"), kind="database"
    )

    capture.flow_history.broadcast.assert_called_once_with(
        CaptureErrorEvent(
            kind="database",
            message="DatabaseError: db down",
            host="example.com",
            timestamp=123.456,
        )
    )


@pytest.mark.asyncio
async def test_report_capture_error_message_format(capture):
    await capture._report_capture_error(
        "example.com", TypeError("bad type"), kind="parse"
    )

    event = error_events(capture)[0]
    assert event.message == "TypeError: bad type"


@pytest.mark.asyncio
@pytest.mark.parametrize("host", [None, ""])
async def test_report_capture_error_normalizes_empty_host(capture, host):
    await capture._report_capture_error(host, ValueError("x"), kind="parse")

    event = error_events(capture)[0]
    assert event.host is None


@pytest.mark.asyncio
async def test_report_capture_error_survives_broadcast_failure(capture):
    capture.flow_history.broadcast = AsyncMock(side_effect=RuntimeError("ws down"))

    await capture._report_capture_error("example.com", ValueError("x"), kind="parse")

    capture.flow_history.broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_start_proxy_adds_addon(mock_app_state, mocker):
    mock_master = MagicMock()
    mock_master.run = AsyncMock()
    mocker.patch("vex_cli.proxy.DumpMaster", return_value=mock_master)

    await start_proxy(mock_app_state)

    mock_master.addons.add.assert_called_once()
    added = mock_master.addons.add.call_args[0][0]
    assert isinstance(added, VexCapture)


@pytest.mark.asyncio
async def test_start_proxy_stores_master_on_cancel(mock_app_state, mocker):
    mock_master = MagicMock()
    mock_master.run = AsyncMock(side_effect=asyncio.CancelledError)
    mocker.patch("vex_cli.proxy.DumpMaster", return_value=mock_master)

    await start_proxy(mock_app_state)

    assert mock_app_state.mitmproxy_master is mock_master


@pytest.mark.asyncio
async def test_start_proxy_stores_master_on_success(mock_app_state, mocker):
    mock_master = MagicMock()
    mock_master.run = AsyncMock()
    mocker.patch("vex_cli.proxy.DumpMaster", return_value=mock_master)

    await start_proxy(mock_app_state)

    assert mock_app_state.mitmproxy_master is mock_master


@pytest.mark.asyncio
async def test_start_proxy_uses_correct_options(mock_app_state, mocker):
    mock_master = MagicMock()
    mock_master.run = AsyncMock()
    mock_options_cls = mocker.patch("vex_cli.proxy.Options")
    mocker.patch("vex_cli.proxy.DumpMaster", return_value=mock_master)
    server_info = mock_app_state.get_server_info()

    await start_proxy(mock_app_state)

    mock_options_cls.assert_called_once_with(
        listen_host=server_info.server_address,
        listen_port=server_info.proxy_port,
        http2=True,
    )
