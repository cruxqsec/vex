import httpx
import asyncio
from uuid import UUID

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp
    from vex_cli.models.pydantic import FlowSummary, Scope

from textual import on, work
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Input
from textual.widget import Widget

from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.history.table import (
    VexHTTPTable,
    VexHTTPTableContainer,
    VexHTTPTableEmpty,
)
from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.request_area import RequestAreaContainer
from vex_client.widgets.response_area import ResponseAreaContainer
from vex_client.api.raw_api import get_raw_request, get_raw_response
from vex_client.api.summaries_api import delete_flow, delete_all_flows
from vex_client.modals.confirm import ConfirmModal
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel
from vex_client.widgets.table import VexDataTable


class VexHTTPHistoryScreen(Screen):
    CSS_PATH = "http_history.tcss"

    BINDINGS = [
        Binding(
            "ctrl+x",
            "hide_show_req_res_areas",
            "Hide/show request and response area",
            priority=True,
        ),
        Binding(
            "ctrl+z",
            "hide_show_http_table",
            "Hide/show HTTP table",
            priority=True,
        ),
        Binding(
            "/",
            "focus_search",
            "Focus the search bar",
            priority=True,
        ),
        Binding("tab", "focus_next_skip_search", "Focus Next", show=False),
        Binding(
            "shift+tab", "focus_previous_skip_search", "Focus Previous", show=False
        ),
        Binding("d", "delete_selected_entry", "Delete selected entry", priority=True),
        Binding("ctrl+d", "delete_all_entries", "Delete all entries", priority=True),
    ]

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def search_bar(self) -> Input:
        return self.query_one("#http-search-bar", Input)

    @property
    def http_table(self) -> VexHTTPTable:
        return self.query_one(VexHTTPTable)

    @property
    def http_table_empty(self) -> VexHTTPTableEmpty:
        return self.query_one(VexHTTPTableEmpty)

    @property
    def request_area(self) -> VexTextArea:
        return self.query_one("#history-request-area", VexTextArea)

    @property
    def response_area(self) -> VexTextArea:
        return self.query_one("#history-response-area", VexTextArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        yield VexHTTPTableContainer(id="http-table-container")
        with Horizontal(id="text-areas"):
            yield RequestAreaContainer(id="request-area-container")
            yield ResponseAreaContainer(id="response-area-container")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self) -> None:
        self.navigation_bar.set_navigation_btn_color()
        self.http_table.set_columns(self.size)

        # for hiding table/areas
        self._req_res_hidden: bool = False
        self._http_table_hidden: bool = False
        self._selected_summary_uuid: UUID | None = None

        app: VexApp = cast("VexApp", self.app)
        app.history_screen = self
        self.watch(app, "active_scope", self._on_scope_changed, init=False)
        self.populate_table()

    def on_unmount(self) -> None:
        cast("VexApp", self.app).history_screen = None

    def _on_scope_changed(self, scope: "Scope | None") -> None:
        self.populate_table()

    def _filter_by_scope(self, summaries: "list[FlowSummary]") -> "list[FlowSummary]":
        app = cast("VexApp", self.app)
        scope = app.active_scope
        if scope is None:
            return summaries
        if not scope.allow_endpoints and not scope.deny_endpoints:
            return summaries
        filtered = []
        for summary in summaries:
            if summary.host in scope.deny_endpoints:
                continue
            if scope.allow_endpoints and summary.host not in scope.allow_endpoints:
                continue
            filtered.append(summary)
        return filtered

    async def on_screen_resume(self) -> None:
        self.http_table.focus()

    @on(VexDataTable.SortChanged)
    def _on_sort_changed(self, event: VexDataTable.SortChanged) -> None:
        event.stop()
        self._populate_from_sort()

    @work(name="populate_history", exclusive=True, group="populate_history")
    async def _populate_from_sort(self) -> None:
        self.populate_table()

    @work(name="populate_history", exclusive=True, group="populate_history")
    async def populate_table(self) -> None:
        self.http_table_empty.set_loading(True)
        self.http_table.clear_table()
        self.request_area.clear()
        self.response_area.clear()

        summaries = self._filter_by_scope(
            list(cast("VexApp", self.app).history_summary_cache.values())
        )
        summaries = self.http_table.sorted_summaries(summaries)

        BATCH_SIZE = 200
        try:
            self.http_table.begin_bulk_insert()
            for i in range(0, len(summaries), BATCH_SIZE):
                with self.app.batch_update():
                    for summary in summaries[i : i + BATCH_SIZE]:
                        self.http_table.insert_full_summary(summary)
                await asyncio.sleep(0)
        finally:
            self.http_table.end_bulk_insert()
            self.http_table_empty.set_loading(False)

    def reset(self) -> None:
        self.http_table.clear_table()
        self.request_area.clear()
        self.response_area.clear()
        self._selected_summary_uuid = None

    # ------------------ Selecting summaries ---------------

    @on(DataTable.RowSelected)
    async def select_summary(self, event: DataTable.RowSelected) -> None:
        """
        Select a summary and fetch the corresponding raw request/response.
        Then display them in the text areas.
        """
        summary_id = UUID(event.row_key.value)

        if summary_id is None:
            return

        self._selected_summary_uuid = summary_id
        self.fetch_raw_summaries(summary_id)

    @work(name="fetch_raw_summaries", exclusive=True, group="fetch_raw_summaries")
    async def fetch_raw_summaries(self, summary_id: UUID) -> None:
        app = cast("VexApp", self.app)
        host, port = app.get_api_info()

        if host is None or port is None:
            return

        try:
            raw_request = await get_raw_request(summary_id, host, port)
        except httpx.HTTPError:
            app.log_vex("Couldn't fetch request data! Check logs.", severity="error")
            raw_request = None

        try:
            raw_response = await get_raw_response(summary_id, host, port)
        except httpx.HTTPError:
            app.log_vex("Couldn't fetch response data! Check logs.", severity="error")
            raw_response = None

        if raw_request:
            self.request_area.text = raw_request.data.decode("latin-1")
        else:
            app.log_vex("Couldn't fetch request data!", severity="error")
            return

        if raw_response:
            self.response_area.text = (
                raw_response.data.decode("latin-1") if raw_response.data else ""
            )
        else:
            self.response_area.clear()
            app.log_vex("Couldn't fetch response data!", severity="error")

    # -------------- ACTIONS -----------------------

    def action_hide_show_req_res_areas(self) -> None:
        self._req_res_hidden = not self._req_res_hidden
        self.query_one("#text-areas", Horizontal).set_class(
            self._req_res_hidden, "hidden"
        )
        self.http_table.focus()

    def action_hide_show_http_table(self) -> None:
        self._http_table_hidden = not self._http_table_hidden
        self.query_one("#http-table-container", VexHTTPTableContainer).set_class(
            self._http_table_hidden, "hidden"
        )
        self.request_area.focus()

    def action_focus_search(self) -> None:
        self.search_bar.focus()

    # ----------------- Delete logic ------------------------

    def action_delete_selected_entry(self) -> None:
        row_key_str = self.http_table.get_highlighted_row_key()
        if row_key_str is None:
            self.notify("No entry selected", severity="warning")
            return

        app = cast("VexApp", self.app)
        host, port = app.get_api_info()
        if host is None or port is None:
            return

        flow_id = UUID(row_key_str)

        async def do_delete(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                success = await delete_flow(flow_id, host, port)
            except httpx.HTTPError:
                self.notify(
                    "Network error deleting entry. Check logs.", severity="error"
                )
                return
            if success:
                app.history_summary_cache.pop(flow_id, None)
                self.http_table.remove_row(row_key_str)
                if flow_id == self._selected_summary_uuid:
                    self.request_area.clear()
                    self.response_area.clear()
                    self._selected_summary_uuid = None
            else:
                self.notify("Entry couldn't be deleted", severity="error")

        app.push_screen(ConfirmModal("Delete selected entry?"), do_delete)  # type: ignore

    def action_delete_all_entries(self) -> None:
        app = cast("VexApp", self.app)
        host, port = app.get_api_info()
        if host is None or port is None:
            return

        async def do_delete_all(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                success = await delete_all_flows(host, port)
            except httpx.HTTPError:
                self.notify(
                    "Network error deleting entries. Check logs.", severity="error"
                )
                return
            if success:
                app.history_summary_cache.clear()
                self.reset()
            else:
                self.notify("Entries couldn't be deleted", severity="error")

        app.push_screen(ConfirmModal("Delete ALL entries?"), do_delete_all)  # type: ignore

    # ----------------- Focus logic ------------------------

    def action_focus_next_skip_search(self) -> None:
        max_attempts = len(self.screen.focus_chain)
        for _ in range(max_attempts):
            next_widget = self.screen.focus_next()
            if next_widget is None:
                return
            if not self._should_skip_focus(next_widget):
                return

    def action_focus_previous_skip_search(self) -> None:
        max_attempts = len(self.screen.focus_chain)
        for _ in range(max_attempts):
            prev_widget = self.screen.focus_previous()
            if prev_widget is None:
                return
            if not self._should_skip_focus(prev_widget):
                return

    def _should_skip_focus(self, widget: Widget) -> bool:
        if widget.id == "http-search-bar":
            return True
        for ancestor in widget.ancestors_with_self:
            if ancestor.has_class("hidden") or ancestor.has_class("empty"):
                return True
        return False
