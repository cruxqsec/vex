import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, cast
from uuid import UUID

if TYPE_CHECKING:
    from vex_client.app import VexApp


from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Static
from textual.widgets.data_table import CellDoesNotExist
from textual_autocomplete import AutoComplete, DropdownItem, TargetState

from vex_cli.models.pydantic import FlowSummary, RequestSummary, ResponseSummary
from vex_client.widgets.empty_message_widget import EmptyMessageWidget
from vex_client.widgets.table import IconColumnCell, SortDirection, VexDataTable

logger = logging.getLogger(__name__)


_SEARCH_PREFIXES = [
    "host:",
    "method:",
    "path:",
    "query:",
    "status:",
    "mime:",
    "title:",
    "ext:",
    "cookie:",
]


class SearchFieldAutoComplete(AutoComplete):
    def get_search_string(self, target_state: TargetState) -> str:
        text_before_cursor = target_state.text[: target_state.cursor_position]
        last_space = text_before_cursor.rfind(" ")
        if last_space == -1:
            return text_before_cursor
        return text_before_cursor[last_space + 1 :]

    def apply_completion(self, value: str, state: TargetState) -> None:
        target = self.target
        text = target.value
        cursor_pos = state.cursor_position
        text_before_cursor = text[:cursor_pos]
        text_after_cursor = text[cursor_pos:]
        last_space = text_before_cursor.rfind(" ")
        if last_space == -1:
            new_text = value + text_after_cursor
            new_cursor = len(value)
        else:
            new_text = text_before_cursor[: last_space + 1] + value + text_after_cursor
            new_cursor = last_space + 1 + len(value)
        with self.prevent(Input.Changed):
            target.value = new_text
            target.cursor_position = new_cursor
        new_target_state = self._get_target_state()
        self._rebuild_options(
            new_target_state, self.get_search_string(new_target_state)
        )


class VexHTTPTableContainer(Vertical):
    def compose(self) -> ComposeResult:
        with Horizontal(id="http-table-header"):
            yield Static("\[/] Search", id="http-search-title")
            search_input = Input(
                placeholder="Enter a query... (host:example.com method:post status:200 string-to-match)",
                id="http-search-bar",
            )
            yield search_input
        yield SearchFieldAutoComplete(
            search_input,
            candidates=[DropdownItem(main=prefix) for prefix in _SEARCH_PREFIXES],
        )
        yield VexHTTPTableEmpty(id="http-table-empty")


