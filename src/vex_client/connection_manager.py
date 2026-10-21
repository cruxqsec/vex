import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from enum import Enum

import websockets

from vex_cli.models.pydantic import VexServerInfo
from vex_client.api.client import ApiClient


class ConnectionError(Exception):
    """Broad exception which signals an error happened at the start or during a connection."""


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages connection to the vex-cli instance.

    Handles the websocket monitor to /ws/ping.
    Creates the APIClient and closes it.
    Works for local and remote connections.
    """

    def __init__(self, on_state_changed: Callable[[ConnectionState], None]):
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        # callback so Textual can post messages when we update state
        # decoupled for easier testing instead of having post.message directly here
        self._on_state_changed = on_state_changed

        self._server_info: VexServerInfo | None = None
        self._api_client: ApiClient | None = None
        self._connection_task: asyncio.Task | None = None
        self._disconnect_requested = False

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def api_client(self) -> ApiClient | None:
        if self._state is ConnectionState.CONNECTED:
            return self._api_client
        return None

    @property
    def server_info(self) -> VexServerInfo | None:
        return self._server_info

    def _set_state(self, state: ConnectionState) -> None:
        if self._state is state:
            return

        self._state = state
        if self._on_state_changed is not None:
            self._on_state_changed(state)

    async def connect(self, server_info: VexServerInfo) -> None:
        """Start connecting in the background."""
        await self.disconnect()

        self._server_info = server_info.model_copy()
        self._disconnect_requested = False
        self._set_state(ConnectionState.CONNECTING)
        self._connection_task = asyncio.create_task(
            self._run_connection(self._server_info)
        )

    async def disconnect(self) -> None:
        """Stop connecting or monitoring and wait for cleanup."""
        task = self._connection_task
        self._disconnect_requested = True

        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

            self._connection_task = None

        # Also covers cancellation before the task started running.
        self._api_client = None
        self._server_info = None
        self._set_state(ConnectionState.DISCONNECTED)

    async def _run_connection(self, server_info: VexServerInfo) -> None:
        api: ApiClient | None = None

        try:
            api = ApiClient(
                server_info.server_address,
                server_info.api_port,
            )

            target = f"{server_info.server_address}:{server_info.api_port}"
            url = f"ws://{target}/ws/ping"
            logger.debug("Connecting to server at %s", target)

            async for ws in websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                open_timeout=10,
            ):
                try:
                    logger.debug("Checking server handshake at %s", target)
                    if not await api.health.health_check_handshake():
                        raise ConnectionError("Server handshake failed")

                    self._api_client = api
                    self._set_state(ConnectionState.CONNECTED)
                    logger.info("Server connected at %s", target)

                    await ws.wait_closed()
                    if not self._disconnect_requested:
                        logger.warning("Server connection to %s lost; reconnecting", target)
                        self._set_state(ConnectionState.RECONNECTING)

                finally:
                    await ws.close()

        except asyncio.CancelledError:
            raise

        except ConnectionError:
            logger.debug("Server handshake failed at %s; connection stopped", target)

        except Exception:
            logger.exception(
                "Unexpected error in connection to %s:%s",
                server_info.server_address,
                server_info.api_port,
            )

        finally:
            if api is not None:
                try:
                    await api.close()
                except Exception:
                    logger.exception(
                        "Failed to close API client for %s:%s",
                        server_info.server_address,
                        server_info.api_port,
                    )

            self._api_client = None
            self._server_info = None
            self._set_state(ConnectionState.DISCONNECTED)
