# tests/test_websockets.py
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

from vex_cli.app import create_app
from vex_cli.dependencies import get_flow_history
from vex_cli.flow_history import FlowHistory
from vex_cli.models.pydantic import RequestSummary
from uuid import uuid4
from datetime import datetime, timezone


def make_request_summary():
    return RequestSummary(
        flow_id=uuid4(),
        host="example.com",
        method="GET",
        path="/test",
        request_size=123,
        is_tls=False,
        query=None,
        file_extension=None,
        timestamp=datetime.now(timezone.utc).timestamp(),
    )


@pytest.fixture
def mock_flow_history():
    return AsyncMock(spec=FlowHistory)


@pytest.fixture
def ws_client(mock_flow_history):
    app = create_app()
    app.dependency_overrides[get_flow_history] = lambda: mock_flow_history
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# --- /ws/history ---

def test_history_websocket_accepts_connection(ws_client, mock_flow_history):
    queue = asyncio.Queue()
    mock_flow_history.subscribe = AsyncMock(return_value=queue)
    mock_flow_history.unsubscribe = AsyncMock()

    with ws_client.websocket_connect("/ws/history") as ws:
        ws.close()


def test_history_websocket_sends_summary(ws_client, mock_flow_history):
    summary = make_request_summary()
    queue = asyncio.Queue()
    queue.put_nowait(summary)
    mock_flow_history.subscribe = AsyncMock(return_value=queue)
    mock_flow_history.unsubscribe = AsyncMock()

    with ws_client.websocket_connect("/ws/history") as ws:
        data = ws.receive_text()

    received = json.loads(data)
    assert received["host"] == "example.com"
    assert received["method"] == "GET"


def test_history_websocket_unsubscribes_on_disconnect(ws_client, mock_flow_history):
    queue = asyncio.Queue()
    mock_flow_history.subscribe = AsyncMock(return_value=queue)
    mock_flow_history.unsubscribe = AsyncMock()

    with ws_client.websocket_connect("/ws/history") as ws:
        pass

    mock_flow_history.unsubscribe.assert_called_once_with(queue)


def test_history_websocket_unsubscribes_on_exception(ws_client, mock_flow_history):
    queue = asyncio.Queue()
    mock_flow_history.subscribe = AsyncMock(return_value=queue)
    mock_flow_history.unsubscribe = AsyncMock()

    with ws_client.websocket_connect("/ws/history") as ws:
        pass

    mock_flow_history.unsubscribe.assert_called_once()


# --- /ws/intercept ---

def test_intercept_websocket_accepts_connection(ws_client, mock_flow_history):
    mock_flow_history.subscribe = AsyncMock(return_value=asyncio.Queue())
    mock_flow_history.unsubscribe = AsyncMock()

    with ws_client.websocket_connect("/ws/intercept") as ws:
        pass