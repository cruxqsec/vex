import asyncio
import logging
import time

from mitmproxy import http
from mitmproxy.log import ALERT
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.errors import DatabaseError
from vex_cli.errors import ValidationError as VexValidationError
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

MITMPROXY_LOG_LEVELS = {
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "info": logging.INFO,
    "alert": ALERT,
    "debug": logging.DEBUG,
}


class MitmproxyLogForwarder:
    """Addon that forwards mitmproxy's internal log entries into our logging.

    Mitmproxy's legacy log handler re-emits stdlib records it sees as LogEntry
    events again, so our own records must never come back through here — they
    are filtered out at the source instead.
    """

    def __init__(self):
        self.logger = logging.getLogger("vex.mitmproxy")
        self.logger.propagate = True  # reach root's file handler
        self.logger.addHandler(logging.NullHandler())  # no double logging if root reconfigured
        _suppress_echo_into_mitmproxy(self.logger.name)


def _suppress_echo_into_mitmproxy(logger_name: str) -> None:
    """Mitmproxy's LegacyLogEvents root handler turns every stdlib record into
    an AddLogHook event again; records from our forwarder must not re-enter it
    or logging loops forever."""
    from mitmproxy.log import LegacyLogEvents

    for handler in logging.getLogger().handlers:
        if isinstance(handler, LegacyLogEvents):
            for f in handler.filters:
                if getattr(f, "__name__", None) == "_vex_skip_echo":
                    return
            handler.addFilter(_make_echo_filter(logger_name))
            return


def _make_echo_filter(logger_name: str):
    def _vex_skip_echo(record: logging.LogRecord) -> bool:
        return record.name != logger_name

    return _vex_skip_echo

    async def add_log(self, entry):
        level = MITMPROXY_LOG_LEVELS.get(entry.level, logging.INFO)
        self.logger.log(level, entry.msg)


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

            raw_req = await asyncio.to_thread(flow_to_raw_request, flow)
            summary = RequestSummary.from_flow(flow, raw_req)
            raw = RawRequest.from_flow(flow, raw_req)

            await self._save_and_broadcast(flow, summary, raw)

        except (DatabaseError, VexValidationError) as e:
            await self._report_capture_error(flow.request.pretty_host, e, kind="database")
        except (ValueError, TypeError) as e:
            await self._report_capture_error(flow.request.pretty_host, e, kind="parse")
        except Exception as e:
            logger.exception("Unexpected error in request processing")
            await self._report_capture_error(flow.request.pretty_host, e, kind="unknown")

    async def response(self, flow: http.HTTPFlow):
        """Called when response is received"""
        try:
            if not self.app_state.is_project_active:
                return

            if not flow.metadata.get("in_scope", False):
                return

            raw_res = await asyncio.to_thread(flow_to_raw_response, flow)
            summary = ResponseSummary.from_flow(flow, raw_res)
            raw = RawResponse.from_flow(flow, raw_res)

            await self._save_and_broadcast(flow, summary, raw)

        except (DatabaseError, VexValidationError) as e:
            await self._report_capture_error(flow.request.pretty_host, e, kind="database")
        except (ValueError, TypeError) as e:
            await self._report_capture_error(flow.request.pretty_host, e, kind="parse")
        except Exception as e:
            logger.exception("Unexpected error in response processing")
            await self._report_capture_error(flow.request.pretty_host, e, kind="unknown")

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

    async def _save_and_broadcast(
        self,
        flow: http.HTTPFlow,
        summary: RequestSummary | ResponseSummary,
        raw: RawRequest | RawResponse,
    ):
        databases = self.db_manager.active_databases()
        if databases is None:
            return
        summaries_db, raw_db = databases

        # Summaries are the source of truth, so they commit first; 
        # if the raw side then fails, roll the summary back 
        created_orm: RequestSummaryORM | ResponseSummaryORM = await summaries_db.create(summary.to_orm())
        try:
            await raw_db.create(raw.to_orm())
        except Exception as raw_exp:
            logger.exception(
                "Raw write failed for flow %s; rolling back its summary",
                summary.flow_id,
            )
            await self._report_capture_error(flow.request.pretty_host,raw_exp, kind="database")
            try:
                await summaries_db.delete_by_flow_id(type(created_orm), summary.flow_id)
            except Exception as delete_exp:
                logger.error(
                    "Rollback failed for flow %s; orphaned summary left behind",
                    summary.flow_id,
                )
                await self._report_capture_error(flow.request.pretty_host, delete_exp, kind="database")
            return

        summary.id = created_orm.id
        await self.flow_history.broadcast(summary)

    async def _report_capture_error(
            self,
            host: str | None,
            exc: Exception,
            *, # so kind is a keyword argument
            kind: CaptureErrorKind,
        ) -> None:
            """Log and push a capture failure to subscribers. Never raises."""
            log = logger.error
            log("Capture failure (%s): %s", kind, exc, exc_info=exc)

            event = CaptureErrorEvent(
                kind=kind,
                message=f"{type(exc).__name__}: {exc}",
                host=host if host else None,
                timestamp=time.time(),
            )

            try:
                await self.flow_history.broadcast(event)
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
    mitmproxy_log_forwarder = MitmproxyLogForwarder()
    master.addons.add(addon, mitmproxy_log_forwarder)

    try:
        await master.run()
    except asyncio.CancelledError:
        logger.info("Proxy server shutdown requested.")
