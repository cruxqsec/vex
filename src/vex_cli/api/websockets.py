import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from vex_cli.dependencies import get_flow_history
from vex_cli.flow_history import FlowEvent, FlowHistory

logger = logging.getLogger(__name__)

websocket_router = APIRouter(tags=["Websockets"])


@websocket_router.websocket("/ping")
async def ping(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.receive()
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass


@websocket_router.websocket("/history")
async def history_websocket(
    websocket: WebSocket,
    flow_history: Annotated[FlowHistory, Depends(get_flow_history)],
):
    client_queue: asyncio.Queue[FlowEvent] = await flow_history.subscribe()

    try:
        await websocket.accept()
        while True:
            event: FlowEvent = await client_queue.get()
            await websocket.send_text(event.model_dump_json())
    except WebSocketDisconnect:
        logger.info("Flow history client disconnected")
    except (RuntimeError, OSError):
        logger.info("Flow history error raised in websocket")
    finally:
        await flow_history.unsubscribe(client_queue)


@websocket_router.websocket("/intercept")
async def intercept_websocket(
    websocket: WebSocket,
):
    await websocket.accept()

    # TODO: to implement
