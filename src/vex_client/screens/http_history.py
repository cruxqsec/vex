import asyncio
import json
from typing import TYPE_CHECKING, cast

import websockets
from pydantic import ValidationError

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import work
from textual.binding import Binding
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Button

from vex_cli.models.pydantic import RequestSummary, ResponseSummary, FlowSummary
from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.history.history_table import VexHTTPTable, VexHTTPTableContainer
from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.request_area import RequestAreaContainer
from vex_client.widgets.response_area import ResponseAreaContainer
from vex_client.api.summaries_api import get_all_summaries
from vex_client.api.raw_api import get_raw_request, get_raw_response


class VexHTTPHistoryScreen(Screen):
    CSS_PATH = "css/http_history.tcss"

    BINDINGS = [
        Binding(
            "x",
            "hide_show_req_res_areas",
            "Hide/show request and response area",
            show=True,
            priority=True,
        ),
    ]

    def __init__(self, **kwargs) -> None:
        self.hidden = True;
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def http_table(self) -> VexHTTPTable:
        return self.query_one(VexHTTPTable)

    # TODO: determine the specific
    @property
    def request_area(self) -> VexTextArea:
        return self.query_one(VexTextArea)

    # TODO: determine the specific
    @property
    def response_area(self) -> VexTextArea:
        return self.query_one(VexTextArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        yield VexHTTPTableContainer(id="http-table")
        with Horizontal(id="text-areas"):
            yield RequestAreaContainer(id="request-area")
            yield ResponseAreaContainer(id="response-area")
        yield Footer()

    def on_mount(self) -> None:
        self.navigation_bar.set_navigation_btn_color()
        self.http_table.set_columns(self.size)
        self._history_websocket_manager()

    async def on_screen_resume(self) -> None:
        self.set_focus(self.http_table)

    def parse_summary_message(self, raw_data: str) -> RequestSummary | ResponseSummary:
        data = json.loads(raw_data)
        try:
            return RequestSummary.model_validate(data)
        except ValidationError:
            return ResponseSummary.model_validate(data)

    @work(exclusive=True)
    async def fetch_all_summaries(self) -> None:
        """
        Worker function that fetches all summaries of a project
        through vex-cli API and adds them to the table.
        """
        app: VexApp = cast("VexApp", self.app)
        host, port = app.get_api_info()
        skip: int = 0

        if host is None or port is None:
            return

        while True:
            full_summaries: list[FlowSummary] = await get_all_summaries(
                host, port, skip, 50
            )

            if not full_summaries:
                break

            for summary in full_summaries:
                if self.http_table.row_exists(str(summary.flow_id)):
                    self.notify(f"Row with key {summary.flow_id} exists")
                    continue

                self.http_table.insert_full_summary(summary)

            skip += 50

    @work(name="history_manager", exclusive=True)
    async def _history_websocket_manager(self) -> None:
        app: VexApp = cast("VexApp", self.app)

        while True:
            await app.is_project_active_event.wait()  # waits if not set (cleared)
            self.notify("History manager activated")
            await self._handle_history_connection()
            await asyncio.sleep(5)  # so we don't spam the server

    async def _handle_history_connection(self) -> None:
        """Connects to vex-cli websocket and processes messages (summaries)"""
        app: VexApp = cast("VexApp", self.app)
        host, port = app.get_api_info()

        if host is None or port is None:
            return

        self.uri = f"ws://{host}:{port}/ws/history"

        try:
            async with websockets.connect(self.uri) as websocket:
                self.notify("Connection to websocket successful!")
                async for raw_message in websocket:
                    if not app.is_project_active_event.is_set():
                        # skips processing but keeps loop/connection alive
                        continue
                    self._handle_message(raw_message)
        except Exception as e:
            self.notify(f"Unexpected error: {e}")

    def _handle_message(self, raw_message: websockets.Data) -> None:
        try:
            message = self.parse_summary_message(str(raw_message))

            if isinstance(message, RequestSummary):
                self.http_table.insert_request_summary(message)
            elif isinstance(message, ResponseSummary):
                self.http_table.insert_response_summary(message)

        except ValidationError as e:
            self.notify(f"Received invalid JSON structure: {e}")
        except json.JSONDecodeError:
            self.notify("Received data that wasn't even JSON!")

    # -------------- ACTIONS -----------------------

    def action_hide_show_req_res_areas(self) -> None:
        self.hidden = not self.hidden
        self.query_one("#text-areas", Horizontal).set_class(self.hidden, "empty")