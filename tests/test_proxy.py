import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from vex_cli.models.pydantic import (
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
    VexServerInfo,
)
from vex_cli.proxy import VexCapture, start_proxy
from vex_cli.flow_scope import FlowScope


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
    state.get_db_manager.return_value = MagicMock()
    state.get_db_manager().summaries_db.create = AsyncMock()
    state.get_db_manager().raw_db.create = AsyncMock()
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
    return flow


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

    capture.flow_history.broadcast_summary.assert_not_called()


@pytest.mark.asyncio
async def test_request_calls_save_and_broadcast(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)
    mocker.patch.object(RequestSummary, "from_flow", return_value=mock_summary)
    mocker.patch.object(RawRequest, "from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_summary, mock_raw)


@pytest.mark.asyncio
async def test_request_does_not_raise_on_exception(capture, mock_flow, mocker):
    mocker.patch.object(
        RequestSummary, "from_flow", side_effect=Exception("unexpected")
    )

    await capture.request(mock_flow)


@pytest.mark.asyncio
async def test_request_sets_in_scope_metadata(capture, mock_flow, mocker):
    mock_flow.request.pretty_host = "example.com"
    mock_flow.metadata = {}
    capture.flow_scope.apply_scope.return_value = True
    mocker.patch.object(RequestSummary, "from_flow", return_value=MagicMock())
    mocker.patch.object(RawRequest, "from_flow", return_value=MagicMock())
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    capture.flow_scope.apply_scope.assert_called_once_with("example.com")
    assert mock_flow.metadata["in_scope"] is True


@pytest.mark.asyncio
async def test_request_skips_out_of_scope(capture, mock_flow, mocker):
    mock_flow.request.pretty_host = "evil.com"
    mock_flow.metadata = {}
    capture.flow_scope.apply_scope.return_value = False
    mocker.patch.object(RequestSummary, "from_flow")
    capture._save_and_broadcast = AsyncMock()

    await capture.request(mock_flow)

    # Should not try to create summary if out of scope
    capture._save_and_broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_response_does_nothing_if_no_active_project(capture, mock_flow):
    capture.app_state.is_project_active = False

    await capture.response(mock_flow)

    capture.flow_history.broadcast_summary.assert_not_called()


@pytest.mark.asyncio
async def test_response_calls_save_and_broadcast(capture, mock_flow, mocker):
    mock_summary = MagicMock(spec=ResponseSummary)
    mock_raw = MagicMock(spec=RawResponse)
    mocker.patch.object(ResponseSummary, "from_flow", return_value=mock_summary)
    mocker.patch.object(RawResponse, "from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_summary, mock_raw)


@pytest.mark.asyncio
async def test_response_does_not_raise_on_exception(capture, mock_flow, mocker):
    mocker.patch.object(
        ResponseSummary, "from_flow", side_effect=Exception("unexpected")
    )

    await capture.response(mock_flow)  # should not raise


@pytest.mark.asyncio
async def test_response_returns_early_when_not_in_scope(capture, mock_flow):
    mock_flow.metadata = {"in_scope": False}
    capture.flow_history.broadcast_summary = AsyncMock()
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    # Should not try to create summary if out of scope
    capture._save_and_broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_response_processes_in_scope_flows(capture, mock_flow, mocker):
    mock_flow.metadata = {"in_scope": True}

    mock_summary = MagicMock(spec=ResponseSummary)
    mock_raw = MagicMock(spec=RawResponse)
    mocker.patch.object(ResponseSummary, "from_flow", return_value=mock_summary)
    mocker.patch.object(RawResponse, "from_flow", return_value=mock_raw)
    capture._save_and_broadcast = AsyncMock()

    await capture.response(mock_flow)

    capture._save_and_broadcast.assert_called_once_with(mock_summary, mock_raw)


@pytest.mark.asyncio
async def test_save_and_broadcast_saves_to_summaries_db(capture, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_summary, mock_raw)

    capture.db_manager.summaries_db.create.assert_called_once_with(
        mock_summary.to_orm()
    )


@pytest.mark.asyncio
async def test_save_and_broadcast_saves_to_raw_db(capture, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_summary, mock_raw)

    capture.db_manager.raw_db.create.assert_called_once_with(mock_raw.to_orm())


@pytest.mark.asyncio
async def test_save_and_broadcast_broadcasts_summary(capture):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)

    await capture._save_and_broadcast(mock_summary, mock_raw)

    capture.flow_history.broadcast_summary.assert_called_once_with(mock_summary)


@pytest.mark.asyncio
async def test_save_and_broadcast_saves_concurrently(capture, mocker):
    mock_summary = MagicMock(spec=RequestSummary)
    mock_raw = MagicMock(spec=RawRequest)
    gather_spy = mocker.patch("vex_cli.proxy.asyncio.gather", wraps=asyncio.gather)

    await capture._save_and_broadcast(mock_summary, mock_raw)

    gather_spy.assert_called_once()


@pytest.mark.asyncio
async def test_capture_error_method_passes(capture, mock_flow):
    # Just ensures it doesn't raise
    await capture.error(mock_flow)


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
