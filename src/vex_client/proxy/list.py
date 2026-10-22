from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Literal

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static

from vex_cli.models.pydantic import VexServerInfo
from vex_client.widgets.button import VexButton


class InstanceState(Enum):
    STOPPED = "stopped"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    CONNECTED = "connected"


# TODO: currently we store server_info which as the connection address
# but actually it is the bind address
# for example:
# spawning a server we can bind it to 0.0.0.0
# but we would have to connect to localhost still!
@dataclass
class ProxyInstance:
    name: str
    server_info: VexServerInfo
    mode: Literal["local", "remote"]


class VexProxyListWidget(Widget):
    def __init__(self, instances: list[ProxyInstance], **kwargs) -> None:
        self.instances = instances
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(id="proxy-list-header"):
            yield Static(" INSTANCES ", id="proxy-list-title")
            yield VexButton(r"\[c] Create", id="btn-create")
            yield VexButton(r"\[e] Edit", id="btn-edit")
            yield VexButton(r"\[d] Delete", id="btn-delete")
        yield ProxyList(
            *[ProxyListItem(i) for i in self.instances],
            id="proxy-listview",
        )


class ProxyList(ListView, can_focus=True):
    """
    Vex proxy list for adding and selecting a vex-cli instance to run.
    """

    BINDINGS: ClassVar = [
        Binding("enter", "select_cursor", "Start/Connect/Enter instance", show=True),
        Binding("k", "cursor_up", "🡅", show=False),
        Binding("j", "cursor_down", "🡇", show=False),
        Binding("d", "screen.delete_instance", "Delete instance", show=True),
    ]


    def does_instance_exist(self, instance: ProxyInstance) -> ProxyListItem | None:
        for child in self.children:
            if isinstance(child, ProxyListItem) and child.instance == instance:
                return child

        return None

    def find_item(
        self,
        server_info: VexServerInfo,
        mode: Literal["local", "remote"],
    ) -> ProxyListItem | None:
        for child in self.children:
            if (
                isinstance(child, ProxyListItem)
                and child.instance.mode == mode
                and child.instance.server_info == server_info
            ):
                return child

        return None


class ProxyListItem(ListItem):
    """
    Proxy list item with a status_dot and buttons.
    """

    def __init__(self, instance: ProxyInstance, **kwargs) -> None:
        self.instance: ProxyInstance = instance
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="row-inner"):
            yield Static("○", id="instance-dot", classes="row-indicator")
            yield Static(self.instance.name, id="instance-name", classes="row-name")
            with Horizontal(classes="row-actions"):
                yield VexButton(r"\[↵] Enter", id="btn-enter")
                yield VexButton(r"\[↵] Connect", id="btn-connect")
                yield VexButton(r"\[↵] Start", id="btn-start")
                yield VexButton(r"\[s] Stop", id="btn-stop")
                yield VexButton("Disconnect", id="btn-disconnect")
                yield VexButton("Connecting…", id="btn-progress", disabled=True)


    def render_state(self, state: InstanceState, *, local_running: bool) -> None:
        local = self.instance.mode == "local"
        connected = state == InstanceState.CONNECTED
        busy = state in (InstanceState.CONNECTING, InstanceState.RECONNECTING)

        self.query_one("#btn-start", VexButton).display = (
            local and state == InstanceState.STOPPED
        )
        self.query_one("#btn-connect", VexButton).display = (
            state == InstanceState.DISCONNECTED
        )
        self.query_one("#btn-enter", VexButton).display = connected
        self.query_one("#btn-disconnect", VexButton).display = busy or connected
        self.query_one("#btn-stop", VexButton).display = local and local_running

        progress = self.query_one("#btn-progress", VexButton)
        progress.display = busy
        if state == InstanceState.RECONNECTING:
            progress.label = "Reconnecting…"
        else:
            progress.label = "Connecting…"

        self.set_class(connected, "row-connected")
        self.set_class(busy, "row-busy")
        instance_dot = self.query_one("#instance-dot", Static)
        instance_dot.set_class(connected, "connected")
        instance_dot.set_class(busy, "busy")
        if connected:
            instance_dot.update("●")
        else:
            instance_dot.update("○")


    def update_instance(self, instance_data: ProxyInstance):
        self.instance.name = instance_data.name
        self.instance.server_info = instance_data.server_info
        self.instance.mode = instance_data.mode
        self.query_one("#instance-name", Static).update(self.instance.name)
