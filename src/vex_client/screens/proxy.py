from typing import TYPE_CHECKING, cast

from pydantic import ValidationError

if TYPE_CHECKING:
    from vex_client.app import VexApp

import logging

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import ListView, Static

from vex_cli.bind import try_bind_ports
from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import is_process_running, read_pid_file
from vex_client.api.health_check import check_health_pid, check_health_retries
from vex_client.screens.modals.proxy_modal import CreateUpdateProxyScreen, InstanceData
from vex_client.widgets.center_middle import CenterMiddle
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.proxy.proxy_list import VexProxyList, VexProxyListItem
from vex_client.widgets.logs_panel import VexLogsPanel

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


class VexProxyScreen(Screen):
    CSS_PATH = "css/proxy.tcss"

    BINDINGS = [
        Binding("c", "add_instance", "Add instance"),
        Binding("u", "update_instance", "Update instance"),
        Binding("ctrl+s", "stop_instance", "Stop instance", show=True),
        Binding("ctrl+c", "app.quit", "Quit", show=False),
        Binding("ctrl+f", "test", "Quit", show=False),
    ]

    @property
    def proxy_list(self) -> VexProxyList:
        return self.query_one("#proxy-list", VexProxyList)

    @property
    def footer(self) -> VexFooter:
        return self.query_one(VexFooter)

    def compose(self) -> ComposeResult:
        yield CenterMiddle(Static(banner, id="banner"), id="banner-container")
        yield VexProxyList(id="proxy-list")
        yield VexLogsPanel()
        yield VexFooter()

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

    async def check_for_running_instance(self):
        """
        Checks for any running instances of vex-cli.
        If it exists it adds it
        """

        app = cast("VexApp", self.app)
        pid_file = vex_pid_file()

        if not pid_file.exists():
            return

        try:
            pid_data = read_pid_file(pid_file)

            if not is_process_running(pid_data.pid):
                app.log_vex(
                    message="Found stale PID file in vex data directory. Please delete it.",
                    severity="error",
                )
                return

            server_info = VexServerInfo(
                server_address=pid_data.host,
                proxy_port=pid_data.proxy_port,
                api_port=pid_data.api_port,
            )

            instance = self.proxy_list.does_instance_exist(server_info)

            if instance is None:
                instance = VexProxyListItem("Running instance", server_info)
                self.proxy_list.append(instance)

            # call /health endpoint to confirm the pid from
            # the file is the same as from the endpoint
            health_check_pid_result = await check_health_pid(
                host=instance.server_info.server_address,
                port=instance.server_info.api_port,
            )

            if health_check_pid_result == pid_data.pid:
                app.log_vex("Found running instance.", severity="info")
                app.vex_controller.server_info = server_info
                app.vex_controller.cli_pid = pid_data.pid
                instance.toggle_active()
                app.server_online = True

        except (OSError, ValidationError):
            app.log_vex("Error reading vex.pid file!", severity="error")

    # ------------ actions -----------------

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
                app.log_vex("Connection failed: timeout.", severity="error")

            return

        can_bind, port = try_bind_ports(server_info)
        address = server_info.server_address

        if not can_bind:
            app.log_vex(
                message=f"Port {port} on {address} is already in use!",
                severity="error",
            )
            return

        successful_startup = app.vex_controller.start_vex_cli(server_info)

        if successful_startup:
            app.log_vex("Successfuly started vex-cli.", severity="success")
            app.log_vex(f"Proxy: {server_info.server_address}:{server_info.proxy_port}")
            app.log_vex(f"API: {server_info.server_address}:{server_info.api_port}")
            selected_instance.toggle_active()
            app.server_online = True
        else:
            app.log_vex(
                message="Failed to start instance. Check logs.", severity="error"
            )

    async def action_stop_instance(self) -> None:
        """Stops vex-cli when we press Ctrl+s on a highlighted list element"""
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
            await app.set_active_project(None)
            app.log_vex(message="Server stopped.")
            app.server_online = False
        else:
            app.log_vex(
                message="Failed to stop! Try `kill -9 $pid`",
                severity="error",
            )

    async def action_add_instance(self):
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

    async def action_update_instance(self):
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

    def action_test(self):
        self.log(self.footer.online_key.styles)
