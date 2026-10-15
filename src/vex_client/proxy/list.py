from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import ListItem, ListView, Static

from vex_client.widgets.button import VexButton


@dataclass
class ProxyInstance:
    name: str
    server_address: str
    proxy_port: int
    api_port: int
    running: bool


class VexProxyListWidget(Widget):
    def __init__(self, instances: list[ProxyInstance], **kwargs) -> None:
        self.instances = instances
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(id="proxy-list-header"):
            yield Static(" INSTANCES ", id="proxy-list-title")
            yield VexButton("\[c] Create", id="btn-create")
            yield VexButton("\[e] Edit", id="btn-edit")
            yield VexButton("\[d] Delete", id="btn-delete")
        yield ProxyList(
            *[ProxyListItem(i) for i in self.instances],
            id="proxy-listview",
        )


class ProxyList(ListView, can_focus=True):
    """
    Vex proxy list for adding and selecting a vex-cli instance to run.
    """

    BINDINGS: ClassVar = [
        Binding("enter", "select_cursor", "Start/Enter instance", show=True),
        Binding("k", "cursor_up", "🡅", show=False),
        Binding("j", "cursor_down", "🡇", show=False),
        Binding("d", "delete_item", "Delete instance", show=True),
    ]

    def action_delete_item(self):
        if self.index is None:
            return

        item = self.highlighted_child
        item = cast(ProxyListItem, item)

        if item.instance.running:
            message = "Instance is running. Stop it to delete it."
            self.notify(title="Cannot delete instance!", message=message)
        else:
            self.pop(self.index)

    def does_instance_exist(self, instance: ProxyInstance) -> ProxyListItem | None:
        for child in self.children:
            list_item = cast(ProxyListItem, child)
            if list_item.instance == instance:
                return list_item
        return None


class ProxyListItem(ListItem):
    """
    Proxy list item with a status_dot and buttons.
    """

    def __init__(self, instance: ProxyInstance, **kwargs) -> None:
        self.instance = instance
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="row-inner"):
            yield Static("○", id="instance-dot", classes="row-indicator")
            yield Static(self.instance.name, id="instance-name", classes="row-name")
            with Horizontal(classes="row-actions"):
                yield VexButton("\[s] Stop", id="btn-stop")
                yield VexButton("\[↵] Connect", id="btn-connect")
                yield VexButton("\[↵] Start", id="btn-start")

    def on_mount(self) -> None:
        self._apply_running_state()

    def set_running(self, running: bool) -> None:
        self.instance.running = running
        self._apply_running_state()

    def _apply_running_state(self) -> None:
        running = self.instance.running
        self.set_class(running, "row-running")
        instance_dot = self.query_one("#instance-dot", Static)
        instance_dot.set_class(running, "running")
        self.query_one("#btn-stop", VexButton).set_class(running, "running")
        self.query_one("#btn-connect", VexButton).set_class(running, "running")
        self.query_one("#btn-start", VexButton).set_class(running, "running")

        if running:
            instance_dot.update("●")
        else:
            instance_dot.update("○")

    def update_instance(self, instance_data: ProxyInstance):
        self.instance.name = instance_data.name
        self.instance.server_address = instance_data.server_address
        self.instance.proxy_port = instance_data.proxy_port
        self.instance.api_port = instance_data.api_port
        self.instance.running = instance_data.running
        self._apply_running_state()
