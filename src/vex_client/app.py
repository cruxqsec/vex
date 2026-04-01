import asyncio

from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive
from textual import log

from vex_cli.models import  Project

from vex_client.screens.proxy import VexProxyScreen
from vex_client.screens.scope import VexScopeScreen
from vex_client.screens.http_history import VexHTTPHistoryScreen
from vex_client.screens.intercept import VexInterceptScreen
from vex_client.screens.replay import VexReplayScreen
from vex_client.screens.project import VexProjectsScreen

from vex_client.settings import Settings
from vex_client.cli_controller import VexController

import logging
logger = logging.getLogger(__name__)

class VexApp(App[str]):
    
    CSS_PATH = "vex.tcss"
    
    BINDINGS = [
        Binding("ctrl+q", "switch('history-screen')", "Navigate to HTTP History screen",
                show=False, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+w", "switch('intercept-screen')", "Navigate to Intercept screen",
                show=False, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+e", "switch('replay-screen')", "Navigate to Replay screen",
                show=False, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+r", "switch('scope-screen')","Navigate to Scope screen",
                show=False, priority=True,  group=Binding.Group("Navigation")),
        Binding("ctrl+t", "switch('projects-screen')", "Navigate to Projects screen",
                show=False, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+c", "switch('proxy-screen')", "Quit", show=True, priority=True),
    ]
    
    SCREENS = {
       "proxy-screen": VexProxyScreen,
       "scope-screen": VexScopeScreen,
       "history-screen": VexHTTPHistoryScreen,
       "intercept-screen": VexInterceptScreen,
       "replay-screen": VexReplayScreen,
       "projects-screen": VexProjectsScreen,
    }

    is_project_active = reactive(False, always_update=True, init=False)
    
    async def on_mount(self) -> None:
        self.vex_active_project: Project | None = None
        self.vex_controller: VexController = VexController()
        self.is_project_active_event: asyncio.Event = asyncio.Event()
        
        self.settings: Settings = Settings()
        self.theme = self.settings.theme

        # preload all screens so we don't have widget
        # lookup problems and we can add data to tables
        for screen_name in self.SCREENS.keys():
            await self.preload_screen(screen_name)

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")
    
    def set_active_project(self, active_project: Project | None) -> None:
        self.vex_active_project = active_project
        if self.vex_active_project is None:
            self.is_project_active = False
            self.is_project_active_event.clear() # set flag to off -> workers wait
        else:
            self.is_project_active = True
            self.is_project_active_event.set() # set flag to on -> workers can work
    
    def get_active_project(self) -> Project | None:
        return self.vex_active_project
    
    def get_api_info(self) -> tuple[str, int] | tuple[None, None]:
        """
        Return the API info so we can call vex-cli API
        """
        server_info = self.vex_controller.get_server_info()

        if server_info is None:
            return None, None

        return server_info.server_address, server_info.api_port
    
    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)
    
    def get_screen_name(self) -> str:
        """
        Get screen name for the screen we use to install it and is defined in the SCREENS
        """
        current_screen = self.app.screen
        
        for name, screen in self.app.SCREENS.items():
            if isinstance(current_screen, screen): # type: ignore
                return name
        
        return ""
    
    async def preload_screen(self, screen_name: str) -> None:
        """
        Preload all the screens by pushing them waiting a bit and then popping them.
        We do this so we have all the main widgets of each screen mounted.
        """
        await self.push_screen(screen_name)
        await asyncio.sleep(0.5)
        await self.pop_screen()
    
    def check_action(
        self, action: str, parameters: tuple[object, ...]
    ) -> bool | None:  
        """Check if we can switch screen."""
        if (
            action == "switch" 
            and (self.screen.is_modal or isinstance(self.screen, VexProxyScreen))
        ):
            return False
        elif (
            action == "switch" 
            and len(parameters) == 1
            and parameters[0] not in {"proxy-screen", "projects-screen"}
            and not self.is_project_active 
        ):
            return False
        return True
