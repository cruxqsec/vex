from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog


class VexLogsPanel(Widget):
    """Logs panel that is displayed when we click the logs button/key."""

    DEFAULT_CSS = """
    VexLogsPanel {
        dock: bottom;
        height: 20;
        background: $panel;
        display: none;
        offset-y: 0;
    }

    VexLogsPanel.visible {
        display: block;
    }

    #log-output {
        background: $panel;
        border-title-align: left;
        border-top: round $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="log-output", highlight=True, markup=True)
