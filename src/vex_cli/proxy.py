import asyncio
import logging

from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.flow_history import FlowHistory
from vex_cli.flow_scope import FlowScope
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
        self.app_state: VexState = app_state
        self.flow_history: FlowHistory = app_state.get_flow_history()
        self.flow_scope: FlowScope = app_state.get_flow_scope()
        self.db_manager: DatabaseManager = app_state.get_db_manager()

    async def request(self, flow: http.HTTPFlow):
        """Called when request is captured"""
        try:
            if not self.app_state.is_project_active:
                return

            flow.metadata["in_scope"] = self.flow_scope.apply_scope(
                flow.request.pretty_host
            )
            if not flow.metadata["in_scope"]:
                return

            flow.request.headers.pop(
                "If-Modified-Since", None
            )  # we don't want to receive cached response
            flow.request.headers.pop("If-None-Match", None)  # requests

            summary = RequestSummary.from_flow(flow)
            raw = RawRequest.from_flow(flow)

            await self._save_and_broadcast(summary, raw)

        except Exception:
            logger.exception("Proxy error in request processing")

    async def response(self, flow: http.HTTPFlow):
        """Called when response is received"""
        try:
            if not self.app_state.is_project_active:
                return

            if not flow.metadata.get("in_scope", False):
                return

            summary = ResponseSummary.from_flow(flow)
            raw = RawResponse.from_flow(flow)

            await self._save_and_broadcast(summary, raw)

        except Exception:
            logger.exception("Proxy error in response processing")

    async def error(self, flow: http.HTTPFlow):
        """Called when request errors and no response is captured"""
        pass

    async def _save_and_broadcast(
        self,
        summary: RequestSummary | ResponseSummary,
        raw: RawRequest | RawResponse,
    ):
        created_orm, _ = await asyncio.gather(
            self.db_manager.summaries_db.create(summary.to_orm()),
            self.db_manager.raw_db.create(raw.to_orm()),
        )
        summary.id = created_orm.id
        await self.flow_history.broadcast_summary(summary)


async def start_proxy(app_state: VexState):
    server_info = app_state.get_server_info()

    opts = Options(
        listen_host=server_info.server_address,
        listen_port=server_info.proxy_port,
        http2=True,
    )

    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    app_state.mitmproxy_master = master

    addon = VexCapture(app_state)
    master.addons.add(addon)

    try:
        await master.run()
    except asyncio.CancelledError:
        logger.info("Proxy server shutdown requested.")
