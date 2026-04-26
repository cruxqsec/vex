from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label
from textual.containers import Horizontal

from vex_client.version import VERSION


class OnlineKey(Widget, can_focus=False):
    """Online display in the footer."""

    DEFAULT_CSS = """
    
    OnlineKey {
        color: $background;
        background: $error;
        height: 1;
        padding: 0 1;
        width: auto;
    }

    OnlineKey .online {
        background: $success;
    }
    
    """

    def compose(self) -> ComposeResult:
        yield Label(" ")

    def on_mount(self) -> None:
        self.query_one(Label).tooltip = "Online: 127.0.0.1:8080:9000"


class CommandPaletteKey(Widget, can_focus=False):
    """Command palette footer button/key."""

    DEFAULT_CSS = """
        CommandPaletteKey {
            background: $panel;
            color: $text-muted;
            width: auto;
            padding: 0 1;
        }
        CommandPaletteKey:hover {
            background: $surface;
        }
    """

    def compose(self) -> ComposeResult:
        yield Label(" Commands")

    def on_click(self) -> None:
        self.app.action_command_palette()


class LogsKey(Widget, can_focus=False):
    """Logs footer button/key."""

    DEFAULT_CSS = """
        LogsKey {
            background: $panel;
            color: $text-muted;
            width: auto;
            padding: 0 1;
        }
        LogsKey:hover {
            background: $surface;
        }
    """

    def compose(self) -> ComposeResult:
        yield Label(" Logs")

    def on_click(self) -> None:
        pass

class VersionKey(Widget, can_focus=False):
    """Version display in the footer."""
    DEFAULT_CSS = """
        VersionKey {
            background: $panel;
            color: $text-muted;
            width: auto;
            padding: 0 1;
        }
        VersionKey:hover {
            background: $surface;
        }
    """

    def compose(self) -> ComposeResult:
        yield Label(f"[bold]v{VERSION}")


class Seperator(Widget, can_focus=False):
    """Simple | seperator in the footer."""
    DEFAULT_CSS = """
        Seperator {
            background: $panel;
            color: $accent;
            width: auto;
        }
    """

    def compose(self) -> ComposeResult:
        yield Label("|")


class VexCmdKey(Widget):
    """Command key (format: key description)."""
    DEFAULT_CSS = """
    VexCmdKey {
        background: $panel;
        layout: horizontal;
        width: auto;
    }

    VexCmdKey .key {
        background: $panel;
        color: $accent;
    }

    VexCmdKey .description {
        padding: 0 1;
        color: $text-muted;
    }
    """

    def __init__(self, key: str, description: str, **kwargs) -> None:
        self.key = key
        self.description = description
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Label(self.key, classes="key")
        yield Label(self.description, classes="description")


class VexFooter(Widget):
    """Custom footer class."""
    DEFAULT_CSS = """
    VexFooter {
        dock: bottom;
        height: 1;
        background: $panel;
        layout: horizontal;
    }

    #left-side {
        dock: left;
        width: auto;
        height: 1;
        margin: 0 !important;
        padding: 0 !important;
    }
    #right-side {
        dock: right;
        width: auto;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="left-side"):
            yield OnlineKey()
            yield CommandPaletteKey()
            yield LogsKey()
        with Horizontal(id="right-side"):
            yield VexCmdKey("f1", "Help")
            yield VexCmdKey("f2", "Settings")
            yield Seperator()
            yield VersionKey()
