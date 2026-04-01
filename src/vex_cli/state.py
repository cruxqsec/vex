import asyncio

from vex_cli.models.pydantic import Project, VexServerInfo
from vex_cli.database import DatabaseManager
from vex_cli.flow_history import FlowHistory
from vex_cli.locations import vex_log_directory


import logging
logger = logging.getLogger(__name__)

class VexState:
    """
    Vex server state object.
    """

    def __init__(self, server_info: VexServerInfo):
        self.server_info = server_info

        self._db_initialized: bool = False
        self._active_project: Project | None = None
        self._lock = asyncio.Lock()
        self._flow_history: FlowHistory = FlowHistory()
        
        self._configure_logging()

    async def initialize_db(self) -> None:
        """Initialize all the components of the app"""
        self._db_manager: DatabaseManager = DatabaseManager()
        await self._db_manager.initialize()

        self._db_initialized = True
    
    @property
    def is_project_active(self) -> bool:
        return bool(self._active_project)
    
    @property
    def is_db_initialized(self) -> bool:
        return bool(self._db_initialized)

    def get_server_info(self) -> VexServerInfo:
        return self.server_info

    def get_active_project(self) -> Project | None:
        return self._active_project
    
    async def set_active_project(self, project: Project | None):
        async with self._lock:
            self._active_project = project

    def get_flow_history(self) -> FlowHistory:
        return self._flow_history
    
    def get_db_manager(self) -> DatabaseManager:
        return self._db_manager
    
    def _configure_logging(self):
        """Configure logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(vex_log_directory()/'vex-cli.log')]
        )       
       
    async def shutdown(self):
        if self._db_manager:
            await self._db_manager.close()
        

        
        
