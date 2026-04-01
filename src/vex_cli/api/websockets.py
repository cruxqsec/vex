import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from vex_cli.dependencies import get_flow_history
from vex_cli.flow_history import FlowHistory
from vex_cli.models.pydantic import RequestSummary, ResponseSummary

logger = logging.getLogger(__name__)

websocket_router = APIRouter()


@websocket_router.websocket("/history")
async def history_websocket(
    websocket: WebSocket, flow_history: FlowHistory = Depends(get_flow_history)
):
    await websocket.accept()

    client_queue = await flow_history.subscribe()
    try:
        while True:
            summary: RequestSummary | ResponseSummary = await client_queue.get()
            await websocket.send_text(summary.model_dump_json())
    except WebSocketDisconnect as e:
        logger.info("Flow history client disconnected")
    except Exception as e:
        logger.error(f"Error in websocket: {e}")
    finally:
        await flow_history.unsubscribe(client_queue)


@websocket_router.websocket("/intercept")
async def intercept_websocket(
    websocket: WebSocket, flow_history: FlowHistory = Depends(get_flow_history)
):
    await websocket.accept()
    pass
