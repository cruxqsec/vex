from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

if TYPE_CHECKING:
    from vex_client.app import VexApp

import logging

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, ListView, Static

from vex_cli.bind import try_bind_ports
from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import is_process_running, read_pid_file
from vex_client.api.health_check import check_health_pid, check_health_retries
from vex_client.screens.modals.proxy_modal import CreateUpdateProxyScreen, InstanceData
from vex_client.version import VERSION
from vex_client.widgets.proxy.proxy_list import VexProxyList, VexProxyListItem

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
    CSS_PATH = "css/proxy.tcss"

    BINDINGS = [
        Binding("c", "add_instance", "Add instance"),
        Binding("u", "update_instance", "Update instance"),
        Binding("ctrl+s", "stop_instance", "Stop instance", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False),
    ]

    @property
    def proxy_list(self) -> VexProxyList:
        return self.query_one("#proxy-list", VexProxyList)

    def compose(self) -> ComposeResult:
        with Vertical(id="banner-container"):
            yield Static(banner, id="banner")
            # yield Center(VexLink("vex.sh", url=website, id="website-link"))
            yield Center(Static(f"Version: {VERSION}", id="version"))
        with Container(id="main-container"):
            yield VexProxyList(id="proxy-list")
        yield Footer()

    async def on_mount(self):
        # append the default proxy
        self.proxy_list.append(
            VexProxyListItem(
                "Local instance",
                VexServerInfo(
                    server_address="127.0.0.1", proxy_port=8080, api_port=9000
                ),
            )
        )
        self.proxy_list.index = 0
        self.item_to_update: VexProxyListItem | None = None

        await self.check_for_running_instance()

    def action_add_instance(self):
        """
        Allow the user to add the list item instance data.
        """

        def create_instance(instance_data: InstanceData):
            server_info = VexServerInfo(
                server_address=instance_data.address,
                proxy_port=instance_data.proxy_port,
                api_port=instance_data.api_port,
            )
            item = VexProxyListItem(instance_data.name, server_info)
            self.proxy_list.append(item)

        self.app.push_screen(CreateUpdateProxyScreen(None), create_instance)  # type: ignore

    def action_update_instance(self):
        """
        Allow the user to update the list item instance data.
        """
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
            selected_instance.server_info.api_port,
        )

        def update_instance(instance_data: InstanceData):
            if self.item_to_update is None:
                return
            self.item_to_update.update_item(instance_data)
            self.item_to_update = None

        self.app.push_screen(CreateUpdateProxyScreen(instance_data), update_instance)  # type: ignore

    @on(ListView.Selected)
    async def start_enter_vex(self, event: ListView.Selected) -> None:
        """
        Starts vex-cli when we press Enter on selected element.
        On second enter or if the vex-cli is already running we enter main interface.
        """

        selected_instance: VexProxyListItem = cast(VexProxyListItem, event.item)
        server_info = selected_instance.server_info
        app = cast("VexApp", self.app)

        if app.vex_controller.is_cli_running:
            # this should happen on second select or if proxy is already running
            # before we switch we should try a health check
            health_check_complete = await check_health_retries(
                retries=10,
                host=selected_instance.server_info.server_address,
                port=selected_instance.server_info.api_port,
            )

            if health_check_complete:
                app.switch_screen("projects-screen")
            else:
                self.notify("Couldn't connect to the server", severity="error")

            return

        can_bind, port = try_bind_ports(server_info)
        address = server_info.server_address

        if not can_bind:
            self.notify(
                title="ERROR",
                message=f"Port {port} on {address} is already in use!",
                severity="error",
            )
            return

        successful_startup = app.vex_controller.start_vex_cli(server_info)

        if successful_startup:
            message = (
                f"API server started on port:{server_info.api_port}\n"
                f"Proxy server started on port:{server_info.proxy_port}"
            )
            self.notify(message=message, timeout=5.0)
            selected_instance.toggle_active()
        else:
            self.notify(
                message="Failed to start instance. Check logs.", severity="error"
            )

    def action_stop_instance(self) -> None:
        """
        Stops vex-cli when we press Ctrl+s on a highlighted list element
        """
        # we have to work with the highlighted element
        selected_instance = self.proxy_list.highlighted_child
        if selected_instance is None:
            return

        # cast for the typer
        selected_instance = cast(VexProxyListItem, selected_instance)
        app = cast("VexApp", self.app)

        if not app.vex_controller.is_cli_running:
            return

        successful_stop = app.vex_controller.stop_vex_cli()

        if successful_stop:
            selected_instance.toggle_active()
            app.set_active_project(None)
            self.notify(message="Proxy instance has shutdown")
        else:
            self.notify(
                message="Could not stop vex-cli. Try stopping it yourself",
                severity="error",
            )

    async def check_for_running_instance(self):
        """
        Checks for any running instances of vex-cli.
        If it exists it adds it
        """

        pid_file = vex_pid_file()

        if not pid_file.exists():
            return

        try:
            pid_data = read_pid_file(pid_file)

            if not is_process_running(pid_data.pid):
                self.notify(
                    "Found stale PID file in vex data directory. Please delete it."
                )
                # stale pid file
                return

            server_info = VexServerInfo(
                server_address=pid_data.host,
                proxy_port=pid_data.proxy_port,
                api_port=pid_data.api_port,
            )

            app = cast("VexApp", self.app)
            instance = self.proxy_list.does_instance_exist(server_info)

            if instance is None:
                # create new
                instance = VexProxyListItem("Running instance", server_info)
                self.proxy_list.append(instance)

            # call /health endpoint to confirm the pid from
            # the file is the same as from the endpoint
            health_check_pid_result = await check_health_pid(
                host=instance.server_info.server_address,
                port=instance.server_info.api_port,
            )

            if health_check_pid_result == pid_data.pid:
                app.vex_controller.set_server_info(server_info)
                app.vex_controller.set_pid(pid_data.pid)
                self.call_after_refresh(instance.toggle_active)

        except (OSError, ValidationError):
            self.notify("Error reading vex.pid file.", severity="error")
