import psutil

from textual.app import App
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual import log

from vex_cli.models import VexServerInfo, Project
from vex_cli.bind import try_bind_ports

from vex_client.screens.proxy import VexProxyScreen
from vex_client.screens.scope import VexScopeScreen
from vex_client.screens.http_history import VexHTTPHistoryScreen
from vex_client.screens.intercept import VexInterceptScreen
from vex_client.screens.replay import VexReplayScreen
from vex_client.screens.project import VexProjectsScreen
from vex_client.settings import Settings
from vex_client.process import (
    start_detached_process,
    terminate_process,
    kill_process,
    INACTIVE_PROCESS
)

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
    
    def on_mount(self) -> None:
        self.server_info: VexServerInfo | None = None
        self.vex_cli_pid: int = INACTIVE_PROCESS
        self.vex_cli_running: bool = False
        self.vex_active_project: Project | None = None
        
        self.settings: Settings = Settings()
        self.theme = self.settings.theme

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")
    
    def set_active_project(self, active_project: Project | None) -> None:
        self.vex_active_project = active_project
        if self.vex_active_project is not None:
            self.is_project_active = True
        else:
            self.is_project_active = False
    
    def get_active_project(self) -> Project | None:
        return self.vex_active_project
    
    @property
    def is_vex_cli_running(self) -> bool:
        return self.vex_cli_running
    
    def set_vex_running(self, running: bool) -> None:
        self.vex_cli_running = running
    
    def set_vex_pid(self, pid: int) -> None:
        self.vex_cli_pid = pid
    
    def get_server_info(self) -> VexServerInfo | None:
        return self.server_info
    
    def set_server_info(self, server_info: VexServerInfo | None):
        self.server_info = server_info
        
    def get_api_info(self) -> tuple[str, int] | tuple[()]:
        if self.server_info is None:
            return ()

        return (self.server_info.server_address, self.server_info.api_port)
       
    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)
    
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

    def start_vex_cli(self, server_info: VexServerInfo) -> bool:
        
        can_bind, port = try_bind_ports(server_info)         
        address = server_info.server_address

        if not can_bind: 
            self.notify(
                title="ERROR",
                message=f"Port {port} on {address} is already in use!",
                severity="error"
            )
            return False
        
        cmd = ["vex-cli", "start", "--address", server_info.server_address,
               "--proxy-port", str(server_info.proxy_port),
               "--api-port", str(server_info.api_port)
        ]

        pid = start_detached_process(cmd) 
        
        if pid == INACTIVE_PROCESS:
            self.notify(title="FAILED TO START INSTANCE", message="Failed to start instance. Check logs.")
            self.set_vex_pid(INACTIVE_PROCESS)
            return False
        
        message = (
            f"API server:{server_info.server_address}:{server_info.api_port}\n"
            f"Proxy server:{server_info.server_address}:{server_info.proxy_port}"
        )
        self.notify(title="INSTANCE STARTED", message=message, timeout=5.0)
        self.set_vex_running(True)
        self.set_server_info(server_info)
        self.set_vex_pid(pid)
        
        return True

    def stop_vex_cli(self):
        if self.vex_cli_pid == INACTIVE_PROCESS:
            return
        
        terminated = terminate_process(self.vex_cli_pid)
        
        if terminated and not psutil.pid_exists(self.vex_cli_pid):
            self.notify(title="INSTANCE SHUTDOWN", message="Proxy instance has shutdown")
            return
        
        # if graceful termination doesn't work then we kill it
        kill_process(self.vex_cli_pid)
        self.notify(title="INSTANCE SHUTDOWN", message="Proxy instance has shutdown")
    
        self.set_vex_pid(INACTIVE_PROCESS)
        self.set_server_info(None)