from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Select

from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel


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
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def method_select(self) -> Select:
        return self.query_one("#method-select", Select)

    @property
    def request_area(self) -> VexTextArea:
        return self.query_one("#replay-request-area", VexTextArea)

    @property
    def response_area(self) -> VexTextArea:
        return self.query_one("#replay-response-area", VexTextArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        with Container(id="replay-main-container"):
            with Horizontal(id="send-request-bar"):
                pass
                # yield MethodSelect(value="GET", id="method-select")
                # yield Input(value="https://", id="request-input")
                # yield Button("Send", classes="func-btn")
            with Horizontal(id="req-res-area"):
                pass
        yield VexLogsPanel()
        yield VexFooter()

    def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()

        # app: VexApp = cast("VexApp", self.app)
        # app.populate_log_panel(self)
