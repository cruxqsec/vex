import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from vex_cli.app import create_app, start_fastapi
from vex_cli.errors import AppException


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_app_state():
    server_info = MagicMock()
    server_info.server_address = "127.0.0.1"
    server_info.api_port = 8081
    state = MagicMock()
    state.get_server_info.return_value = server_info
    return state


def test_create_app_returns_fastapi_instance(app):
    from fastapi import FastAPI

    assert isinstance(app, FastAPI)


def test_health_router_registered(app):
    routes = [r.path for r in app.routes]
    assert any("health" in path for path in routes)


def test_projects_router_registered(app):
    routes = [r.path for r in app.routes]
    assert any("projects" in path for path in routes)


def test_summary_router_registered(app):
    routes = [r.path for r in app.routes]
    assert any("summar" in path for path in routes)


def test_raw_router_registered(app):
    routes = [r.path for r in app.routes]
    assert any("raw" in path for path in routes)


def test_websocket_router_registered(app):
    routes = [r.path for r in app.routes]
    assert any("ws" in path for path in routes)


def test_all_api_routes_have_correct_prefix(app):
    routes = [r.path for r in app.routes]
    assert any(r.startswith("/api") for r in routes)


def test_app_exception_handler_returns_correct_status(client):
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/test-app-exception")
    def raise_app_exception():
        raise AppException(status_code=404, message="Not found")

    client.app.include_router(router)
    response = client.get("/test-app-exception")

    assert response.status_code == 404
    assert response.json()["error"] == "AppException"
    assert response.json()["message"] == "Not found"


def test_app_exception_handler_500_response(client):
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/test-500-app-exception")
    def raise_500():
        raise AppException(status_code=500, message="Internal error")

    client.app.include_router(router)
    response = client.get("/test-500-app-exception")

    assert response.status_code == 500
    assert response.json()["message"] == "Internal error"


def test_catch_all_handler_returns_500(client):
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/test-unexpected")
    def raise_unexpected():
        raise Exception("something broke")

    client.app.include_router(router)
    response = client.get("/test-unexpected")

    assert response.status_code == 500
    assert response.json()["error"] == "InternalServerError"
    assert response.json()["message"] == "Something went wrong"


@pytest.mark.asyncio
async def test_start_fastapi_stores_server_on_cancel(mock_app_state, mocker):
    mock_server = MagicMock()
    mock_server.serve = AsyncMock(side_effect=asyncio.CancelledError)
    mocker.patch("vex_cli.app.uvicorn.Server", return_value=mock_server)
    mocker.patch("vex_cli.app.uvicorn.Config", return_value=MagicMock())

    await start_fastapi(mock_app_state)

    assert mock_app_state.uvicorn_server is mock_server


@pytest.mark.asyncio
async def test_start_fastapi_stores_server_on_success(mock_app_state, mocker):
    mock_server = MagicMock()
    mock_server.serve = AsyncMock()
    mocker.patch("vex_cli.app.uvicorn.Server", return_value=mock_server)
    mocker.patch("vex_cli.app.uvicorn.Config", return_value=MagicMock())

    await start_fastapi(mock_app_state)

    assert mock_app_state.uvicorn_server is mock_server


# ------------ VexApp API client ownership tests ------------


def _make_vex_app(mocker) -> "VexApp":
    from vex_client.app import VexApp

    mocker.patch.object(VexApp, "on_mount", AsyncMock())
    app = VexApp()
    app.vex_controller = MagicMock()
    app.vex_controller.server_info = None
    app._api_client = None
    app._api_info = None
    return app


def _mock_api_client(mocker) -> MagicMock:
    client = MagicMock()
    client.aclose = AsyncMock()
    client.is_closed = False
    return client


@pytest.mark.asyncio
async def test_close_api_closes_client_and_forgets(mocker):
    app = _make_vex_app(mocker)
    client = _mock_api_client(mocker)
    app._api_client = client
    app._api_info = ("127.0.0.1", 8081)

    await app.close_api()

    client.aclose.assert_awaited_once()
    assert app._api_client is None
    assert app._api_info is None


@pytest.mark.asyncio
async def test_close_api_no_client_is_noop(mocker):
    app = _make_vex_app(mocker)
    app._api_info = ("127.0.0.1", 8081)

    await app.close_api()

    assert app._api_client is None
    assert app._api_info is None


@pytest.mark.asyncio
async def test_adopt_api_sets_ownership(mocker):
    app = _make_vex_app(mocker)
    client = _mock_api_client(mocker)

    await app.adopt_api(client, ("127.0.0.1", 8081))

    assert app._api_client is client
    assert app._api_info == ("127.0.0.1", 8081)
    client.aclose.assert_not_awaited()
    await app.close_api()  # cleanup for the test-created client object


@pytest.mark.asyncio
async def test_adopt_api_closes_previous_client(mocker):
    app = _make_vex_app(mocker)
    old_client = _mock_api_client(mocker)
    new_client = _mock_api_client(mocker)
    app._api_client = old_client
    app._api_info = ("127.0.0.1", 8081)

    await app.adopt_api(new_client, ("127.0.0.2", 9090))

    old_client.aclose.assert_awaited_once()
    assert app._api_client is new_client
    assert app._api_info == ("127.0.0.2", 9090)
    new_client.aclose.assert_not_awaited()
    await app.close_api()  # cleanup for the test-created client object


@pytest.mark.asyncio
async def test_api_client_property_none_without_server_info():
    from vex_client.app import VexApp

    app = VexApp()
    app.vex_controller = MagicMock()
    app.vex_controller.server_info = None
    app._api_client = None
    app._api_info = None

    assert app.api_client is None
    assert app._api_client is None


@pytest.mark.asyncio
async def test_api_client_property_rebuild_closes_stale_client(mocker):
    app = _make_vex_app(mocker)

    def _fake_api_client(host: str, port: int, client=None):
        mock = _mock_api_client(mocker)
        mock._constructed_with = (host, port)
        return mock

    mocker.patch("vex_client.app.ApiClient", side_effect=_fake_api_client)

    server_info = MagicMock()
    server_info.server_address = "127.0.0.1"
    server_info.api_port = 8081
    app.vex_controller.server_info = server_info

    old_client = _mock_api_client(mocker)
    app._api_client = old_client
    app._api_info = ("127.0.0.1", 9999)

    client = app.api_client
    assert client is not None
    assert client is not old_client
    assert client._constructed_with == ("127.0.0.1", 8081)
    assert app._api_info == ("127.0.0.1", 8081)

    # stale close is fire-and-forget (property rebuild path, option A)
    await asyncio.sleep(0)
    old_client.aclose.assert_awaited_once()

    # teardown: nothing real leaked; every client is a mock
    await app.close_api()
    client.aclose.assert_awaited_once()
    old_client.aclose.assert_awaited_once()
