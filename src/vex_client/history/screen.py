from uuid import UUID

from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable

from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.history.table import VexHTTPTable, VexHTTPTableContainer
from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.request_area import RequestAreaContainer
from vex_client.widgets.response_area import ResponseAreaContainer
from vex_client.api.raw_api import get_raw_request, get_raw_response
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel


class VexHTTPHistoryScreen(Screen):
    CSS_PATH = "http_history.tcss"

    BINDINGS = [
        Binding(
            "ctrl+x",
            "hide_show_req_res_areas",
            "Hide/show request and response area",
            show=True,
            priority=True,
        ),
        Binding(
            "ctrl+z",
            "hide_show_http_table",
            "Hide/show HTTP table",
            show=True,
            priority=True,
        ),
        Binding(
            "ctrl+b",
            "test",
            "test",
            show=True,
            priority=True,
        ),
    ]

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def http_table(self) -> VexHTTPTable:
        return self.query_one(VexHTTPTable)

    @property
    def request_area(self) -> VexTextArea:
        return self.query_one("#request-area", VexTextArea)

    @property
    def response_area(self) -> VexTextArea:
        return self.query_one("#response-area", VexTextArea)

    def __init__(self, **kwargs) -> None:
        self._req_res_hidden = False
        self._http_table_hidden = False
        # parent constructor
        super().__init__(**kwargs)

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

        app: VexApp = cast("VexApp", self.app)

        app.history_screen = self
        self.populate_table()

    def on_unmount(self) -> None:
        cast("VexApp", self.app).history_screen = None

    async def on_screen_resume(self) -> None:
        self.set_focus(self.http_table)

    def populate_table(self) -> None:
        self.set_loading(True)

        # clear all the areas
        self.http_table.clear_table()
        self.request_area.clear()
        self.response_area.clear()

        for summary in cast("VexApp", self.app).history_summary_cache.values():
            self.http_table.insert_full_summary(summary)

        self.set_loading(False)

    # ------------------ Selecting summaries ---------------

    @on(DataTable.RowSelected)
    async def select_summary(self, event: DataTable.RowSelected) -> None:
        """
        Select a summary and fetch the corresponding raw request/response.
        Then display them in the text areas.
        """
        app = cast("VexApp", self.app)
        summary_id = cast(UUID, event.row_key.value)

        if summary_id is None:
            return

        host, port = app.get_api_info()

        if host is None or port is None:
            return

        raw_request = await get_raw_request(summary_id, host, port)
        raw_response = await get_raw_response(summary_id, host, port)

        if raw_request:
            self.request_area.text = raw_request.data.decode("utf-8")
        else:
            app.log_vex("Couldn't fetch request/response data!", severity="error")

        if raw_response:
            self.response_area.text = (
                raw_response.data.decode("utf-8") if raw_response.data else ""
            )

    # -------------- ACTIONS -----------------------

    def action_hide_show_req_res_areas(self) -> None:
        self._req_res_hidden = not self._req_res_hidden
        self.query_one("#text-areas", Horizontal).set_class(
            self._req_res_hidden, "hidden"
        )

    def action_hide_show_http_table(self) -> None:
        self._http_table_hidden = not self._http_table_hidden
        self.query_one("#http-table-container", VexHTTPTableContainer).set_class(
            self._http_table_hidden, "hidden"
        )
        self.query_one("#text-areas", Horizontal).set_class(
            self._http_table_hidden, "table-hidden"
        )

    def action_test(self) -> None:
        self.log(self.query_one(VexHTTPTableContainer).styles)
