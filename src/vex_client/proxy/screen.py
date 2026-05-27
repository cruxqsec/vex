from typing import TYPE_CHECKING, cast

from pydantic import ValidationError
import websockets
import time

if TYPE_CHECKING:
    from vex_client.app import VexApp

import logging

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import ListView, Static, Button
from textual.containers import Container, Horizontal, Vertical

from vex_cli.bind import try_bind_ports
from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import is_process_running, read_pid_file
from vex_client.api.health_check import check_health_pid
from vex_client.modals.proxy_modal import CreateUpdateProxyScreen
from vex_client.modals.confirm import ConfirmModal
from vex_client.widgets.footer import VexFooter
from vex_client.proxy.list import (
    VexProxyListWidget,
    ProxyList,
    ProxyListItem,
    ProxyInstance,
)
from vex_client.proxy.cards import ProxyStatusCard, ProxyInfoCard
from vex_client.widgets.logs_panel import VexLogsPanel

logger = logging.getLogger(__name__)

BANNER = """
░██    ░██                       
░██    ░██                       
░██    ░██  ░███████  ░██    ░██ 
░██    ░██ ░██    ░██  ░██  ░██  
 ░██  ░██  ░█████████   ░█████   
  ░██░██   ░██         ░██  ░██  
   ░███     ░███████  ░██    ░██
        
"""

BANNER_2 = """
░██    ░██  ░███████  ░██    ░██ 
░██    ░██ ░██    ░██  ░██  ░██  
 ░██  ░██  ░█████████   ░█████   
  ░██░██   ░██         ░██  ░██  
   ░███     ░███████  ░██    ░██ 
"""

BANNER_3 = """\
 ██╗   ██╗███████╗██╗  ██╗
 ██║   ██║██╔════╝╚██╗██╔╝
 ██║   ██║█████╗   ╚███╔╝ 
 ╚██╗ ██╔╝██╔══╝   ██╔██╗ 
  ╚████╔╝ ███████╗██╔╝ ██╗
   ╚═══╝  ╚══════╝╚═╝  ╚═╝"""

TAGLINE = "SECURITY TOOLKIT IN THE TERMINAL"
NOT_STARTED = -1

