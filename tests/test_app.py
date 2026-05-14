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
async def test_start_fastapi_shuts_down_on_cancel(mock_app_state, mocker):
    mock_server = MagicMock()
    mock_server.serve = AsyncMock(side_effect=asyncio.CancelledError)
    mock_server.shutdown = AsyncMock()
    mocker.patch("vex_cli.app.uvicorn.Server", return_value=mock_server)
    mocker.patch("vex_cli.app.uvicorn.Config", return_value=MagicMock())

    await start_fastapi(mock_app_state)

    mock_server.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_start_fastapi_shuts_down_even_if_cleanup_fails(mock_app_state, mocker):
    mock_server = MagicMock()
    mock_server.serve = AsyncMock(side_effect=asyncio.CancelledError)
    mock_server.shutdown = AsyncMock(side_effect=Exception("cleanup failed"))
    mocker.patch("vex_cli.app.uvicorn.Server", return_value=mock_server)
    mocker.patch("vex_cli.app.uvicorn.Config", return_value=MagicMock())

    await start_fastapi(mock_app_state)
