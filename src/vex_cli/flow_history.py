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

    @property
    def subscribers_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue[FlowEvent] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, dead_queue: asyncio.Queue[FlowEvent]):
        self._subscribers.discard(dead_queue)

    def broadcast(self, event: FlowEvent):
        """Broadcast flow summary to all subscribers."""
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()  # drop oldest
            queue.put_nowait(event)
