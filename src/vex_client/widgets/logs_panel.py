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
        border-top: wide $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="log-output", highlight=True, markup=True)
    
    def toggle_panel(self) -> None:
        if "visible" in self.classes:
            self.styles.animate("height", value=0, duration=0.2)
            self.remove_class("visible")
        else:
            self.add_class("visible")
            self.styles.animate("height", value=10, duration=0.2)

