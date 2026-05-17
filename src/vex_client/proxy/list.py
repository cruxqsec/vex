from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView, Static

from vex_cli.models.pydantic import VexServerInfo
from vex_client.modals.proxy_modal import InstanceData
from vex_client.proxy.status import Status


class VexProxyList(ListView, can_focus=True):
    """
    Vex proxy list for adding and selecting a vex-cli instance to run.
    """

    BORDER_TITLE = "Vex proxies"

    BINDINGS = [
        Binding("enter", "select_cursor", "Start/Enter instance", show=True),
        Binding("k", "cursor_up", "🡅", show=False),
        Binding("j", "cursor_down", "🡇", show=False),
        Binding("d", "delete_item", "Delete instance", show=True),
    ]

    def action_delete_item(self):
        if self.index is None:
            return

        item = self.highlighted_child
        item = cast(VexProxyListItem, item)

        if item.is_active:
            message = "Instance is running. Stop it to delete it."
            self.notify(title="Cannot delete instance!", message=message)
        else:
            self.pop(self.index)

    def does_instance_exist(
        self, server_info: VexServerInfo
    ) -> VexProxyListItem | None:
        for child in self.children:
            instance_item = cast(VexProxyListItem, child)
            if instance_item.server_info == server_info:
                return instance_item
        return None


class VexProxyListItem(ListItem):
    """
    Proxy list item with a status_dot.
    """

    is_active = reactive(False)

    def __init__(self, instance_name: str, server_info: VexServerInfo) -> None:
        super().__init__()
        self.server_info = server_info
        self.instance_name = instance_name

        self.proxy_info_str = (
            f"""{instance_name} {server_info.server_address} """
            f"""proxy:{server_info.proxy_port} api:{server_info.api_port}"""
        )

    @property
    def status_dot(self) -> Static:
        return self.query_one(".status-dot", Static)

    @property
    def status(self) -> Status:
        return self.query_one(".status", Status)

    def toggle_active(self):
        self.is_active = not self.is_active

    def watch_is_active(self, active: bool):
        if active:
            self.status_dot.toggle_class("active")
            self.status.state = "Running"
        else:
            self.status_dot.toggle_class("active")
            self.status.state = "Shutdown"

    def update_item(self, instance_data: InstanceData):
        self.instance_name = instance_data.name
        self.server_info.server_address = instance_data.address
        self.server_info.proxy_port = instance_data.proxy_port
        self.server_info.api_port = instance_data.api_port

        self.proxy_info_str = (
            f"""{instance_data.name} """
            f"""{instance_data.address} """
            f"""proxy:{instance_data.proxy_port} """
            f"""api:{instance_data.api_port}"""
        )
        self.query_one(Label).update(self.proxy_info_str)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="item-row"):
            yield Static("⬤", classes="status-dot active")
            yield Label(self.proxy_info_str, classes="instance-data")
            yield Status(classes="status")
