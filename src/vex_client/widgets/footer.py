from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal

from vex_client.version import VERSION


class OnlineKey(Widget, can_focus=False):
    """Online display in the footer."""

    def compose(self) -> ComposeResult:
        yield Label(" ")

    def on_mount(self) -> None:
        self.query_one(Label).tooltip = "Disconnected"


class CommandPaletteKey(Widget, can_focus=False):
    """Command palette footer button/key."""

    def compose(self) -> ComposeResult:
        yield Label(" Commands")

    def on_click(self) -> None:
        self.app.action_command_palette()


class LogsKey(Widget, can_focus=False):
    """Logs footer button/key."""

    def compose(self) -> ComposeResult:
        yield Label(" Logs")

    def on_click(self) -> None:
        self.app.toggle_logs()  # type: ignore


class VersionKey(Widget, can_focus=False):
    """Version display in the footer."""

    def compose(self) -> ComposeResult:
        yield Label(f"[bold]v{VERSION}")


class Seperator(Widget, can_focus=False):
    """Simple | seperator in the footer."""

    def compose(self) -> ComposeResult:
        yield Label("|")


class VexCmdKey(Widget):
    """Command key (format: key description)."""

    def __init__(self, key: str, description: str, **kwargs) -> None:
        self.key = key
        self.description = description
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Label(self.key, classes="key")
        yield Label(self.description, classes="description")


class VexFooter(Widget):
    """Custom footer class."""

    @property
    def online_key(self) -> OnlineKey:
        return self.query_one(OnlineKey)

    @property
    def logs_key(self) -> LogsKey:
        return self.query_one(LogsKey)

    def compose(self) -> ComposeResult:
        with Horizontal(id="left-side"):
            yield OnlineKey()
            yield CommandPaletteKey()
            yield LogsKey()
        with Horizontal(id="right-side"):
            yield VexCmdKey("f1", "Help")
            yield VexCmdKey("^C", "Proxy screen", id="exit-cmd-key")
            yield Seperator()
            yield VersionKey()

    def on_mount(self) -> None:
        self.watch(self.app, "server_online", self._on_server_online_changed)

    def _on_server_online_changed(self, online: bool) -> None:
        self.online_key.set_class(online, "online")
        self.online_key.tooltip = "Online" if online else "Offline"
