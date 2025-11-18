import asyncio

from mitmproxy import http
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from vex_cli.models import RequestSummary, ResponseSummary, RawRequest, RawResponse
from vex_cli.errors import ProxyException

from vex_cli.state import VexState
from vex_cli.flow_history import FlowHistory
from vex_cli.database import DatabaseManager, SummariesDatabase, RawDatabase

import logging
logger = logging.getLogger(__name__)

class VexCapture:
    """
    mitmproxy addon that captures HTTP traffic.
    Routes flows to appropriate handlers (history, intercept, replay).
    """

    def __init__(self, app_state: VexState):
        self._app_state: VexState = app_state
        self._flow_history: FlowHistory = app_state.get_flow_history()
        self._db_manager: DatabaseManager =  app_state.get_db_manager()
        
    @property
    def summaries_db(self) -> SummariesDatabase | None:
        return self._db_manager.get_summaries_db()
    
    @property
    def raw_db(self) -> RawDatabase | None:
        return self._db_manager.get_raw_db()

    async def request(self, flow: http.HTTPFlow):
        """Called when request is captured"""
        try:
            if not self._app_state.is_db_initialized or not self._app_state.is_project_active:
                return

            flow.request.headers.pop("If-Modified-Since", None) # we don't want to receive cached response
            flow.request.headers.pop("If-None-Match", None)     # requests
            
            summary = RequestSummary.from_flow(flow)
            raw = RawRequest.from_flow(flow)
            
            if self.summaries_db is not None and self.raw_db is not None:
                await self.summaries_db.create(summary)
                await self.raw_db.create(raw)
              
            await self._flow_history.broadcast_summary(summary)

        except Exception as e:
            logger.error(f"Proxy error in request processing: {e}")
            raise ProxyException(f"Proxy error in request processing: {e}")

    async def response(self, flow: http.HTTPFlow):
        """Called when response is received"""
        try:
            if not self._app_state.is_db_initialized or not self._app_state.is_project_active:
                return

            summary = ResponseSummary.from_flow(flow)
            raw = RawResponse.from_flow(flow)
            

            if self.summaries_db is not None and self.raw_db is not None:
                await self.summaries_db.create(summary)
                await self.raw_db.create(raw)

            await self._flow_history.broadcast_summary(summary)

        except Exception as e:
            logger.error(f"Proxy error in response processing: {e}")
            raise ProxyException(f"Proxy error in response processing: {e}")

    async def error(self, flow: http.HTTPFlow):
        """Called when request errors and no response is captured"""
        pass
    

async def start_proxy(app_state:VexState):
    proxy_info = app_state.get_proxy_info()

    opts = Options(
        listen_host=proxy_info.server_address,
        listen_port=proxy_info.proxy_port,
        http2=True
    )
    
    master = DumpMaster(opts, with_termlog=False, with_dumper=False)
    
    addon = VexCapture(app_state)
    master.addons.add(addon)

    try:
        await master.run()
    except asyncio.CancelledError as e:
        logger.info(f"Proxy was shutdown by user.")
        if master is not None:
            master.shutdown() # type: ignore
        raise ProxyException(f"Proxy was shutdown.") # reraise for asyncio.gather
    except Exception as e:
        logger.error(f"Error in proxy_master: {e}")
        if master is not None:
            master.shutdown() # type:ignore
        raise ProxyException(f"Proxy error: {e}") # reraise for asyncio.gather

