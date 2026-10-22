import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from vex_cli.models.pydantic import FlowSummary, Project, RequestSummary, Scope, VexServerInfo
from vex_client.api.client import ApiClient
from vex_client.app import VexApp
from vex_client.connection_manager import ConnectionState
from vex_client.proxy.screen import VexProxyScreen

def server():
    return VexServerInfo(server_address="127.0.0.1", proxy_port=8080, api_port=8000)


def request():
    return RequestSummary(
        id=1, flow_id=uuid4(), host="example.com", method="GET", path="/",
        request_size=10, is_tls=True, query=None, file_extension=None, timestamp=1.0,
    )


def project():
    return Project(id=uuid4(), name="History", created_at=1.0, updated_at=1.0)


def avoid_local_discovery(monkeypatch):
    monkeypatch.setattr(VexProxyScreen, "_discover_local_instance", AsyncMock(return_value=None))
    monkeypatch.setattr(VexProxyScreen, "_check_local_process", lambda self: None)



async def test_history_opened_while_loading_uses_manager_state(monkeypatch):
    avoid_local_discovery(monkeypatch)
    app = VexApp()
    async with app.run_test() as pilot:
        app.server_online = True
        app.active_project = project()
        app.history_manager.start_project()
        summary = FlowSummary(**request().model_dump())
        started = asyncio.Event()
        release = asyncio.Event()

        async def fetch(skip, size):
            started.set()
            await release.wait()
            return [summary]

        api = cast(ApiClient, SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=fetch)))
        task = asyncio.create_task(app.history_manager.load_summaries(api))
        try:
            await started.wait()
            await app.switch_screen("history-screen")
            await pilot.pause()
            assert app.history_manager.is_loading
            assert app.history_screen.http_table_empty._cover_widget is not None
            release.set()
            await task
            await pilot.pause()
            assert app.history_screen.http_table.row_exists(str(summary.flow_id))
            assert app.history_screen.http_table_empty._cover_widget is None
        finally:
            release.set()
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


async def test_disconnect_preserves_visible_history_but_blocks_return_navigation(monkeypatch):
    avoid_local_discovery(monkeypatch)
    app = VexApp()
    async with app.run_test() as pilot:
        app.server_online = True
        app.active_project = project()
        app.history_manager.start_project()
        summary = request()
        app.history_manager._handle_message(summary.model_dump_json())
        await app.switch_screen("history-screen")
        screen = app.history_screen
        screen.request_refresh()
        await pilot.pause()
        assert screen.http_table.row_exists(str(summary.flow_id))
        screen.request_area.text = "already displayed request"
        screen.response_area.text = "already displayed response"
        app.active_scope = Scope(id=1, name="All", allow_endpoints=[], deny_endpoints=[])
        await pilot.pause()
        screen.request_area.text = "already displayed request"
        screen.response_area.text = "already displayed response"

        app.server_online = False
        app._end_session()
        await pilot.pause()
        assert summary.flow_id in app.history_manager.summaries
        assert screen.http_table.row_exists(str(summary.flow_id))
        assert screen.request_area.text == "already displayed request"
        assert screen.response_area.text == "already displayed response"

        app.switch_screen("projects-screen")
        await pilot.pause()
        await pilot.press("ctrl+q")
        await pilot.pause()
        assert app.screen is app.projects_screen
        assert screen.http_table.row_exists(str(summary.flow_id))
        assert screen.http_table.get_cell_raw_value("Host", str(summary.flow_id)) == summary.host


async def test_switching_project_replaces_previous_history(monkeypatch):
    avoid_local_discovery(monkeypatch)
    app = VexApp()
    async with app.run_test() as pilot:
        app.server_online = True
        old_project = project()
        app.active_project = old_project
        app.history_manager.start_project()
        old_summary = request()
        app.history_manager._handle_message(old_summary.model_dump_json())
        await app.switch_screen("history-screen")
        app.history_screen.request_refresh()
        await pilot.pause()
        assert app.history_screen.http_table.row_exists(str(old_summary.flow_id))

        app.connection_manager._server_info = server()
        app.connection_manager._state = ConnectionState.CONNECTED
        app.connection_manager._api_client = cast(
            ApiClient,
            SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=AsyncMock(return_value=[]))),
        )
        monkeypatch.setattr(app, "_fetch_scopes", lambda: None)
        monkeypatch.setattr(app, "_fetch_active_scope", lambda: None)
        app.set_project(project())
        await pilot.pause()
        assert not app.history_manager.summaries
        assert not app.history_screen.http_table.row_exists(str(old_summary.flow_id))
        app.connection_manager._api_client = None
        app.connection_manager._state = ConnectionState.DISCONNECTED


async def test_reconnect_to_same_project_reloads_from_empty_cache(monkeypatch):
    avoid_local_discovery(monkeypatch)
    app = VexApp()
    async with app.run_test() as pilot:
        original_project = project()
        app.server_online = True
        app.active_project = original_project
        app.history_manager.start_project()
        previous = request()
        app.history_manager._handle_message(previous.model_dump_json())

        app.server_online = False
        app._end_session()
        assert previous.flow_id in app.history_manager.summaries

        incoming = FlowSummary(**request().model_dump())
        fetch = AsyncMock(return_value=[incoming])
        app.connection_manager._server_info = server()
        app.connection_manager._state = ConnectionState.CONNECTED
        app.connection_manager._api_client = cast(
            ApiClient, SimpleNamespace(summaries=SimpleNamespace(get_all_summaries=fetch))
        )
        monkeypatch.setattr(app, "_fetch_scopes", lambda: None)
        monkeypatch.setattr(app, "_fetch_active_scope", lambda: None)
        app.server_online = True
        app.set_project(original_project)
        assert previous.flow_id not in app.history_manager.summaries
        await pilot.pause()
        assert list(app.history_manager.summaries) == [incoming.flow_id]
        fetch.assert_awaited_once_with(0, 50)
        app.connection_manager._api_client = None
        app.connection_manager._state = ConnectionState.DISCONNECTED
