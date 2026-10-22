import asyncio
import time
from typing import TYPE_CHECKING, ClassVar, cast

import httpx
from pydantic import ValidationError
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, ListView, Static

from vex_cli.bind import try_bind_ports
from vex_cli.models.pydantic import ServerMetaData, VexServerInfo
from vex_cli.pid_func import read_metadata_file
from vex_client.api.client import ApiClient
from vex_client.connection_manager import ConnectionState
from vex_client.modals.proxy_modal import CreateUpdateProxyScreen
from vex_client.process import find_local_process
from vex_client.proxy.cards import ProxyInfoCard, ProxyStatusCard
from vex_client.proxy.list import (
    InstanceState,
    ProxyInstance,
    ProxyList,
    ProxyListItem,
    VexProxyListWidget,
)
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel

if TYPE_CHECKING:
    from vex_client.app import VexApp

BANNER_3 = """\
 ██╗   ██╗███████╗██╗  ██╗
 ██║   ██║██╔════╝╚██╗██╔╝
██║   ██║█████╗   ╚███╔╝
╚██╗ ██╔╝██╔══╝   ██╔██╗
  ╚████╔╝ ███████╗██╔╝ ██╗
   ╚═══╝  ╚══════╝╚═╝  ╚═╝"""

TAGLINE = "TERMINAL SECURITY TOOLKIT"


