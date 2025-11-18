from textual.app import App
from textual.binding import Binding
from textual.reactive import reactive
from textual import log

from subprocess import Popen, DEVNULL, TimeoutExpired
import socket

from vex_cli.models import ProxyInfo
from vex_client.screens.proxy import VexProxyScreen
from vex_client.screens.scope import VexScopeScreen
from vex_client.screens.http_history import VexHTTPHistoryScreen
from vex_client.screens.intercept import VexInterceptScreen
from vex_client.screens.replay import VexReplayScreen
from vex_client.screens.projects import VexProjectsScreen
from vex_client.settings import Settings

import logging
logger = logging.getLogger(__name__)

class VexApp(App[str]):
    
    CSS_PATH = "vex-main.tcss"
    
    BINDINGS = [
        Binding("ctrl+q", "switch('history-screen')", "Navigate to HTTP History screen",
                show=True, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+w", "switch('intercept-screen')", "Navigate to Intercept screen",
                show=True, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+e", "switch('replay-screen')", "Navigate to Replay screen",
                show=True, priority=True, group=Binding.Group("Navigation")),
        Binding("ctrl+r", "switch('scope-screen')","Navigate to Scope screen",
                show=True, priority=True,  group=Binding.Group("Navigation")),
        Binding("ctrl+t", "switch('projects-screen')", "Navigate to Projects screen",
                show=True, priority=True, group=Binding.Group("Navigation")),
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
    
    proxy_running = reactive(False)
    proxy_process: Popen | None = None
    
    def get_proxy_info(self) -> ProxyInfo | None:
        return self.proxy_info
    
    def set_proxy_info(self, proxy_info: ProxyInfo):
        self.proxy_info = proxy_info
    
    def on_mount(self) -> None:
        self.settings: Settings = Settings()
        self.proxy_info: ProxyInfo | None = None
        self.theme = self.settings.theme

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")
        
    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)
    
    def check_action(
        self, action: str, parameters: tuple[object, ...]
    ) -> bool | None:  
        """Check if the switch screen may run"""
        if action == "switch" and isinstance(self.screen, VexProxyScreen):
            return False
        return True
    

    def can_bind_ports(self, proxy_info: ProxyInfo) -> bool:
        """Check if we can bind to both ports"""
        address = proxy_info.server_address
        to_check = [(address, proxy_info.proxy_port),
                    (address, proxy_info.api_port)]
        for address, port in to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((address, port))
            except OSError:
                self.notify(title="Port already in use!",
                            message=f"Port {port} on {address} is already in use!",
                            severity="error")
                return False
        return True
        
    
    def watch_proxy_running(self, running: bool):
        if running:
            self.start_proxy()
        else:
            self.stop_proxy()
        
    def start_proxy(self):
        if self.proxy_info is not None:
            if not self.can_bind_ports(self.proxy_info):
                return

            try:
                self.proxy_process = Popen(
                    ["vex-cli", "start", "--address", self.proxy_info.server_address,
                     "--proxy-port", str(self.proxy_info.proxy_port),
                     "--api-port", str(self.proxy_info.api_port)],
                    stdout=DEVNULL,
                    stderr=DEVNULL,
                )
                message = f"""
                API server:{self.proxy_info.server_address}:{self.proxy_info.api_port}
                Proxy server: {self.proxy_info.server_address}:{self.proxy_info.proxy_port}
                """
                self.notify(title="Vex proxy started", message=message)
            except FileNotFoundError:
                logger.error("vex-cli could not be found in $PATH.")
            except PermissionError:
                logger.error("No permission to execute vex-cli.")
            except Exception as e:
                logger.error(f"Unexpected exception occurred trying to run vex-cli {e}")
        

    def stop_proxy(self):
        if self.proxy_process is not None:
            try:
                self.proxy_process.terminate()
                self.proxy_process.wait(timeout=3.0)
            except TimeoutExpired:
                logger.warning("Could not terminate vex-cli gracefully. Attempting to kill.")
                self.proxy_process.kill()
                self.proxy_process.wait(timeout=1.0) 
            finally:
                self.notify(title="Proxy shutdown!", message="Vex has shutdown.")
                
    def on_onmount(self):
        self.stop_proxy()