class VexHTTPTableEmpty(EmptyMessageWidget):
    """Container that holds VexHTTPTable plus an empty widget"""

    def __init__(self, **kwargs):
        # custom icons for columns
        # brown_style = Style(color=Color.from_rgb(139, 69, 19))
        brown_style = Style(color=Color.from_rgb(181, 101, 29))
        self.has_cookie_column = IconColumnCell(
            Text("󰆘", style=brown_style, justify="right"), "Cookie"
        )
        history_columns = (
            ("#", 3),
            ("Host", 18),
            ("Method", 5),
            ("Path", 18),
            ("Query", 10),
            ("Status", 5),
            ("Size", 7),
            ("Title", 8),
            ("Time(ms)", 8),
            ("Sent at", 12),
            (self.has_cookie_column, 2),
            ("Ext", 3),
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
        # parent constructor
        super().__init__(percent_columns=columns, **kwargs)

    SORT_KEYS: dict[str, Callable[[FlowSummary], Any]] = {
        "#": lambda f: f.id,
        "Host": lambda f: (f.host or "").lower(),
        "Method": lambda f: f.method or "",
        "Path": lambda f: (f.path or "").lower(),
        "Query": lambda f: (f.query or "").lower(),
        "Status": lambda f: f.status_code or -1,
        "Size": lambda f: f.response_size or -1,
        "Title": lambda f: (f.http_title or "").lower(),
        "Time(ms)": lambda f: f.duration_ms or -1,
        "Sent at": lambda f: f.timestamp or 0.0,
        "Cookie": lambda f: bool(f.cookie),
        "Ext": lambda f: (f.file_extension or "").lower(),
    }

    RESPONSE_SORT_KEYS = {"Status", "Size", "Title", "Time(ms)", "Sent at", "Cookie"}

    def sorted_summaries(self, summaries: list[FlowSummary]) -> list[FlowSummary]:
        if self._sort_column_key is None:
            return summaries
        key_func = self.SORT_KEYS.get(self._sort_column_key)
        if key_func is None:
            return summaries
        return sorted(
            summaries,
            key=key_func,
            reverse=self._sort_direction == SortDirection.DESCENDING,
        )

    def on_mount(self) -> None:
        self.watch(self.app, "theme", self._on_app_theme_changed)

    def _on_app_theme_changed(self, theme: str) -> None:
        self.set_loading(True)
        self._recolor_cells()

    def _recolor_cells(self) -> None:
        """Recolor the custom cells on theme change which we display with theme colors."""
        app: VexApp = cast("VexApp", self.app)
        for row_key in self._data:
            flow_id: UUID = UUID(row_key.value)
            if flow_id not in app.history_summary_cache:
                continue

            row: FlowSummary = app.history_summary_cache[flow_id]

            self.update_cell(str(flow_id), "Method", self.render_method(row.method))

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
            return Text(method, justify="right")
        return Text(method, style=self._style_for(component), justify="right")

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

    def render_cookie(self, has_cookie: bool) -> Text:
        if has_cookie:
            return Text("󰸞", style=self._style_for("cookie-yes"), justify="right")
        return Text("", style=self._style_for("cookie-no"), justify="right")

    def time_display(self, timestamp: float) -> Text:
        dt_object = datetime.fromtimestamp(timestamp)
        # Format: HH:MM:SS Day/Month
        return Text(dt_object.strftime("%H:%M:%S %d/%m"), style="italic")

    def insert_request_summary(self, request_summary: RequestSummary) -> None:
        try:
            app: VexApp = cast("VexApp", self.app)
            if self.row_exists(str(request_summary.flow_id)):
                return
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
                None,  # ResponseSummmary field are empty
                request_summary.file_extension,
                key=str(request_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            app.log_vex("Error inserting request into table. Check logs.", "error")
            logger.exception("Error inserting request summary into table")

    def insert_response_summary(self, response_summary: ResponseSummary) -> None:
        flow_id = str(response_summary.flow_id)
        if not self.row_exists(flow_id):
            # row is filtered out; cache holds the update for the next rebuild
            return
        try:
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
                flow_id, "Cookie", self.render_cookie(bool(response_summary.cookie))
            )
        except CellDoesNotExist:
            self.app.log_vex(  # type: ignore
                "Error inserting response summary, could not find corresponding request summary!",
                severity="error",
            )
        except Exception:
            self.app.log_vex("Error updating response in table. Check logs.", "error")  # type: ignore
            logger.exception("Error updating response summary in table")

    def insert_full_summary(self, full_summary: FlowSummary) -> None:
        try:
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
                full_summary.file_extension,
                key=str(full_summary.flow_id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.app.log_vex("Error inserting summary into table. Check logs.", "error")  # type: ignore
            logger.exception("Error inserting full summary into table")

    def get_cell_raw_value(self, column_key: str, row_key: str) -> str | None:
        from uuid import UUID

        app = cast("VexApp", self.app)
        try:
            flow_id = UUID(row_key)
        except ValueError:
            return None
        if flow_id not in app.history_summary_cache:
            return None
        flow = app.history_summary_cache[flow_id]

        match column_key:
            case "#":
                return str(flow.id)
            case "Host":
                return flow.host
            case "Method":
                return flow.method
            case "Path":
                return flow.path
            case "Query":
                return flow.query
            case "Status":
                return str(flow.status_code) if flow.status_code is not None else None
            case "Size":
                return (
                    str(flow.response_size) if flow.response_size is not None else None
                )
            case "Title":
                return flow.http_title
            case "Time(ms)":
                return str(flow.duration_ms) if flow.duration_ms is not None else None
            case "Sent at":
                if flow.timestamp:
                    dt = datetime.fromtimestamp(flow.timestamp)
                    return dt.strftime("%H:%M:%S %d/%m")
                return None
            case "Cookie":
                return flow.cookie
            case "Ext":
                return flow.file_extension
        return None
