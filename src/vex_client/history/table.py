from uuid import UUID
from datetime import datetime

from rich.text import Text
from rich.style import Style
from rich.color import Color

from textual import on
from textual.widgets import Static, Input
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets.data_table import CellDoesNotExist


from vex_cli.models.pydantic import RequestSummary, ResponseSummary, FlowSummary
from vex_client.widgets.table import VexDataTable, IconColumnCell
from vex_client.widgets.empty_message_widget import EmptyMessageWidget

EXT_TO_ICON = {
    ".js": "",
    ".ts": "",
    ".css": "",
    ".html": "",
    ".json": "",
    ".php": "",
    ".png": "󰸭",
    ".jpg": "󰈥",
    ".svg": "󰜡",
    ".pdf": "󰈦",
}


class VexHTTPTableContainer(Vertical):
    def compose(self) -> ComposeResult:
        with Horizontal(id="http-table-header"):
            yield Static("\[/] Search", id="http-search-title")
            yield Input(id="http-search-bar")
        yield VexHTTPTableEmpty(id="http-table-empty")

class VexHTTPTableEmpty(EmptyMessageWidget):
    """Container that holds VexHTTPTable plus an empty widget"""

    def __init__(self, **kwargs):
        # custom icons for columns
        brown_style = Style(color=Color.from_rgb(139, 69, 19))
        self.has_cookie_column = IconColumnCell(
            Text("󰆘", style=brown_style, justify="right"), "Cookie"
        )
        self.file_extension_column = IconColumnCell(
            Text("󰈔", style="bold white", justify="right"), "Extension"
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
            (self.has_cookie_column, 2),
            (self.file_extension_column, 2),
        )

        self.table = VexHTTPTable(
            cursor_type="row",
            zebra_stripes=True,
            cell_padding=1,
            columns=history_columns,
            id="http-table",
        )
        super().__init__(
            widget=self.table,
            empty_message="Requests proxied through Vex are displayed here.",
            **kwargs,
        )


