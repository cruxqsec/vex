from typing import TYPE_CHECKING, ClassVar, cast
from uuid import UUID

import httpx
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import DataTable, Input


from vex_client.history.query import SearchTerm, filter_summaries, parse_search_query
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

if TYPE_CHECKING:
    from vex_cli.models.pydantic import Scope
    from vex_client.app import VexApp


class VexHistoryScreen(Screen):
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.applied_search: tuple[SearchTerm, ...] = ()
        self._selected_summary_uuid: UUID | None = None
        self._refresh_generation = 0
        self._refresh_pending = False
        self._raw_generation = 0
        self._req_res_hidden = False
        self._http_table_hidden = False

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

    def on_mount(self) -> None:
        self.navigation_bar.set_navigation_btn_color()
        self.http_table.set_columns(self.size)

        self.watch(self.app, "active_scope", self._on_scope_changed, init=False)
        self.http_table_empty.set_loading(
            cast("VexApp", self.app).history_manager.is_loading
        )
        self.request_refresh()

    def invalidate_pending_work(self) -> None:
        """Invalidate callbacks and raw results without changing the visible history."""
        self._refresh_generation += 1
        self._refresh_pending = False
        self._raw_generation += 1
        if self.is_mounted:
            self.workers.cancel_group(self, "fetch_raw_summaries")

    def _clear_selection(self) -> None:
        self._raw_generation += 1
        self._selected_summary_uuid = None
        if self.is_mounted:
            self.workers.cancel_group(self, "fetch_raw_summaries")
            self.request_area.clear()
            self.response_area.clear()

    def clear_screen(self) -> None:
        """Clear deleted history, preserving the applied search and sort."""
        self.invalidate_pending_work()
        self._clear_selection()
        if self.is_mounted:
            self.http_table.synchronize_summaries([])
            self.http_table_empty.set_loading(
                cast("VexApp", self.app).history_manager.is_loading
            )

    def reset_project_view(self) -> None:
        """Reset project-specific UI state, including before the first mount."""
        self.clear_screen()
        self.applied_search = ()
        if self.is_mounted:
            self.search_bar.value = ""
            self.http_table.reset_sort(notify=False)

    def _on_scope_changed(self, scope: "Scope | None") -> None:
        app = cast("VexApp", self.app)
        if app.active_project is None and not app.server_online:
            return
        self.request_refresh()

    def history_loading_changed(self, loading: bool) -> None:
        if not self.is_mounted:
            return
        self.http_table_empty.set_loading(loading)
        app = cast("VexApp", self.app)
        if not loading and app.server_online and app.active_project is not None:
            self.request_refresh()

    @on(Input.Submitted, "#http-search-bar")
    def _on_search_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        try:
            terms = parse_search_query(event.value)
        except ValueError as exc:
            self.notify(str(exc), severity="warning")
            return
        self.applied_search = terms
        self.request_refresh()

    async def on_screen_resume(self) -> None:
        self.http_table.focus()

    @on(VexDataTable.SortChanged)
    def _on_sort_changed(self, event: VexDataTable.SortChanged) -> None:
        event.stop()
        self.request_refresh()

    def request_refresh(self) -> None:
        """Coalesce event bursts into one synchronous reconciliation."""
        if not self.is_mounted or self._refresh_pending:
            return
        self._refresh_pending = True
        self.call_later(self._refresh_table, self._refresh_generation)

    def _refresh_table(self, generation: int) -> None:
        if generation != self._refresh_generation:
            return
        self._refresh_pending = False
        if not self.is_mounted:
            return
        app = cast("VexApp", self.app)
        summaries = filter_summaries(
            app.history_manager.summaries.values(), app.active_scope, self.applied_search
        )
        summaries = self.http_table.sort_items(summaries)
        with self.app.batch_update():
            self.http_table.synchronize_summaries(summaries)
            if self._selected_summary_uuid is not None and not any(
                summary.flow_id == self._selected_summary_uuid for summary in summaries
            ):
                self._clear_selection()
            self.http_table_empty.set_loading(app.history_manager.is_loading)


    # ------------------ Selecting summaries ---------------

    @on(DataTable.RowSelected)
    async def select_summary(self, event: DataTable.RowSelected) -> None:
        """
        Select a summary and fetch the corresponding raw request/response.
        Then display them in the text areas.
        """
        if event.row_key.value is None:
            return
        summary_id = UUID(event.row_key.value)
        if not self.http_table.row_exists(str(summary_id)):
            return

        self._clear_selection()
        self._selected_summary_uuid = summary_id
        self.fetch_raw_summaries(summary_id, self._raw_generation)


    @work(name="fetch_raw_summaries", exclusive=True, group="fetch_raw_summaries")
    async def fetch_raw_summaries(self, summary_id: UUID, generation: int) -> None:
        app = cast("VexApp", self.app)
        api = app.connection_manager.api_client
        project_id = app.active_project.id if app.active_project is not None else None

        def is_current() -> bool:
            return (
                self.is_mounted
                and generation == self._raw_generation
                and summary_id == self._selected_summary_uuid
                and api is app.connection_manager.api_client
                and project_id == (
                    app.active_project.id if app.active_project is not None else None
                )
            )

        if not is_current():
            return
        if api is None:
            self.notify("Connect to the server to load request/response data.", severity="warning")
            return

        request_error = False
        try:
            raw_request = await api.raw.get_raw_request(summary_id)
        except httpx.HTTPError:
            if not is_current():
                return
            app.log_vex(
                "Could not load request data.", "warning", write_to_log=False
            )
            request_error = True
            raw_request = None

        if not is_current():
            return

        response_error = False
        try:
            raw_response = await api.raw.get_raw_response(summary_id)
        except httpx.HTTPError:
            if not is_current():
                return
            app.log_vex(
                "Could not load response data.", "warning", write_to_log=False
            )
            response_error = True
            raw_response = None

        if not is_current():
            return

        if raw_request:
            self.request_area.text = raw_request.data.decode("latin-1")
        else:
            if not request_error:
                app.log_vex(
                    "Could not load request data.", "warning", write_to_log=False
                )

        if raw_response:
            self.response_area.text = (
                raw_response.data.decode("latin-1") if raw_response.data else ""
            )
        else:
            self.response_area.clear()
            if not response_error:
                app.log_vex(
                    "Could not load response data.", "warning", write_to_log=False
                )

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
        if app.connection_manager.api_client is None:
            self.notify("Connect to the server to delete an entry.", severity="warning")
            return

        flow_id = UUID(row_key_str)

        async def do_delete(confirmed: bool) -> None:
            if not confirmed:
                return
            api = app.connection_manager.api_client
            if api is None:
                self.notify("Connect to the server to delete an entry.", severity="warning")
                return
            try:
                success = await api.summaries.delete_flow(flow_id)
            except httpx.HTTPError:
                self.notify("Could not delete entry.", severity="warning")
                return
            if success:
                app.history_manager.remove_summary(flow_id)
                if flow_id == self._selected_summary_uuid:
                    self._clear_selection()
                self.request_refresh()
            else:
                self.notify("Entry couldn't be deleted", severity="error")

        app.push_screen(ConfirmModal("Delete selected entry?"), do_delete)  # type: ignore

    def action_delete_all_entries(self) -> None:
        app = cast("VexApp", self.app)
        if app.connection_manager.api_client is None:
            self.notify("Connect to the server to delete entries.", severity="warning")
            return

        async def do_delete_all(confirmed: bool) -> None:
            if not confirmed:
                return
            api = app.connection_manager.api_client
            if api is None:
                self.notify("Connect to the server to delete entries.", severity="warning")
                return
            try:
                success = await api.summaries.delete_all_flows()
            except httpx.HTTPError:
                self.notify("Could not delete entries.", severity="warning")
                return
            if success:
                app.history_manager.clear_summaries()
                self.clear_screen()
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
