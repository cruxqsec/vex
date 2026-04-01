import asyncio
import json
from typing import TYPE_CHECKING, cast

import websockets
from pydantic import ValidationError
from websockets.exceptions import ConnectionClosed

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import work
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer

from vex_cli.models.pydantic import RequestSummary, ResponseSummary
from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.history.history_table import VexHTTPTable
from vex_client.widgets.request_area import RequestArea
from vex_client.widgets.response_area import ResponseArea


class VexHTTPHistoryScreen(Screen):
    CSS_PATH = "css/http_history.tcss"

    BINDINGS = [
        # Binding("c", "get_table", "Get table columns", show=True, priority=True),
    ]

    def __init__(self, **kwargs):
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def http_table(self) -> VexHTTPTable:
        return self.query_one("#http-table", VexHTTPTable)

    @property
    def request_area(self) -> RequestArea:
        return self.query_one("#request-area", RequestArea)

    @property
    def response_area(self) -> ResponseArea:
        return self.query_one("#response-area", ResponseArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        with Container(id="main-container"):
            yield VexHTTPTable(cursor_type="row", zebra_stripes=True, id="http-table")
            # with Horizontal():
            #    yield RequestArea(empty_message="Select a row to display the request.",
            #                      read_only=True, tab_behavior="focus", id="request-area")
            #    yield ResponseArea(empty_message="Select a row to display the response",
            #                       read_only=True, tab_behavior="focus", id="response-area")
        yield Footer()

    def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.call_after_refresh(self.http_table.set_columns)
        self.history_websocket_manager()

    def parse_summary_message(self, raw_data: str):
        data = json.loads(raw_data)

        if "host" in data:
            return RequestSummary.model_validate(data)
        if "status_code" in data:
            return ResponseSummary.model_validate(data)

    @work(name="history_manager", exclusive=True)
    async def history_websocket_manager(self):
        app = cast("VexApp", self.app)

        self.notify("History manager started")
        while True:
            await app.is_project_active_event.wait()  # waits if not set (cleared)
            await self.handle_history_connection()

            self.notify(
                "History websocket reconnecting in 5 seconds!", severity="warning"
            )
            await asyncio.sleep(5)  # so we don't spam the server

    async def handle_history_connection(self):
        """Connects to vex-cli websocket and processes messages (summaries)"""
        app = cast("VexApp", self.app)
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
                    try:
                        # This parses the JSON AND validates the structure in one step
                        message = self.parse_summary_message(str(raw_message))

                        if isinstance(message, RequestSummary):
                            self.http_table.insert_request_summary(message)
                        elif isinstance(message, ResponseSummary):
                            self.http_table.insert_response_summary(message)

                    except ValidationError as e:
                        self.notify(f"Received invalid JSON structure: {e}")
                    except json.JSONDecodeError:
                        self.notify("Received data that wasn't even JSON!")
        except ConnectionClosed:
            self.notify("Server closed connection. Retrying in 5s...")

        except Exception as e:
            self.notify(f"Unexpected error: {e}")
