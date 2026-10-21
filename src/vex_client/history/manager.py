import asyncio
import json
import logging
from collections.abc import Callable
from uuid import UUID

import websockets
from pydantic import ValidationError
from websockets.exceptions import ConnectionClosed

from vex_cli.models.pydantic import (
    CaptureErrorEvent,
    FlowEvent,
    FlowSummary,
    RequestSummary,
    ResponseSummary,
    VexServerInfo,
)
from vex_client.api.client import ApiClient

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(
        self,
        on_summary_received: Callable[[RequestSummary | ResponseSummary], None],
        on_loading_changed: Callable[[bool], None],
    ) -> None:
        self.summaries: dict[UUID, FlowSummary] = {}
        self.is_loading = False
        self._on_summary_received = on_summary_received
        self._on_loading_changed = on_loading_changed
        self._accept_messages = False
        self._load_task: asyncio.Task[None] | None = None

    def stop(self) -> None:
        self._accept_messages = False
        self._cancel_load()

    def start_project(self) -> None:
        self._cancel_load()
        self.clear_summaries()
        self._accept_messages = True

    def clear_project(self) -> None:
        self._cancel_load()
        self.clear_summaries()
        self._accept_messages = False

    def remove_summary(self, flow_id: UUID) -> None:
        self.summaries.pop(flow_id, None)

    def clear_summaries(self) -> None:
        self.summaries.clear()

    def _cancel_load(self) -> None:
        if self._load_task is not None:
            self._load_task.cancel()
            self._load_task = None
        self._set_loading(False)

    def _set_loading(self, loading: bool) -> None:
        if self.is_loading != loading:
            self.is_loading = loading
            self._on_loading_changed(loading)

    async def receive_summaries(self, server_info: VexServerInfo) -> None:
        """Receive live history until the owning worker is cancelled."""
        uri = f"ws://{server_info.server_address}:{server_info.api_port}/ws/history"
        connection_failed = False
        while True:
            try:
                logger.debug("Connecting history WebSocket at %s", uri)
                async with websockets.connect(uri) as websocket:
                    connection_failed = False
                    async for raw_message in websocket:
                        if self._accept_messages:
                            self._handle_message(raw_message)
            except asyncio.CancelledError:
                raise
            except (OSError, ConnectionClosed) as exc:
                if connection_failed:
                    logger.debug("History WebSocket retry failed at %s: %s", uri, exc)
                else:
                    logger.warning("History WebSocket disconnected at %s: %s", uri, exc)
                    connection_failed = True
            except Exception:
                logger.exception("History WebSocket failed at %s", uri)
            await asyncio.sleep(5)

    def _parse_message(self, raw_data: str) -> FlowEvent:
        data = json.loads(raw_data)
        if data.get("type") == "capture_error":
            return CaptureErrorEvent.model_validate(data)
        try:
            return RequestSummary.model_validate(data)
        except ValidationError:
            return ResponseSummary.model_validate(data)

    def _handle_message(self, raw_message: websockets.Data) -> None:
        try:
            message = self._parse_message(str(raw_message))
            if isinstance(message, CaptureErrorEvent):
                logger.error("History capture error (%s): %s", message.kind, message.message)
                return
            self._add_summary(message)
            self._on_summary_received(message)
        except (ValidationError, json.JSONDecodeError):
            logger.exception("Invalid message on /ws/history")
        except Exception:
            logger.exception("Failed to process message on /ws/history")

    def _add_summary(self, summary: RequestSummary | ResponseSummary | FlowSummary) -> None:
        if isinstance(summary, RequestSummary):
            self.summaries[summary.flow_id] = FlowSummary(**summary.model_dump())
        elif isinstance(summary, ResponseSummary):
            flow = self.summaries.get(summary.flow_id)
            if flow is not None:
                flow.status_code = summary.status_code
                flow.response_size = summary.response_size
                flow.mime = summary.mime
                flow.http_title = summary.http_title
                flow.cookie = summary.cookie
                flow.duration_ms = summary.duration_ms
                flow.timestamp = summary.timestamp
        else:
            self.summaries[summary.flow_id] = summary

    async def load_summaries(self, api: ApiClient) -> None:
        if not self._accept_messages:
            return
        self._cancel_load()
        task = asyncio.current_task()
        self._load_task = task
        self._set_loading(True)
        try:
            skip = 0
            while True:
                batch = await api.summaries.get_all_summaries(skip, 50)
                if self._load_task is not task:
                    return
                for summary in batch:
                    self._add_summary(summary)
                if len(batch) < 50:
                    break
                skip += 50
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not load history summaries")
        finally:
            # A cancelled load may finish cleaning up after its replacement starts.
            if self._load_task is task:
                self._load_task = None
                self._set_loading(False)
