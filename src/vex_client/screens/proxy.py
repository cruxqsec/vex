from typing import cast, TYPE_CHECKING
from pydantic import ValidationError

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Footer, ListView
from textual.containers import Container, Center, Vertical
from textual.binding import Binding

from vex_cli.models import VexServerInfo 
from vex_cli.locations import vex_pid_file
from vex_cli.pid_func import is_process_running, read_pid_file

from vex_client.version import VERSION
from vex_client.widgets.proxy.proxy_list import VexProxyList, VexProxyListItem
from vex_client.screens.modals.proxy_modal import CreateUpdateProxyScreen, InstanceData
from vex_client.api.health_check import check_health_retries, check_health_pid

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


class VexProxyScreen(Screen):

    CSS_PATH="css/proxy.tcss"
    
    BINDINGS = [
        Binding("c", "add_instance","Add instance"),
        Binding("u", "update_instance","Update instance"),
        Binding("ctrl+s", "stop_instance","Stop instance", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False),
    ]
           
    @property
    def proxy_list(self) -> VexProxyList:
        return self.query_one("#proxy-list", VexProxyList)
    
    def compose(self) -> ComposeResult:
        with Vertical(id="banner-container"):
            yield Static(banner, id="banner")
            #yield Center(VexLink("vex.sh", url=website, id="website-link"))
            yield Center(Static(f"Version: {VERSION}", id="version"))
        with Container(id="main-container"):
            yield VexProxyList(id="proxy-list")
        yield Footer()
        
    async def on_mount(self):
        # append the default proxy
        self.proxy_list.append(
            VexProxyListItem("Local instance", VexServerInfo("127.0.0.1", 8080, 9000))
        )
        self.proxy_list.index = 0
        self.item_to_update : VexProxyListItem | None = None
        
        await self.check_for_running_instance()
        
    def action_add_instance(self):
        """Add instance created in the modal screen to the proxy list"""

        def create_instance(instance_data: InstanceData):
            server_info = VexServerInfo(
                instance_data.address,
                instance_data.proxy_port,
                instance_data.api_port
            )
            item = VexProxyListItem(instance_data.name, server_info)
            self.proxy_list.append(item)
        
        self.app.push_screen(CreateUpdateProxyScreen(None), create_instance) # type: ignore

    def action_update_instance(self):
        """Allow the user to change the instance data."""
        selected_instance = self.proxy_list.highlighted_child 
        if selected_instance is None:
            return
        
        # cast for the typer
        selected_instance = cast(VexProxyListItem, selected_instance)
        self.item_to_update = selected_instance
        
        instance_data = InstanceData(
            selected_instance.instance_name, 
            selected_instance.server_info.server_address,
            selected_instance.server_info.proxy_port,
            selected_instance.server_info.api_port
        )

        def update_instance(instance_data: InstanceData):
            if self.item_to_update is None:
                return
            self.item_to_update.update_item(instance_data)
            self.item_to_update = None

        self.app.push_screen(CreateUpdateProxyScreen(instance_data), update_instance) # type: ignore
        
    @on(ListView.Selected)
    async def start_enter_vex(self, event: ListView.Selected) -> None:
        """Start vex-cli and on second select enter the main app with selected proxy."""
        selected_instance: VexProxyListItem = cast(VexProxyListItem, event.item)
        app = cast("VexApp", self.app)
        
        if app.is_vex_cli_running:
            # this should happen on second select or if proxy is already running
            # before we switch we should try a health check
            health_check_complete = await check_health_retries(
                retries=10,
                host=selected_instance.server_info.server_address,
                port=selected_instance.server_info.api_port
            )

            if health_check_complete:
                app.switch_screen("projects-screen")
            else:
                self.notify("Couldn't connect to the server", severity="error")
            return
            
        successful_startup = app.start_vex_cli(selected_instance.server_info)
        
        if successful_startup:
            selected_instance.toggle_active()
        
    def action_stop_instance(self):
        # we have to work with the highlighted element
        selected_instance = self.proxy_list.highlighted_child 
        if selected_instance is None:
            return
        
        # cast for the typer
        selected_instance = cast(VexProxyListItem, selected_instance)
        app = cast("VexApp", self.app)

        if app.is_vex_cli_running:
            selected_instance.toggle_active()
            app.stop_vex_cli()
    
    async def check_for_running_instance(self):
        pid_file = vex_pid_file()
        
        if not pid_file.exists():
            return
        
        try:
            pid_data = read_pid_file(pid_file)

            if not is_process_running(pid_data.pid):
                # stale pid file
                return

            server_info = VexServerInfo(
                server_address=pid_data.host,
                proxy_port=pid_data.proxy_port,
                api_port=pid_data.api_port
            )

            app = cast("VexApp", self.app)
            instance = self.proxy_list.does_instance_exist(server_info)
            
            if instance is None:
                # create new
                instance = VexProxyListItem("Running instance", server_info)
                self.proxy_list.append(instance)
            
            health_check_pid_result = await check_health_pid(
                host=instance.server_info.server_address,
                port=instance.server_info.api_port,
            )

            if health_check_pid_result == pid_data.pid:
                app.set_server_info(server_info)
                app.set_vex_pid(pid_data.pid)
                app.set_vex_running(True)
                self.call_after_refresh(instance.toggle_active)


        except (OSError, ValidationError):
            self.notify("Error reading vex.pid file.", severity="error")

        