class VexHTTPTable(VexDataTable, can_focus=True):
    """
    Table containing HTTP information for the corresponding request and response pair.
    """

    COMPONENT_CLASSES = {
        # HTTP methods
        "vex-datatable--method-get",
        "vex-datatable--method-post",
        "vex-datatable--method-put",
        "vex-datatable--method-delete",
        "vex-datatable--method-patch",
        "vex-datatable--method-options",
        "vex-datatable--method-head",
        # Status codes
        "vex-datatable--status-success",  # 2xx
        "vex-datatable--status-redirect",  # 3xx
        "vex-datatable--status-error",  # 4xx / 5xx
        # File extensions
        "vex-datatable--ext-html",
        "vex-datatable--ext-css",
        "vex-datatable--ext-js",
        "vex-datatable--ext-ts",
        "vex-datatable--ext-php",
        "vex-datatable--ext-json",
        "vex-datatable--ext-pdf",
        "vex-datatable--ext-png",
        "vex-datatable--ext-jpg",
        "vex-datatable--ext-svg",
        # Cookie indicator
        "vex-datatable--cookie-yes",
        "vex-datatable--cookie-no",
    }

    def __init__(self, columns: tuple, **kwargs):
        self._row_cache: dict[UUID, FlowSummary] = {}

        # parent constructor
        super().__init__(percent_columns=columns, **kwargs)

    def on_mount(self) -> None:
        self.watch(self.app, "theme", self._on_app_theme_changed)

    def _on_app_theme_changed(self, theme: str) -> None:
        self.set_loading(True)
        self._recolor_cells()
        self.log(self._row_cache)

    def _recolor_cells(self) -> None:
        """Recolor the custom cells on theme change which we display with theme colors."""
        for row_key in self._data:
            flow_id: UUID = UUID(row_key.value)
            if flow_id not in self._row_cache:
                continue

            row: FlowSummary = self._row_cache[flow_id]

            self.update_cell(str(flow_id), "Method", self.render_method(row.method))
            self.update_cell(
                str(flow_id), "Extension", self.render_extension(row.file_extension)
            )

            if row.status_code:
                self.update_cell(
                    str(flow_id), "Status", self.render_status(row.status_code)
                )
            if row.cookie:
                self.update_cell(
                    str(flow_id), "Cookie", self.render_cookie(bool(row.cookie))
                )
        self.set_loading(False)

    def _style_for(self, component: str) -> Style:
        return Style(
            color=self.get_component_rich_style(f"vex-datatable--{component}").color
        )

    def render_method(self, method: str) -> Text:
        component = f"method-{method.lower()}"
        if f"vex-datatable--{component}" not in self.COMPONENT_CLASSES:
            return Text(method, justify="left")
        return Text(method, style=self._style_for(component), justify="left")

    def render_status(self, status: int | None) -> Text:
        if status is None:
            return Text("")
        if 200 <= status < 300:
            component = "status-success"
        elif 300 <= status < 400:
            component = "status-redirect"
        else:
            component = "status-error"
        return Text(str(status), style=self._style_for(component), justify="right")

    def render_extension(self, ext: str | None) -> Text:
        if not ext:
            return Text("󰡯", justify="right")
        component = f"ext-{ext.lower().lstrip('.')}"
        if ext in EXT_TO_ICON:
            return Text(
                EXT_TO_ICON[ext], style=self._style_for(component), justify="right"
            )
        return Text("󰡯", justify="right")

    def render_cookie(self, has_cookie: bool) -> Text:
        if has_cookie:
            return Text("", style=self._style_for("cookie-yes"), justify="right")
        return Text("󰅙", style=self._style_for("cookie-no"), justify="right")

    def time_display(self, timestamp: float) -> Text:
        dt_object = datetime.fromtimestamp(timestamp)
        # Format: HH:MM:SS Day/Month
        return Text(dt_object.strftime("%H:%M:%S %d/%m"), style="italic")

    def clear_table(self) -> None:
        self.clear(columns=False)
        self.post_message(VexDataTable.RowRemoved())

    def insert_request_summary(self, request_summary: RequestSummary) -> None:
        try:
            self._add_to_cache(request_summary)
            self.add_row(
                request_summary.id,
                request_summary.host,
                self.render_method(request_summary.method),
                request_summary.path,
                request_summary.query,
                None,
                None,
                None,
                None,
                None,
                None,  # RequestSummmary field are empty
                self.render_extension(request_summary.file_extension),
                key=str(request_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting summary!", severity="error")

    def insert_response_summary(self, response_summary: ResponseSummary) -> None:
        flow_id = str(response_summary.flow_id)
        try:
            self._add_to_cache(response_summary)
            self.update_cell(
                flow_id, "Status", self.render_status(response_summary.status_code)
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
                flow_id, "Cookies", self.render_cookie(bool(response_summary.cookie))
            )
        except CellDoesNotExist:
            self.notify(
                "Could not find corresponding request summary!", severity="error"
            )
            return

    def insert_full_summary(self, full_summary: FlowSummary) -> None:
        try:
            self._add_to_cache(full_summary)
            self.add_row(
                full_summary.id,
                full_summary.host,
                self.render_method(full_summary.method),
                full_summary.path,
                full_summary.query,
                self.render_status(full_summary.status_code),
                full_summary.response_size,
                full_summary.http_title,
                full_summary.duration_ms,
                self.time_display(full_summary.timestamp),
                self.render_cookie(bool(full_summary.cookie)),
                self.render_extension(full_summary.file_extension),
                key=str(full_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting summary!", severity="error")

    def _add_to_cache(
        self, summary: RequestSummary | ResponseSummary | FlowSummary
    ) -> None:
        if isinstance(summary, RequestSummary):
            self._row_cache[summary.flow_id] = FlowSummary(**summary.model_dump())
        if isinstance(summary, ResponseSummary):
            if summary.flow_id not in self._row_cache:
                unfinished_summary = self._row_cache[summary.flow_id]
                unfinished_summary.status_code = summary.status_code
                unfinished_summary.response_size = summary.response_size
                unfinished_summary.mime = summary.mime
                unfinished_summary.http_title = summary.http_title
                unfinished_summary.cookie = summary.cookie
                unfinished_summary.duration_ms = summary.duration_ms
                unfinished_summary.timestamp = summary.timestamp
        if isinstance(summary, FlowSummary):
            self._row_cache[summary.flow_id] = summary
