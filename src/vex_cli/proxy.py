import asyncio
import logging

from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.flow_history import FlowHistory
from vex_cli.models.pydantic import (
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
)
from vex_cli.state import VexState

logger = logging.getLogger(__name__)


class VexCapture:
    """
    mitmproxy addon that captures HTTP traffic,
    saves it to a database and sends the summary to subscribers.
    Routes flows to appropriate handlers (history, intercept, replay).
    """

    def __init__(self, app_state: VexState):
        self._app_state: VexState = app_state
        self._flow_history: FlowHistory = app_state.get_flow_history()
        self._db_manager: DatabaseManager = app_state.get_db_manager()

    async def request(self, flow: http.HTTPFlow):
        """Called when request is captured"""
        try:
            if not self._app_state.is_project_active:
                return

            flow.request.headers.pop(
                "If-Modified-Since", None
            )  # we don't want to receive cached response
            flow.request.headers.pop("If-None-Match", None)  # requests

            summary = RequestSummary.from_flow(flow)
            raw = RawRequest.from_flow(flow)

            await self._save_and_broadcast(summary, raw)

        except Exception as e:
            logger.error(f"Proxy error in request processing: {e}")

    async def response(self, flow: http.HTTPFlow):
        """Called when response is received"""
        try:
            if not self._app_state.is_project_active:
                return

            summary = ResponseSummary.from_flow(flow)
            raw = RawResponse.from_flow(flow)

            await self._save_and_broadcast(summary, raw)

        except Exception as e:
            logger.error(f"Proxy error in response processing: {e}")

    async def error(self, flow: http.HTTPFlow):
        """Called when request errors and no response is captured"""
        pass

    async def _save_and_broadcast(
        self,
        summary: RequestSummary | ResponseSummary,
        raw: RawRequest | RawResponse,
    ):
        await asyncio.gather(
            self._db_manager.summaries_db.create(summary.to_orm()),
            self._db_manager.raw_db.create(raw.to_orm()),
        )

        await self._flow_history.broadcast_summary(summary)


async def start_proxy(app_state: VexState):
    server_info = app_state.get_server_info()

    opts = Options(
        listen_host=server_info.server_address,
        listen_port=server_info.proxy_port,
        http2=True,
    )

    master = DumpMaster(opts, with_termlog=False, with_dumper=False)

    addon = VexCapture(app_state)
    master.addons.add(addon)

    try:
        await master.run()
    except asyncio.CancelledError:
        logger.info("Proxy server shutdown requested.")
    finally:
        try:
            master.shutdown()
        except Exception as e:
            logger.error(f"Error during proxy cleanup: {e}")