class VexProxyScreen(Screen):
    CSS_PATH = "proxy.tcss"

    BINDINGS = [
        Binding("c", "create_instance", "Add instance"),
        Binding("e", "edit_instance", "Update instance"),
        Binding("s", "stop_instance", "Stop instance"),
        Binding("ctrl+c", "app.quit", "Quit"),
    ]

    @property
    def proxy_list(self) -> ProxyList:
        return self.query_one(ProxyList)

    @property
    def status_card(self) -> ProxyStatusCard:
        return self.query_one("#proxy-status-card", ProxyStatusCard)

    @property
    def info_card(self) -> ProxyInfoCard:
        return self.query_one("#proxy-info-card", ProxyInfoCard)

    @property
    def footer(self) -> VexFooter:
        return self.query_one(VexFooter)

    def __init__(self) -> None:
        self._instances = [
            ProxyInstance("Default instance", "127.0.0.1", 8080, 9000, running=False),
            ProxyInstance("Remote instance", "10.10.15.1", 8083, 9090, running=False),
        ]
        self._proxy_start_time: float = NOT_STARTED
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="banner-container"):
            yield Static(BANNER_3, id="banner")
            yield Static(TAGLINE, id="tagline")
        with Horizontal(id="proxy-main"):
            yield VexProxyListWidget(self._instances, id="proxy-list")
            with Vertical(id="proxy-right"):
                yield ProxyStatusCard(id="proxy-status-card")
                yield ProxyInfoCard(id="proxy-info-card")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self):
        await self.check_for_running_instance()

    def on_screen_resume(self) -> None:
        running_instance = next((obj for obj in self._instances if obj.running), None)

        if running_instance:
            self.status_card.set_active(running_instance, self._elapsed_str())
        else:
            self.status_card.set_active(None, self._elapsed_str())

    def _elapsed_str(self) -> str:
        elapsed = int(time.monotonic() - self._proxy_start_time)
        mins = elapsed // 60
        if mins < 1:
            return "just now"
        elif mins < 60:
            return f"{mins} minutes ago"
        hours, _ = divmod(mins, 60)
        return f"{hours} hours ago"

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
                return

            instance_data = ProxyInstance(
                name="Default instance",  # we set it as default because we don't know the name
                server_address=pid_data.host,
                proxy_port=pid_data.proxy_port,
                api_port=pid_data.api_port,
                running=False,
            )

            list_item = self.proxy_list.does_instance_exist(instance_data)

            if list_item is None:
                list_item = ProxyListItem(instance_data)
                self.proxy_list.append(list_item)

            # call /health endpoint to confirm the pid from
            # the file is the same as from the endpoint
            health_check_pid_result = await check_health_pid(
                host=list_item.instance.server_address,
                port=list_item.instance.api_port,
            )

            if health_check_pid_result == pid_data.pid:
                app.log_vex("Found running instance", severity="info")
                server_info = VexServerInfo(
                    server_address=instance_data.server_address,
                    proxy_port=instance_data.proxy_port,
                    api_port=instance_data.api_port,
                )
                app.vex_controller.server_info = server_info
                app.vex_controller.cli_pid = pid_data.pid
                list_item.set_running(True)
                self._proxy_start_time = time.monotonic()
                self.status_card.set_active(list_item.instance, self._elapsed_str())

        except (OSError, ValidationError):
            app.log_vex("Error reading vex.pid file!", severity="error")

    @work(name="server_monitor", exclusive=True)
    async def _server_monitor(self):
        app = cast("VexApp", self.app)
        host, port = app.get_api_info()
        if host is None or port is None:
            return

        try:
            async with websockets.connect(
                f"ws://{host}:{port}/ws/ping",
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                app.server_online = True
                app.log_vex("Server connected")
                await ws.wait_closed()
                app.log_vex("Server shutdown")
        except websockets.ConnectionClosed:
            app.log_vex("Server closed connection unexpectedly", "warning")
        except OSError:
            app.log_vex("Could not reach server, is it running?", "error")
        except Exception as e:
            app.log_vex(f"Unexpected error in server monitor: {e}", "error")
        finally:
            app.server_online = False
    
    async def _start_vex(self, selected_item: ProxyListItem):
        app = cast("VexApp", self.app)
        server_info = VexServerInfo(
            server_address=selected_item.instance.server_address,
            proxy_port=selected_item.instance.proxy_port,
            api_port=selected_item.instance.api_port,
        )

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
            selected_item.set_running(True)
            self._proxy_start_time = time.monotonic()
            self.status_card.set_active(selected_item.instance, self._elapsed_str())
        else:
            app.log_vex(
                message="Failed to start instance. Check logs.", severity="error"
            )

    async def _enter_vex(self):
        app = cast("VexApp", self.app)
        self._server_monitor()
        app.switch_screen("projects-screen")

    async def _stop_vex(self, selected_instance: ProxyListItem):
        app = cast("VexApp", self.app)

        if not app.vex_controller.is_cli_running:
            return

        async def do_stop(confirmed: bool):
            if not confirmed:
                return

            successful_stop = app.vex_controller.stop_vex_cli()

            if successful_stop:
                selected_instance.set_running(False)
                await app.set_active_project(None)
                self.status_card.set_active(None)
                app.log_vex(message="Server stopped.")
            else:
                app.log_vex(
                    message="Failed to stop server!",
                    severity="error",
                )

        app.push_screen(ConfirmModal(f'Stop running instance?'), do_stop) # type: ignore

    @on(ListView.Highlighted)
    async def update_info_card(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, ProxyListItem):
            self.info_card.update_instance(event.item.instance)

    # ------------ actions -----------------

    @on(ListView.Selected)
    async def start_enter_vex(self, event: ListView.Selected) -> None:
        """
        Starts vex-cli when we press Enter on selected element.
        On second enter or if the vex-cli is already running we enter main interface.
        """
        selected_item: ProxyListItem = cast(ProxyListItem, event.item)
        app = cast("VexApp", self.app)

        if app.vex_controller.is_cli_running:
            await self._enter_vex()
            return

        await self._start_vex(selected_item)

    async def action_stop_instance(self) -> None:
        """Stop the instance if currently running"""
        # we have to work with the highlighted element
        selected_instance = self.proxy_list.highlighted_child
        if selected_instance is None:
            return

        selected_instance = cast(ProxyListItem, selected_instance)
        await self._stop_vex(selected_instance)

    async def action_create_instance(self):
        """
        Allow the user to add the list item instance data.
        """

        def create_instance(instance_data: ProxyInstance):
            item = ProxyListItem(instance_data)
            self.proxy_list.append(item)
            self._instances.append(instance_data)

        self.app.push_screen(CreateUpdateProxyScreen(None), create_instance)  # type: ignore

    async def action_edit_instance(self):
        """
        Allow the user to update the list item instance data.
        """
        selected_item = self.proxy_list.highlighted_child
        if selected_item is None:
            return

        selected_item = cast(ProxyListItem, selected_item)

        def edit_instance(instance_data: ProxyInstance):
            selected_item.update_instance(instance_data)

        self.app.push_screen(
            CreateUpdateProxyScreen(selected_item.instance), edit_instance)  # type: ignore

    # ------------ button logic -----------------

    @on(Button.Pressed, "#btn-create")
    async def on_create(self, event: Button.Pressed) -> None:
        await self.action_create_instance()

    @on(Button.Pressed, "#btn-edit")
    async def on_edit(self, event: Button.Pressed) -> None:
        await self.action_edit_instance()

    @on(Button.Pressed, "#btn-delete")
    async def on_delete(self, event: Button.Pressed) -> None:
        # TODO: check if the clicked button is on the highlighted element 
        self.proxy_list.action_delete_item()

    @on(Button.Pressed, "#btn-stop")
    async def on_stop(self, event: Button.Pressed) -> None:
        row = event.button.ancestors_with_self
        selected_instance = next(a for a in row if isinstance(a, ProxyListItem))
        await self._stop_vex(selected_instance)
    
    @on(Button.Pressed, "#btn-connect")
    async def on_connect(self, event: Button.Pressed) -> None:
        row = event.button.ancestors_with_self
        selected_instance = next(a for a in row if isinstance(a, ProxyListItem))
        app = cast("VexApp", self.app)

        if app.vex_controller.is_cli_running and selected_instance.instance.running:
            await self._enter_vex()

    @on(Button.Pressed, "#btn-start")
    async def on_start(self, event: Button.Pressed) -> None:
        row = event.button.ancestors_with_self
        selected_instance = next(a for a in row if isinstance(a, ProxyListItem))
        await self._start_vex(selected_instance)