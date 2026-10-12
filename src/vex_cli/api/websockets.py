import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from vex_cli.dependencies import get_flow_history
from vex_cli.errors import VexClientDisconnectEvent
from vex_cli.flow_history import FlowEvent, FlowHistory

logger = logging.getLogger(__name__)

websocket_router = APIRouter(tags=["Websockets"])

"""
    /ping       -> connection liveness probe that the client connects
                   to it to establish the Websocket ping/pong frames

    /history    -> client subscribes to this endpoint to recieve summaries
    /intercept  -> not implemented yet
    /replay     -> not implemented yet
"""


@websocket_router.websocket("/ping")
async def ping(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.receive()
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass


async def wait_for_client_disconnect_event(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            raise VexClientDisconnectEvent


async def send_events_to_client(
    websocket: WebSocket, client_queue: asyncio.Queue
) -> None:
    while True:
        event: FlowEvent = await client_queue.get()
        await websocket.send_text(event.model_dump_json())


@websocket_router.websocket("/history")
async def history_websocket(
    websocket: WebSocket,
    flow_history: Annotated[FlowHistory, Depends(get_flow_history)],
):
    client_queue: asyncio.Queue[FlowEvent] = flow_history.subscribe()

    try:
        await websocket.accept()
        async with asyncio.TaskGroup() as group:
            group.create_task(send_events_to_client(websocket, client_queue))
            group.create_task(wait_for_client_disconnect_event(websocket))

    except* (VexClientDisconnectEvent, WebSocketDisconnect):
        logger.info("Flow history client disconnected")
    finally:
        flow_history.unsubscribe(client_queue)


@websocket_router.websocket("/intercept")
async def intercept_websocket(
    websocket: WebSocket,
):
    await websocket.accept()

    # TODO: to implement
