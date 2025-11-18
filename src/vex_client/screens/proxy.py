from typing import cast, TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Footer, ListView, ListItem, Label, Link, Rule
from textual.containers import Container, Horizontal, Center, Vertical
from textual.binding import Binding
from textual.reactive import reactive

if TYPE_CHECKING:
    from vex_client.app import VexApp

from vex_cli.models import ProxyInfo
from vex_client.version import VERSION
from vex_client.widgets.center_middle import CenterMiddle


import logging
logger = logging.getLogger(__name__)


banner = """
░██    ░██                       
░██    ░██                       
░██    ░██  ░███████  ░██    ░██ 
░██    ░██ ░██    ░██  ░██  ░██  
 ░██  ░██  ░█████████   ░█████   
  ░██░██   ░██         ░██  ░██  
   ░███     ░███████  ░██    ░██
        
"""
website = "https://vex.sh"
github_repo = "https://github.com/b/vex"

class VexLink(Link, can_focus=False):
    """Non focusable Link"""

class Status(Static):
    status = reactive("Shutdown")
    
    def running(self):
        self.status = "Running"

    def shutdown(self):
        self.status = "Shutdown"

    def render(self):
        return self.status

class VexProxyList(ListView, can_focus=True):
    """
    Vex proxy list for adding and selecting VexCLI proxy info.
    """
    BORDER_TITLE = "Vex proxies"

    BINDINGS = [
        Binding("enter", "select_cursor", "Start instance", show=True),
        Binding("k", "cursor_up", "🡅", show=True),
        Binding("j", "cursor_down", "🡇", show=True),
    ]
    
class VexProxyListItem(ListItem):
    """
    Proxy list item with a status_dot.
    """
    
    DEFAULT_CSS = """
        VexProxyListItem Horizontal {
            width: 1fr;
            height: auto;
            padding: 1;
        }

        .status-dot {
            width: 1fr;
            content-align: left middle;
            color: red;
            padding: 0 2;
        }
    
        .instance-data {
            width: 6fr;
            content-align: center middle;
            margin: 0 2 0 2;
        }
        
        .status {
            width: auto;
            content-align: right middle;
            background: $background-lighten-2;
            margin: 0 2 0 4;
            padding: 0 2;
        }
        .active {
            color: green;
        }
        .inactive {
            color: red;
        }
    """
    
    def __init__(self, instance_name: str, proxy_info: ProxyInfo) -> None:
        super().__init__()
        self.instance_name = instance_name
        self.proxy_info = proxy_info
        
        self.proxy_info_str = f"""{proxy_info.server_address} proxy:{proxy_info.proxy_port} api:{proxy_info.api_port}"""
    
    @property
    def status_dot(self) -> Static:
        return self.query_one(".status-dot", Static)
    
    @property
    def status(self) -> Status:
        return self.query_one(".status", Status)
        
    def active(self):
        self.status.running()
        status_dot = self.status_dot
        status_dot.remove_class("inactive")
        status_dot.add_class("active")

    def inactive(self):
        self.status.shutdown()
        status_dot = self.status_dot
        status_dot.remove_class("active")
        status_dot.add_class("inactive")

    
    def compose(self) -> ComposeResult:
        with Horizontal(classes="item-row"):
            yield Static("⬤", classes="status-dot inactive")
            yield Label(f"{self.instance_name} {self.proxy_info_str}", classes="instance-data")
            yield Status(classes="status")

class VexProxyScreen(Screen):

    CSS_PATH="css/proxy.tcss"
    
    BINDINGS = [
        Binding("ctrl+a", "","Add instance"),
        Binding("ctrl+c", "app.quit", "Quit", show=True),
    ]
    
    @property
    def app(self) -> VexApp:
        """For the static type."""
        return self.app
       
    @property
    def proxy_list(self) -> VexProxyList:
        return self.query_one("#proxy-list", VexProxyList)
    
    def compose(self) -> ComposeResult:
        with Vertical(id="banner-container"):
            yield Static(banner, id="banner")
            with Container(id="info"):
                yield Center(VexLink("vex.sh", url=website, id="website-link"))
                yield Rule("vertical")
                yield Center(Static(f"Version: {VERSION}", id="version"))
        with Container(id="main-container"):
            yield VexProxyList(id="proxy-list")
        yield Footer()
        
    def on_mount(self):
        # append the default proxy
        self.proxy_list.append(VexProxyListItem("Local instance", 
                                                ProxyInfo("127.0.0.1", 8080, 9000)))
        self.proxy_list.index = 0
        
    def action_add_instance(self):
        # start a new screen
        # get returned data from screen
        # append to proxy_list
        pass
        
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected_proxy: VexProxyListItem = cast(VexProxyListItem, event.item)

        if not self.app.proxy_running: 
            selected_proxy.active()
            self.app.set_proxy_info(selected_proxy.proxy_info) 
            self.app.proxy_running = True 
        else:
            # on second select we go into the main app
            self.app.switch_screen("projects-screen")
        