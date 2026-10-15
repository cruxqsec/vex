import asyncio
import logging
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

from vex_cli.api.websockets import (  # adjust to your module path
    history_websocket,
    send_events_to_client,
    wait_for_client_disconnect_event,
)
from vex_cli.errors import VexClientDisconnectEvent


async def test_ping_connects(ws_connect):
    async with ws_connect("/ping"):
        pass


async def test_history_subscribes_on_connect(ws_connect, flow_history):
    async with ws_connect("/history"):
        assert len(flow_history._subscribers) == 1


async def test_history_unsubscribes_on_client_disconnect(
    ws_connect, flow_history, caplog
):
    with caplog.at_level(logging.INFO):
        async with ws_connect("/history"):
            pass

    assert not flow_history._subscribers
    assert "Flow history client disconnected" in caplog.text


async def test_history_streams_broadcast_event(
    ws_connect, flow_history, request_summary
):
    summary = request_summary()

    async with ws_connect("/history") as ws:
        flow_history.broadcast(summary)
        async with asyncio.timeout(2):
            message = await ws.receive_json()

    assert message["flow_id"] == str(summary.flow_id)
    assert message["host"] == summary.host


async def test_history_streams_events_in_order(
    ws_connect, flow_history, request_summary, response_summary
):
    req, res = request_summary(), response_summary()

    async with ws_connect("/history") as ws:
        flow_history.broadcast(req)
        flow_history.broadcast(res)
        async with asyncio.timeout(2):
            first = await ws.receive_json()
            second = await ws.receive_json()

    assert first["flow_id"] == str(req.flow_id)
    assert second["status_code"] == res.status_code


async def test_history_broadcasts_to_all_clients(
    ws_connect, flow_history, request_summary
):
    summary = request_summary()

    async with ws_connect("/history") as a, ws_connect("/history") as b:
        flow_history.broadcast(summary)
        async with asyncio.timeout(2):
            msg_a = await a.receive_json()
            msg_b = await b.receive_json()

    assert msg_a["flow_id"] == msg_b["flow_id"] == str(summary.flow_id)


@pytest.fixture
def fake_ws(flow_history, request_summary):
    ws = AsyncMock()

    async def never():
        await asyncio.Event().wait()

    async def accept():
        flow_history.broadcast(request_summary())

    ws.receive.side_effect = never
    ws.accept.side_effect = accept
    return ws


async def test_wait_raises_on_disconnect_message():
    ws = AsyncMock()
    ws.receive.side_effect = [
        {"type": "websocket.receive"},
        {"type": "websocket.disconnect"},
    ]

    with pytest.raises(VexClientDisconnectEvent):
        await wait_for_client_disconnect_event(ws)

    assert ws.receive.await_count == 2


async def test_send_propagates_websocket_disconnect(request_summary):
    ws = AsyncMock()
    ws.send_text.side_effect = WebSocketDisconnect()
    queue = asyncio.Queue()
    queue.put_nowait(request_summary())

    with pytest.raises(WebSocketDisconnect):
        await send_events_to_client(ws, queue)


async def test_history_catches_send_disconnect(fake_ws, flow_history, caplog):
    fake_ws.send_text.side_effect = WebSocketDisconnect()

    with caplog.at_level(logging.INFO):
        await history_websocket(fake_ws, flow_history)

    assert "Flow history client disconnected" in caplog.text
    assert not flow_history._subscribers


async def test_history_does_not_swallow_unexpected_errors(fake_ws, flow_history):
    fake_ws.send_text.side_effect = RuntimeError("boom")

    with pytest.raises(ExceptionGroup) as exc:
        await history_websocket(fake_ws, flow_history)

    assert exc.group_contains(RuntimeError)
    assert not flow_history._subscribers  # finally still cleaned up
