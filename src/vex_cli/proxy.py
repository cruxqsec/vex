import asyncio
import logging
import time
from uuid import UUID

from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
from pydantic import ValidationError

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.errors import ConflictError, DatabaseError
from vex_cli.flow_helper import flow_to_raw_request, flow_to_raw_response
from vex_cli.flow_history import FlowHistory
from vex_cli.flow_scope import FlowScope
from vex_cli.models.orm import RequestSummaryORM, ResponseSummaryORM
from vex_cli.models.pydantic import (
    CaptureErrorEvent,
    CaptureErrorKind,
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
)
from vex_cli.state import VexState

logger = logging.getLogger(__name__)
logging.getLogger("mitmproxy").setLevel(
    logging.DEBUG
)  # get mitmproxy logs in vex-cli.log


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

            raw_req_bytes: bytes = await asyncio.to_thread(flow_to_raw_request, flow)
            summary: RequestSummary = RequestSummary.from_flow(flow, raw_req_bytes)
            raw: RawRequest = RawRequest(id=UUID(flow.id), data=raw_req_bytes)

            await self.save_and_broadcast_summary(flow, summary, raw)

        except (DatabaseError, ConflictError) as e:
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="database")
        except (ValidationError, UnicodeError) as e:
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="parse")
        except Exception as e:
            logger.exception("Unexpected error in request processing")
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="unknown")

    async def response(self, flow: http.HTTPFlow):
        """Called when response is received"""
        try:
            if not self.app_state.is_project_active:
                return

            if not flow.metadata.get("in_scope", False):
                return

            raw_res_bytes: bytes | None = await asyncio.to_thread(
                flow_to_raw_response, flow
            )
            summary: ResponseSummary = ResponseSummary.from_flow(flow, raw_res_bytes)
            raw: RawResponse = RawResponse(id=UUID(flow.id), data=raw_res_bytes)

            await self.save_and_broadcast_summary(flow, summary, raw)

        except (DatabaseError, ConflictError) as e:
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="database")
        except (ValidationError, UnicodeError) as e:
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="parse")
        except Exception as e:
            self.log_and_broadcast_error(flow.request.pretty_host, e, kind="unknown")

    async def error(self, flow: http.HTTPFlow):
        """Called when request errors and no response is captured"""
        try:
            if not self.app_state.is_project_active:
                return

            if not flow.metadata.get("in_scope", False):
                return

            if flow.error is None:
                return

            logger.error(
                "Connection error for flow %s (%s): %s",
                flow.id,
                flow.request.pretty_host,
                flow.error.msg,
            )
        except Exception:
            logger.exception("Unexpected error in error handling")

    async def save_and_broadcast_summary(
        self,
        flow: http.HTTPFlow,
        summary: RequestSummary | ResponseSummary,
        raw: RawRequest | RawResponse,
    ):
        databases = self.db_manager.active_databases()
        if databases is None:
            return
        summaries_db, raw_db = databases

        created_orm = await summaries_db.create(summary.to_orm())

        try:
            await raw_db.create(raw.to_orm())
        except Exception:
            await summaries_db.delete_by_flow_id(type(created_orm), summary.flow_id)
            raise

        summary.id = created_orm.id
        self.flow_history.broadcast(summary)

    def log_and_broadcast_error(
        self,
        host: str | None,
        exc: Exception,
        *,  # so kind is a keyword argument
        kind: CaptureErrorKind,
    ) -> None:
        """Log and broadcast a capture failure to subscribers."""
        logger.error("Capture failure (%s): %s", kind, exc, exc_info=exc)
        event = CaptureErrorEvent(
            kind=kind,
            message=f"{type(exc).__name__}: {exc}",
            host=host if host else None,
            timestamp=time.time(),
        )

        try:
            self.flow_history.broadcast(event)
        except Exception:
            logger.exception("Failed to broadcast capture error")


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
