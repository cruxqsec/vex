from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn
    from mitmproxy.tools.dump import DumpMaster

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.flow_history import FlowHistory
from vex_cli.flow_scope import FlowScope
from vex_cli.models.pydantic import Project, VexServerInfo
from vex_cli.errors import AppException

logger = logging.getLogger(__name__)


class VexState:
    """
    Vex server state object.
    """

    def __init__(self, server_info: VexServerInfo):
        self.server_info = server_info
        # Single-event-loop server: attribute assignment is atomic within the
        # loop; consistency that must span an await lives in DatabaseManager.
        self._active_project: Project | None = None
        self._db_manager: DatabaseManager | None = None

        self._flow_history: FlowHistory = FlowHistory()
        self._flow_scope: FlowScope = FlowScope()

        # Server references for coordinated shutdown
        self.uvicorn_server: uvicorn.Server | None = None
        self.mitmproxy_master: DumpMaster | None = None

    async def initialize_db_manager(self) -> None:
        self._db_manager = DatabaseManager()
        await self._db_manager.initialize()

    @property
    def is_project_active(self) -> bool:
        return (
            self._db_manager is not None
            and self._db_manager.is_project_active
            and bool(self._active_project)
        )

    def get_server_info(self) -> VexServerInfo:
        return self.server_info

    def get_active_project(self) -> Project | None:
        return self._active_project

    async def set_active_project(self, project: Project | None):
        self._active_project = project

    def get_flow_history(self) -> FlowHistory:
        return self._flow_history

    def get_flow_scope(self) -> FlowScope:
        return self._flow_scope

    def get_db_manager(self) -> DatabaseManager:
        if self._db_manager is None:
            raise AppException("Database manager not initialized", 500)
        return self._db_manager

    async def shutdown(self):
        if self._db_manager is not None:
            await self._db_manager.close()
