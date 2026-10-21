from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Rule, Static

from vex_client.proxy.list import ProxyInstance


class ProxyStatusCard(Widget):
    @property
    def status_name(self) -> Static:
        return self.query_one("#status-name", Static)

    @property
    def status_dot(self) -> Static:
        return self.query_one("#status-dot", Static)

    @property
    def status_meta(self) -> Static:
        return self.query_one("#status-meta", Static)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="status-row"):
            yield Static("●", id="status-dot")
            yield Static(" Not connected to any instance", id="status-name")
        yield Static("Connect to an instance to begin", id="status-meta")

    def set_active(
        self, instance: ProxyInstance | None = None, time_passed: str = ""
    ) -> None:
        connected = instance is not None
        if instance is not None:
            self.status_name.update(f" {instance.name}")
            self.status_meta.update(f"Connected · connected {time_passed}")
        else:
            self.status_name.update(" Not connected to any instance")
            self.status_meta.update("Connect to an instance to begin")

        self.set_class(connected, "active")
        self.status_name.set_class(connected, "active")
        self.status_dot.set_class(connected, "active")
        self.status_meta.set_class(connected, "active")


class ProxyInfoCard(Widget):
    def compose(self) -> ComposeResult:
        yield Static("Selected", id="info-title")
        yield Rule(id="info-divider")
        with Horizontal(classes="info-row"):
            yield Static("Name", classes="info-label")
            yield Static("", id="info-name", classes="info-value")
        with Horizontal(classes="info-row"):
            yield Static("Address", classes="info-label")
            yield Static("", id="info-address", classes="info-value")
        with Horizontal(classes="info-row"):
            yield Static("Proxy Port", classes="info-label")
            yield Static("", id="info-proxy-port", classes="info-value")
        with Horizontal(classes="info-row"):
            yield Static("API Port", classes="info-label")
            yield Static("", id="info-api-port", classes="info-value")

    def update_instance(self, instance: ProxyInstance) -> None:
        server_info = instance.server_info
        self.query_one("#info-name", Static).update(instance.name)
        self.query_one("#info-address", Static).update(server_info.server_address)
        self.query_one("#info-proxy-port", Static).update(str(server_info.proxy_port))
        self.query_one("#info-api-port", Static).update(str(server_info.api_port))
        