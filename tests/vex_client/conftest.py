import logging
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from vex_cli import locations
from vex_cli.models.pydantic import Project
from vex_client.api.client import ApiClient
from vex_client.app import VexApp
from vex_client.connection_manager import ConnectionState
from vex_client.proxy.screen import VexProxyScreen


@pytest.fixture(autouse=True)
def isolated_vex_data(tmp_path, monkeypatch):
    directories = (
        locations.vex_data_directory,
        locations.vex_projects_directory,
        locations.vex_log_directory,
        locations.vex_tree_sitter_directory,
    )
    monkeypatch.setattr(locations, "user_data_dir", lambda app: str(tmp_path / "vex"))
    for directory in directories:
        directory.cache_clear()

    logger = logging.getLogger("vex_client")
    original_handlers = tuple(logger.handlers)
    original_level = logger.level
    try:
        yield tmp_path / "vex"
    finally:
        for handler in tuple(logger.handlers):
            if handler not in original_handlers:
                logger.removeHandler(handler)
                handler.close()
        logger.setLevel(original_level)
        for directory in directories:
            directory.cache_clear()


@pytest.fixture
def project_factory():
    def factory():
        return Project(id=uuid4(), name="History view", created_at=1.0, updated_at=1.0)

    return factory


@pytest.fixture
def history_app(monkeypatch, isolated_vex_data):
    monkeypatch.setattr(
        VexProxyScreen, "_discover_local_instance", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(VexProxyScreen, "_check_local_process", lambda self: None)
    app = VexApp()
    monkeypatch.setattr(app, "_fetch_scopes", lambda: None)
    monkeypatch.setattr(app, "_fetch_active_scope", lambda: None)
    return app


@pytest.fixture
def mock_api():
    return SimpleNamespace(
        raw=SimpleNamespace(
            get_raw_request=AsyncMock(return_value=SimpleNamespace(data=b"request")),
            get_raw_response=AsyncMock(return_value=SimpleNamespace(data=b"response")),
        ),
        summaries=SimpleNamespace(
            get_all_summaries=AsyncMock(return_value=[]),
            delete_all_flows=AsyncMock(return_value=True),
            delete_flow=AsyncMock(return_value=True),
        ),
    )


@pytest.fixture
def opened_history(mock_api, project_factory):
    @asynccontextmanager
    async def open_history(app):
        async with app.run_test(size=(140, 45)) as pilot:
            app.server_online = True
            app.active_project = project_factory()
            app.history_manager.start_project()
            app.connection_manager._state = ConnectionState.CONNECTED
            app.connection_manager._api_client = cast(ApiClient, mock_api)
            try:
                app.switch_screen("history-screen")
                await pilot.pause()
                yield pilot, app.history_screen, mock_api
            finally:
                app.connection_manager._api_client = None
                app.connection_manager._state = ConnectionState.DISCONNECTED

    return open_history
