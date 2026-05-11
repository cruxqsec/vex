from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer

from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.intercept.intercept_table import VexHTTPInterceptTable
from vex_client.widgets.request_area import RequestAreaContainer
from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel


class VexInterceptScreen(Screen):
    CSS_PATH = "css/intercept.tcss"

    def __init__(self, **kwargs):
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def intercept_table(self) -> VexHTTPInterceptTable:
        return self.query_one(VexHTTPInterceptTable)

    @property
    def intercept_req_area(self) -> VexTextArea:
        return self.query_one("#intercept-req-area", VexTextArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        #with Vertical(id="main-container"):
            #yield VexHTTPInterceptTable(id="intercept-table")
        yield VexLogsPanel()
        yield VexFooter()

    def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
