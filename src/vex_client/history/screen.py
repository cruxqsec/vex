import asyncio
from typing import TYPE_CHECKING, ClassVar, cast
from uuid import UUID

import httpx

if TYPE_CHECKING:
    from vex_cli.models.pydantic import FlowSummary, Scope
    from vex_client.app import VexApp

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Input

from vex_cli.models.pydantic import RequestSummary, ResponseSummary
from vex_client.history.table import (
    VexHTTPTable,
    VexHTTPTableContainer,
    VexHTTPTableEmpty,
)
from vex_client.modals.confirm import ConfirmModal
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel
from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.request_area import RequestAreaContainer
from vex_client.widgets.response_area import ResponseAreaContainer
from vex_client.widgets.table import VexDataTable
from vex_client.widgets.text_area import VexTextArea

_SEARCH_FIELD_MAP: dict[str, str] = {
    "host": "host",
    "method": "method",
    "path": "path",
    "query": "query",
    "status": "status_code",
    "mime": "mime",
    "title": "http_title",
    "ext": "file_extension",
    "cookie": "cookie",
}


class VexHTTPHistoryScreen(Screen):
    CSS_PATH = "http_history.tcss"

    BINDINGS: ClassVar = [
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

    @on(Input.Submitted, "#http-search-bar")
    def _on_search_submitted(self, event: Input.Submitted) -> None:
        event.stop()
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

    def _parse_query(self, query: str) -> list[tuple[str | None, str]]:
        terms: list[tuple[str | None, str]] = []
        for token in query.split():
            if ":" in token:
                prefix, _, value = token.partition(":")
                prefix_lower = prefix.lower()
                if prefix_lower in _SEARCH_FIELD_MAP and value:
                    terms.append((prefix_lower, value.lower()))
            else:
                terms.append((None, token.lower()))
        return terms

    def _filter_by_search(self, summaries: "list[FlowSummary]") -> "list[FlowSummary]":
        query = self.search_bar.value.strip()
        if not query:
            return summaries
        terms = self._parse_query(query)
        if not terms:
            return summaries
        filtered = []
        for summary in summaries:
            match = True
            for field_prefix, value in terms:
                if field_prefix is not None:
                    field_name = _SEARCH_FIELD_MAP[field_prefix]
                    field_value = getattr(summary, field_name, None)
                    if field_value is None:
                        match = False
                        break
                    if value not in str(field_value).lower():
                        match = False
                        break
                else:
                    found = False
                    for field_name in _SEARCH_FIELD_MAP.values():
                        field_value = getattr(summary, field_name, None)
                        if (
                            field_value is not None
                            and value in str(field_value).lower()
                        ):
                            found = True
                            break
                    if not found:
                        match = False
                        break
            if match:
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
        summaries = self._filter_by_search(summaries)
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

    # ------------------ Live insert path ------------------

    def insert_live_summary(self, message: "RequestSummary | ResponseSummary") -> None:
        """Insert a live WS flow under the current scope/search predicates.

        When a sort is active (or the response updates a response-sorted
        column) the row's position can't be honored by append-only add_row,
        so a full rebuild runs instead, preserving selection.
        """
        app = cast("VexApp", self.app)

        if isinstance(message, RequestSummary):
            flow = app.history_summary_cache.get(message.flow_id)
            if flow is None:
                # cache is guaranteed to contain the flow (inserted by
                # _handle_message just before); defensive only
                return
            if not self._filter_by_scope([flow]) or not self._filter_by_search([flow]):
                return
            if self.http_table.has_active_sort:
                self._rebuild_preserving_selection()
            else:
                self.http_table.insert_request_summary(message)
        else:
            sorted_by_response = (
                self.http_table.has_active_sort
                and self.http_table._sort_column_key
                in self.http_table.RESPONSE_SORT_KEYS
            )
            if sorted_by_response:
                self._rebuild_preserving_selection()
            else:
                self.http_table.insert_response_summary(message)

    @work(
        name="rebuild_preserving_selection",
        exclusive=True,
        group="rebuild_preserving_selection",
    )
    async def _rebuild_preserving_selection(self) -> None:
        """Full repopulate that restores highlight and refetches the raw panes."""
        previous_key = self.http_table.get_highlighted_row_key()
        selected_uuid = self._selected_summary_uuid

        await self.populate_table()

        if previous_key is not None and self.http_table.row_exists(previous_key):
            self.http_table.move_cursor(row=self.http_table.get_row_index(previous_key))
        if selected_uuid is not None and self.http_table.row_exists(str(selected_uuid)):
            self.fetch_raw_summaries(selected_uuid)

    @work(name="fetch_raw_summaries", exclusive=True, group="fetch_raw_summaries")
    async def fetch_raw_summaries(self, summary_id: UUID) -> None:
        app = cast("VexApp", self.app)
        api = app.api_client
        if api is None:
            return

        try:
            raw_request = await api.raw.get_raw_request(summary_id)
        except httpx.HTTPError:
            app.log_vex("Couldn't fetch request data! Check logs.", severity="error")
            raw_request = None

        try:
            raw_response = await api.raw.get_raw_response(summary_id)
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
        if app.api_client is None:
            return

        flow_id = UUID(row_key_str)

        async def do_delete(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                success = await app.api_client.summaries.delete_flow(flow_id)
            except httpx.HTTPError:
                self.notify(
                    "Network error deleting entry. Check logs.", severity="error"
                )
                return
            if success:
                app.history_summary_cache.pop(flow_id, None)
                if self.http_table.row_exists(row_key_str):
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
        if app.api_client is None:
            return

        async def do_delete_all(confirmed: bool) -> None:
            if not confirmed:
                return
            try:
                success = await app.api_client.summaries.delete_all_flows()
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

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "focus_search" and self.search_bar.has_focus:
            return False
        return True

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
