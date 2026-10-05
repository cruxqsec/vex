import asyncio
import logging

from vex_cli.models.pydantic import FlowEvent

logger = logging.getLogger(__name__)


class FlowHistory:
    """
    Maintains and broadcasts captured HTTP flows.
    Clients subscribe through the Websocket API.
    """

    def __init__(self):
        self._subscribers: set[asyncio.Queue[FlowEvent]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue[FlowEvent] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, dead_queue: asyncio.Queue[FlowEvent]):
        async with self._lock:
            self._subscribers.discard(dead_queue)

    async def broadcast(self, event: FlowEvent):
        """Broadcast flow summary to all subscribers"""
        async with self._lock:
            dead_clients = []

            for queue in self._subscribers:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    dead_clients.append(queue)

            if dead_clients:
                for q in dead_clients:
                    self._subscribers.discard(q)
