from datetime import datetime

from rich.text import Text
from rich.style import Style
from rich.color import Color
from textual.widgets.data_table import CellDoesNotExist

from vex_cli.models.pydantic import RequestSummary, ResponseSummary, FlowSummary
from vex_client.widgets.table import VexDataTable, IconColumnCell
from vex_client.widgets.empty_message_widget import EmptyMessageWidget

METHOD_STYLES = {
    "GET": "bold bright_green",
    "POST": "bold bright_yellow",
    "PUT": "bold bright_blue",
    "DELETE": "bold bright_red",
    "PATCH": "bold orange3",
    "OPTIONS": "bold grey50",
    "HEAD": "bold cyan",
}

EXT_ICONS = {
    ".js": Text("", style="bold yellow"),
    ".ts": Text("", style="bold blue"),
    ".css": Text("", style="bold red"),
    ".html": Text("", style="bold green"),
    ".json": Text("", style="bold yellow"),
    ".php": Text("", style="bold blue"),
    ".png": Text("󰸭", style="bold blue"),
    ".jpg": Text("󰈥", style="bold blue"),
    ".svg": Text("󰜡", style="bold yellow"),
    ".pdf": Text("󰈦", style="bold red"),
}


class VexHTTPTableContainer(EmptyMessageWidget):
    """Container that holds VexProjectTable"""

    BORDER_TITLE = "HTTP History"

    def __init__(self, **kwargs):
        self.table = VexHTTPTable(cursor_type="row", zebra_stripes=True, cell_padding=1)
        super().__init__(
            widget=self.table,
            empty_message="Requests proxied through Vex are displayed here.",
            **kwargs,
        )


class VexHTTPTable(VexDataTable, can_focus=True):
    """
    Table containing HTTP information for the corresponding request and response pair.
    """

    def __init__(self, **kwargs):
        # column with percent ration, have to add to 100 for proper display
        brown_style = Style(color=Color.from_rgb(139, 69, 19))
        has_cookie_column = IconColumnCell(
            Text("󰆘", style=brown_style), "has_cookie_set"
        )
        file_extension_column = IconColumnCell(
            Text("󰈔", style="bold white"), "file_extension"
        )
        history_columns = (
            ("#", 3),
            ("Host", 18),
            ("Method", 5),
            ("Path", 18),
            ("Query", 15),
            ("Status", 5),
            ("Size", 4),
            ("Title", 8),
            ("Time(ms)", 8),
            ("Sent at", 10),
            (has_cookie_column, 2),
            (file_extension_column, 2),
        )

        # parent constructor
        super().__init__(percent_columns=history_columns, **kwargs)

    def cookie_display(self, has_cookie: bool) -> Text:
        if has_cookie:
            return Text(
                "",  # check
                style=self.app.theme_variables["success-darken-3"],
                # justify="right",
            )
        else:
            return Text(
                "󰅙",  # crossed out
                style=self.app.theme_variables["error-darken-3"],
                # justify="right",
            )

    def status_display(self, status: int | None) -> Text:
        if status is None:
            return Text("")
        style = ""
        if 200 <= status < 300:
            #style = self.app.theme_variables["success-darken-3"]
            style = "bold green"
        elif 300 <= status < 400:
            #style = self.app.theme_variables["warning-darken-3"]
            style = "bold yellow"
        else:
            #style = self.app.theme_variables["error-darken-3"]
            style = "bold red"
        return Text(str(status), style=style, justify="right")

    def time_display(self, timestamp: float) -> Text:
        dt_object = datetime.fromtimestamp(timestamp)
        # Format: HH:MM:SS Day/Month
        return Text(dt_object.strftime("%H:%M:%S %d/%m"), style="italic")

    def method_display(self, method: str) -> Text:
        return Text(method, style=METHOD_STYLES[method])

    def exstension_display(self, exstension: str | None) -> Text:
        if exstension not in EXT_ICONS:
            return Text("󰡯")  # fallback icon
        return EXT_ICONS[exstension]

    def insert_request_summary(self, request_summary: RequestSummary) -> None:
        try:
            self.add_row(
                request_summary.id,
                request_summary.host,
                self.method_display(request_summary.method),
                request_summary.path,
                request_summary.query,
                None,
                None,
                None,
                None,
                None,
                None,
                self.exstension_display(request_summary.file_extension),
                key=str(request_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting summary!", severity="error")

    def insert_response_summary(self, response_summary: ResponseSummary) -> None:
        flow_id = str(response_summary.flow_id)
        try:
            self.update_cell(
                flow_id, "Status", self.status_display(response_summary.status_code)
            )
            self.update_cell(
                flow_id,
                "Size",
                Text(str(response_summary.response_size), justify="right"),
            )
            self.update_cell(flow_id, "Title", response_summary.http_title)
            self.update_cell(flow_id, "Time(ms)", response_summary.duration_ms)
            self.update_cell(
                flow_id, "Sent at", self.time_display(response_summary.timestamp)
            )
            self.update_cell(
                flow_id, "Cookies", self.cookie_display(response_summary.has_cookie_set)
            )
        except CellDoesNotExist:
            self.notify(
                "Could not find corresponding request summary!", severity="error"
            )
            return

    def insert_full_summary(self, full_summary: FlowSummary) -> None:
        try:
            self.add_row(
                full_summary.id,
                full_summary.host,
                self.method_display(full_summary.method),
                full_summary.path,
                full_summary.query,
                self.status_display(full_summary.status_code),
                full_summary.response_size,
                full_summary.http_title,
                full_summary.duration_ms,
                self.time_display(full_summary.timestamp),
                self.cookie_display(True if full_summary.has_cookie_set else False),
                self.exstension_display(full_summary.file_extension),
                key=str(full_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting summary!", severity="error")
