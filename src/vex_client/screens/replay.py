from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Select

from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.request_area import RequestArea
from vex_client.widgets.response_area import ResponseArea


class MethodSelect(Select, can_focus=True):
    def __init__(self, **kwargs):
        super().__init__(
            options=[
                ("GET", "GET"),
                ("POST", "POST"),
                ("PUT", "PUT"),
                ("DELETE", "DELETE"),
                ("HEAD", "HEAD"),
                ("PATCH", "PATCH"),
                ("OPTIONS", "OPTIONS"),
            ],
            compact=True,
            **kwargs,
        )


class VexReplayScreen(Screen):
    CSS_PATH = "css/replay.tcss"

    def __init__(self, **kwargs):
        self.is_first_mount = True
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def method_select(self) -> Select:
        return self.query_one("#method-select", Select)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        with Container(id="main-container"):
            with Horizontal(id="send-request-bar"):
                yield MethodSelect(value="GET", id="method-select")
                yield Input(value="https://", id="request-input")
                yield Button("Send", classes="func-btn")
            with Horizontal(id="req-res-area"):
                yield RequestArea(
                    empty_message="No request",
                    read_only=False,
                    tab_behavior="focus",
                    id="request-area",
                )
                yield ResponseArea(
                    empty_message="No response",
                    read_only=True,
                    tab_behavior="focus",
                    id="response-area",
                )
        yield Footer()

    def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