class VexProxyScreen(Screen):
    CSS_PATH = "proxy.tcss"

    BINDINGS: ClassVar = [
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
            ProxyInstance(
                "Default instance",
                VexServerInfo(
                    server_address="127.0.0.1", proxy_port=8080, api_port=9000
                ),
                mode="local",
            ),
            ProxyInstance(
                "Remote instance",
                VexServerInfo(
                    server_address="10.10.15.1", proxy_port=8083, api_port=9090
                ),
                mode="remote",
            ),
        ]
        self._connected_at: float | None = None
        self._connected_server_info: VexServerInfo | None = None
        self._last_local_running = False
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

    async def on_mount(self) -> None:
        app = cast("VexApp", self.app)
        self.footer.query_one("#exit-cmd-key").query_one(".description", Label).update(
            "Exit the app"
        )
        self.refresh_connection_status()
        self.set_interval(1.0, self._check_local_process)
        try:
            await self._discover_local_instance()
        except (OSError, httpx.HTTPError) as exc:
            app.log_vex(
                "Could not discover the local instance.",
                severity="warning",
                log_message=f"Local instance discovery failed: {exc}",
            )
        except ValidationError:
            app.log_vex(
                "Could not read the local instance details.",
                severity="error",
                log_message="Invalid local instance metadata during discovery",
                exc_info=True,
            )
        finally:
            self.refresh_connection_status()

    def on_screen_resume(self) -> None:
        self.refresh_connection_status()

    def _check_local_process(self) -> None:
        """Simple process monitor."""
        # TODO: make a proper monitor
        if not self.is_mounted or self.app.screen is not self:
            return

        app = cast("VexApp", self.app)
        if app.cli_controller.is_cli_running != self._last_local_running:
            self.refresh_connection_status()

    def _is_local_running(self, item: ProxyListItem) -> bool:
        app = cast("VexApp", self.app)
        controller = app.cli_controller
        return (
            item.instance.mode == "local"
            and controller.server_info == item.instance.server_info
            and controller.is_cli_running
        )

    def _has_active_connection(self, item: ProxyListItem) -> bool:
        app = cast("VexApp", self.app)
        manager = app.connection_manager
        return (
            manager.server_info == item.instance.server_info
            and manager.state is not ConnectionState.DISCONNECTED
        )

    def get_instance_state(self, item: ProxyListItem) -> InstanceState:
        """Get the current instance state if it's connected and has spawned a local vex-cli."""
        app = cast("VexApp", self.app)
        manager = app.connection_manager

        # first we check if we are connected
        if self._has_active_connection(item):
            if manager.state is ConnectionState.CONNECTED:
                return InstanceState.CONNECTED
            if manager.state is ConnectionState.CONNECTING:
                return InstanceState.CONNECTING
            if manager.state is ConnectionState.RECONNECTING:
                return InstanceState.RECONNECTING

        if item.instance.mode == "local" and not self._is_local_running(item):
            return InstanceState.STOPPED
        return InstanceState.DISCONNECTED

    def get_running_local_item(self) -> ProxyListItem | None:
        for child in self.proxy_list.children:
            if isinstance(child, ProxyListItem) and self._is_local_running(child):
                return child
        return None

    def _calculate_elapsed_time(self) -> str:
        if self._connected_at is None:
            return "not connected"
        elapsed = int(time.monotonic() - self._connected_at)
        mins = elapsed // 60
        if mins < 1:
            return "just now"
        elif mins < 60:
            return f"{mins} minutes ago"
        hours = mins // 60
        return f"{hours} hours ago"

    def refresh_connection_status(self) -> None:
        app = cast("VexApp", self.app)
        manager = app.connection_manager
        self._last_local_running = app.cli_controller.is_cli_running
        connected_item: ProxyListItem | None = None

        for child in self.proxy_list.children:
            if not isinstance(child, ProxyListItem) or not child.is_mounted:
                continue

            state = self.get_instance_state(child)
            child.render_state(state, local_running=self._is_local_running(child))
            if state is InstanceState.CONNECTED and connected_item is None:
                connected_item = child

        if (
            manager.state is not ConnectionState.CONNECTED
            or manager.server_info is None
        ):
            self._connected_at = None
            self._connected_server_info = None
            self.status_card.set_active(None)
            return

        if (
            self._connected_at is None
            or self._connected_server_info != manager.server_info
        ):
            self._connected_at = time.monotonic()
            self._connected_server_info = manager.server_info.model_copy()

        if connected_item is None:
            self.status_card.set_active(None)
            return

        self.status_card.set_active(
            connected_item.instance,
            self._calculate_elapsed_time(),
        )

    def reset(self) -> None:
        self.refresh_connection_status()

    # ------------ Discover, start and connect logic -----------------

    async def _discover_local_instance(self) -> None:
        """Discover and adopt a verified local process without connecting to it."""
        app = cast("VexApp", self.app)
        controller = app.cli_controller
        if controller.is_cli_running:
            return

        try:
            server_metadata: ServerMetaData = read_metadata_file()
        except FileNotFoundError:
            return

        process = find_local_process(server_metadata.pid, server_metadata.create_time)
        if process is None:
            return

        client = ApiClient(server_metadata.host, server_metadata.api_port)
        try:
            health_pid = await client.health.check_health_pid()
        finally:
            await client.close()

        if health_pid != server_metadata.pid:
            return

        server_info = VexServerInfo(
            server_address=server_metadata.host,
            proxy_port=server_metadata.proxy_port,
            api_port=server_metadata.api_port,
        )

        if controller.is_cli_running:
            return
        if controller.server_info is not None:
            controller.clear()
        if not controller.attach_to_running(process, server_info):
            return

        app.log_vex("Found running instance", severity="info")
        list_item = self.proxy_list.find_item(server_info, mode="local")
        if list_item is None:
            instance_data = ProxyInstance(
                name="Discovered instance",
                server_info=server_info.model_copy(),
                mode="local",
            )
            await self.proxy_list.append(ProxyListItem(instance_data))

        self.refresh_connection_status()

    async def _start_local_instance(self, item: ProxyListItem) -> None:
        if item.instance.mode != "local":
            return
        if self.get_instance_state(item) is not InstanceState.STOPPED:
            return

        app = cast("VexApp", self.app)
        controller = app.cli_controller
        if controller.is_cli_running:
            self.notify("Stop the running local instance before starting another.")
            return

        server_info = item.instance.server_info.model_copy()
        can_bind, port = await asyncio.to_thread(try_bind_ports, server_info)
        if not can_bind:
            app.log_vex(f"Port {port} is already in use!", severity="error")
            return

        if controller.is_cli_running:
            return
        if self.get_instance_state(item) is not InstanceState.STOPPED:
            return
        if controller.server_info is not None:
            controller.clear()

        try:
            startup_successful = await controller.spawn_vex_cli(server_info)
            if startup_successful:
                app.log_vex("vex-cli process launched.", severity="success")
            else:
                app.log_vex(
                    "Could not start vex-cli.",
                    severity="error",
                    write_to_log=False,
                )
        finally:
            self.refresh_connection_status()

    async def _connect_instance(self, item: ProxyListItem) -> None:
        if self.get_instance_state(item) is not InstanceState.DISCONNECTED:
            return

        app = cast("VexApp", self.app)
        try:
            await app.connection_manager.connect(item.instance.server_info.model_copy())
        finally:
            self.refresh_connection_status()

    def _enter_instance(self, item: ProxyListItem) -> None:
        if self.get_instance_state(item) is InstanceState.CONNECTED:
            self.app.switch_screen("projects-screen")

    async def _disconnect_instance(self, item: ProxyListItem) -> None:
        if not self._has_active_connection(item):
            return

        app = cast("VexApp", self.app)
        try:
            await app.connection_manager.disconnect()
        finally:
            self.refresh_connection_status()

    async def activate_item(self, item: ProxyListItem) -> None:
        state = self.get_instance_state(item)
        if state is InstanceState.STOPPED:
            await self._start_local_instance(item)
        elif state is InstanceState.DISCONNECTED:
            await self._connect_instance(item)
        elif state is InstanceState.CONNECTED:
            self._enter_instance(item)

    async def _stop_vex(self, item: ProxyListItem) -> None:
        if not self._is_local_running(item):
            return

        app = cast("VexApp", self.app)
        server_info = item.instance.server_info.model_copy()
        try:
            successful_stop = await app.cli_controller.stop_vex_cli()
            if not successful_stop:
                app.log_vex("Failed to stop vex-cli!", severity="error")
                return

            app.log_vex("vex-cli stopped.")
            manager = app.connection_manager
            if (
                manager.server_info == server_info
                and manager.state is not ConnectionState.DISCONNECTED
            ):
                await manager.disconnect()
        finally:
            self.refresh_connection_status()

    @on(ListView.Highlighted)
    async def update_info_card(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, ProxyListItem):
            self.info_card.update_instance(event.item.instance)

    @on(ListView.Selected)
    async def list_view_select(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ProxyListItem):
            await self.activate_item(event.item)

    # ------------ Binding actions -----------------

    async def action_stop_instance(self) -> None:
        selected_item = self.proxy_list.highlighted_child
        if isinstance(selected_item, ProxyListItem):
            await self._stop_vex(selected_item)

    async def action_disconnect_instance(self) -> None:
        selected_item = self.proxy_list.highlighted_child
        if isinstance(selected_item, ProxyListItem):
            await self._disconnect_instance(selected_item)

    def _can_modify_instance(self, item: ProxyListItem) -> bool:
        if self._is_local_running(item) or self._has_active_connection(item):
            self.notify("Stop and disconnect this instance before editing or deleting it.")
            return False
        return True

    async def action_delete_instance(self) -> None:
        selected_item = self.proxy_list.highlighted_child
        index = self.proxy_list.index
        if not isinstance(selected_item, ProxyListItem) or index is None:
            return
        if not self._can_modify_instance(selected_item):
            return

        await self.proxy_list.pop(index)
        self.refresh_connection_status()

    async def action_create_instance(self) -> None:
        async def create_instance(instance_data: ProxyInstance | None) -> None:
            if instance_data is None:
                return
            await self.proxy_list.append(ProxyListItem(instance_data))
            self.refresh_connection_status()

        self.app.push_screen(CreateUpdateProxyScreen(None), create_instance)

    async def action_edit_instance(self) -> None:
        selected_item = self.proxy_list.highlighted_child
        if not isinstance(selected_item, ProxyListItem):
            return
        if not self._can_modify_instance(selected_item):
            return

        def edit_instance(instance_data: ProxyInstance | None) -> None:
            if instance_data is None or not selected_item.is_mounted:
                return
            if not self._can_modify_instance(selected_item):
                return
            selected_item.update_instance(instance_data)
            self.info_card.update_instance(selected_item.instance)
            self.refresh_connection_status()

        self.app.push_screen(
            CreateUpdateProxyScreen(selected_item.instance),
            edit_instance,
        )

    # ------------ Button actions -----------------

    @on(Button.Pressed, "#btn-create")
    async def on_create(self, event: Button.Pressed) -> None:
        await self.action_create_instance()

    @on(Button.Pressed, "#btn-edit")
    async def on_edit(self, event: Button.Pressed) -> None:
        await self.action_edit_instance()

    @on(Button.Pressed, "#btn-delete")
    async def on_delete(self, event: Button.Pressed) -> None:
        await self.action_delete_instance()

    @on(Button.Pressed, "#btn-stop")
    async def on_stop(self, event: Button.Pressed) -> None:
        selected_item = self.get_selected_list_item_from_button_event(event)
        if selected_item is not None:
            await self._stop_vex(selected_item)

    @on(Button.Pressed, "#btn-connect")
    async def on_connect(self, event: Button.Pressed) -> None:
        selected_item = self.get_selected_list_item_from_button_event(event)
        if selected_item is not None:
            await self._connect_instance(selected_item)

    @on(Button.Pressed, "#btn-start")
    async def on_start(self, event: Button.Pressed) -> None:
        selected_item = self.get_selected_list_item_from_button_event(event)
        if selected_item is not None:
            await self._start_local_instance(selected_item)

    @on(Button.Pressed, "#btn-enter")
    def on_enter(self, event: Button.Pressed) -> None:
        selected_item = self.get_selected_list_item_from_button_event(event)
        if selected_item is not None:
            self._enter_instance(selected_item)

    @on(Button.Pressed, "#btn-disconnect")
    async def on_disconnect(self, event: Button.Pressed) -> None:
        selected_item = self.get_selected_list_item_from_button_event(event)
        if selected_item is not None:
            await self._disconnect_instance(selected_item)

    def get_selected_list_item_from_button_event(
        self, event: Button.Pressed
    ) -> ProxyListItem | None:
        for ancestor in event.button.ancestors_with_self:
            if isinstance(ancestor, ProxyListItem):
                return ancestor
        return None
