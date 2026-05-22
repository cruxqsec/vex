from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Rule

from vex_client.proxy.list import ProxyInstance

class ProxyStatusCard(Widget):
    @property
    def status_name(self) -> Static:
        return self.query_one("#status-name", Static)

    @property
    def status_meta(self) -> Static:
        return self.query_one("#status-meta", Static)

    def compose(self) -> ComposeResult:
        yield Static("● No proxy running", id="status-name")
        yield Static("Start a proxy to begin", id="status-meta")

    def set_active(
        self, instance: ProxyInstance | None = None, time_passed: str = ""
    ) -> None:
        running = False
        if instance:
            running = instance.running 
            self.status_name.update(f"● {instance.name}")
            self.status_meta.update(f"Running · started {time_passed}")
        else:
            self.status_name.update("● No proxy running")
            self.status_meta.update("Start a proxy to begin")

        self.set_class(running, "active")
        self.status_name.set_class(running, "active")
        self.status_meta.set_class(running, "active")



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
        with Horizontal(classes="info-row"):
            yield Static("Status", classes="info-label")
            yield Static("", id="info-status", classes="info-value")

    def update_instance(
        self, instance: ProxyInstance
    ) -> None:
        self.query_one("#info-name", Static).update(instance.name)
        self.query_one("#info-address", Static).update(instance.server_address)
        self.query_one("#info-proxy-port", Static).update(str(instance.proxy_port))
        self.query_one("#info-api-port", Static).update(str(instance.api_port))

        status = self.query_one("#info-status", Static)
        status.set_class(instance.running, "running")

        if instance.running:
            status.update("● running")
        else:
            status.update("● stopped")
