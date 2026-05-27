from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from vex_client.app import VexApp

from dataclasses import dataclass
from datetime import datetime
from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog

indicators = {
    "info": ("-", "dim"),
    "success": ("+", "green"),
    "warning": ("!", "yellow"),
    "error": ("X", "red"),
}


@dataclass
class LogMessage:
    message: str
    severity: str


class VexLogsPanel(Widget):
    """Logs panel that is displayed when we click the logs button/key."""

    BORDER_TITLE = " Logs "

    @property
    def rich_log(self) -> RichLog:
        return self.query_one("#log-output", RichLog)

    def compose(self) -> ComposeResult:
        yield RichLog(id="log-output", highlight=True, markup=True)

    def on_mount(self) -> None:
        app = cast("VexApp", self.app)
        for log_message in app._log_history:
            self.rich_log.write(self._format(log_message.message, log_message.severity))

    def toggle_panel(self) -> None:
        if "visible" in self.classes:
            self.styles.animate("height", value=0, duration=0.2)
            self.remove_class("visible")
        else:
            self.add_class("visible")
            self.styles.animate("height", value=8, duration=0.2)

    def write_to_log(self, message: str, severity: str = "info") -> None:
        self.rich_log.write(self._format(message, severity))

    @staticmethod
    def _format(message: str, severity: str) -> Text:
        timestamp = datetime.now().strftime("%H:%M:%S")
        symbol, color = indicators.get(severity, ("-", "$text-muted"))

        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append(f"[{symbol}]", style=color)
        text.append(f" {message}")
        return text
