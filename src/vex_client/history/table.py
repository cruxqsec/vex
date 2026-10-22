from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, cast
from uuid import UUID

from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, Static
from textual_autocomplete import AutoComplete, DropdownItem, TargetState

from vex_cli.models.pydantic import FlowSummary
from vex_client.history.query import SEARCH_FIELDS
from vex_client.widgets.empty_message_widget import EmptyMessageWidget
from vex_client.widgets.table import IconColumnCell, VexDataTable

if TYPE_CHECKING:
    from vex_client.app import VexApp


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
            yield Static(r"\[/] Search", id="http-search-title")
            search_input = Input(
                placeholder="Enter a query...",
                id="http-search-bar",
            )
            yield search_input
        yield SearchFieldAutoComplete(
            search_input,
            candidates=[DropdownItem(main=f"{prefix}:") for prefix in SEARCH_FIELDS],
        )
        yield VexHTTPTableEmpty(id="http-table-empty")


class VexHTTPTableEmpty(EmptyMessageWidget):
    """Container that holds VexHTTPTable plus an empty widget"""

    def __init__(self, **kwargs):

        brown_style = Style(color=Color.from_rgb(181, 101, 29))
        self.has_cookie_column = IconColumnCell(
            Text("󰆘", style=brown_style, justify="right"), "Cookie"
        )

        history_columns = (
            ("#", 6),
            ("Host", 18),
            ("Method", 5),
            ("Path", 20),
            ("Query", 12),
            ("Status", 5),
            ("Size", 8),

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

    COMPONENT_CLASSES: ClassVar = {
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

        super().__init__(percent_columns=columns, **kwargs)
        self._summaries: dict[str, FlowSummary] = {}

    SORT_KEYS: ClassVar[dict[str, Callable[[FlowSummary], Any]]] = {
        "#": lambda summary: summary.id,
        "Host": lambda summary: summary.host.lower(),
        "Method": lambda summary: summary.method.lower(),
        "Path": lambda summary: summary.path.lower(),
        "Query": lambda summary: (
            summary.query.lower() if summary.query is not None else None
        ),
        "Status": lambda summary: summary.status_code,
        "Size": lambda summary: summary.response_size,
        "Time(ms)": lambda summary: summary.duration_ms,
        "Sent at": lambda summary: summary.timestamp,
        "Cookie": lambda summary: bool(summary.cookie),
        "Ext": lambda summary: (
            summary.file_extension.lower() if summary.file_extension is not None else None
        ),
    }

    def on_mount(self) -> None:
        self.watch(self.app, "theme", self._on_app_theme_changed)

    def _on_app_theme_changed(self, theme: str) -> None:
        self._recolor_cells()

    def _recolor_cells(self) -> None:
        """Force invalidation rather than relying on Rich Text style equality."""
        for row in self.ordered_rows:
            summary = (
                self._summaries.get(row.key.value)
                if row.key.value is not None else None
            )
            if summary is not None:
                for column, value in zip(
                    self.ordered_columns, self.render_summary(summary)
                ):
                    self.update_cell(row.key, column.key, value)

    def _style_for(self, component: str) -> Style:
        return Style(
            color=self.get_component_rich_style(f"vex-datatable--{component}").color
        )

    def render_method(self, method: str) -> Text:
        component = f"method-{method.lower()}"
        if f"vex-datatable--{component}" not in self.COMPONENT_CLASSES:
            return Text(method, justify="left")
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

        return Text(dt_object.strftime("%H:%M:%S %d/%m"), style="italic")

    def render_summary(self, summary: FlowSummary) -> tuple[Any, ...]:
        """Use one cell layout for request-only and completed flows."""
        return (
            summary.id,
            summary.host,
            self.render_method(summary.method),
            summary.path,
            summary.query or "",
            self.render_status(summary.status_code),
            Text(
                "" if summary.response_size is None else str(summary.response_size),
                justify="right",
            ),
            Text(
                "" if summary.duration_ms is None else str(summary.duration_ms),
                justify="right",
            ),
            self.time_display(summary.timestamp)
            if summary.timestamp is not None else Text(""),
            self.render_cookie(bool(summary.cookie)),
            summary.file_extension or "",
        )

    def synchronize_summaries(self, summaries: list[FlowSummary]) -> None:
        """Reconcile rows in supplied order without clearing or fetching details.

        Callers apply filtering and ``sort_items`` before synchronization.
        """
        desired = {str(summary.flow_id): summary for summary in summaries}
        previous_index = self.cursor_row
        highlighted = self.get_highlighted_row_key()
        existing = {row.key.value: row.key for row in self.ordered_rows}
        self.begin_bulk_insert()
        try:
            # Suppress transient highlights caused by removing and moving rows.
            with self.prevent(DataTable.RowHighlighted):
                for flow_id in existing.keys() - desired.keys():
                    self.remove_row(existing[flow_id])
                for flow_id, summary in desired.items():
                    values = self.render_summary(summary)
                    if flow_id not in existing:
                        self.add_row(*values, key=flow_id)
                    else:
                        for column, old, value in zip(
                            self.ordered_columns, self.get_row(flow_id), values
                        ):
                            if old != value:
                                self.update_cell(flow_id, column.key, value)
                self._summaries = desired
                if [row.key.value for row in self.ordered_rows] != list(desired):
                    # The # column contains the unique persisted request id.
                    ranks = {
                        summary.id: index
                        for index, summary in enumerate(desired.values())
                    }
                    self.sort("#", key=ranks.__getitem__)
                if desired:
                    index = (
                        self.get_row_index(highlighted)
                        if highlighted is not None and highlighted in desired
                        else min(previous_index, len(desired) - 1)
                    )
                    self.move_cursor(row=index, animate=False, scroll=False)
        finally:
            self.end_bulk_insert()

    def get_cell_raw_value(self, column_key: str, row_key: str) -> str | None:

        app = cast("VexApp", self.app)
        try:
            flow_id = UUID(row_key)
        except ValueError:
            return None
        if flow_id not in app.history_manager.summaries:
            return None
        flow = app.history_manager.summaries[flow_id]

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
                if flow.timestamp is not None:
                    dt = datetime.fromtimestamp(flow.timestamp)
                    return dt.strftime("%H:%M:%S %d/%m")
                return None
            case "Cookie":
                return flow.cookie
            case "Ext":
                return flow.file_extension
        return None
