from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Footer

from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.history.history_table import VexHTTPTable
from vex_client.widgets.request_area import RequestArea
from vex_client.widgets.response_area import ResponseArea

class VexHTTPHistoryScreen(Screen):
    
    CSS_PATH = "css/http_history.tcss"
    
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
            with Horizontal():
                yield RequestArea(empty_message="Select a row to display the request.",
                                  read_only=True, tab_behavior="focus", id="request-area")
                yield ResponseArea(empty_message="Select a row to display the response",
                                   read_only=True, tab_behavior="focus", id="response-area")
        yield Footer()
           
    def on_mount(self):
        self.set_navigation_btn_color()
        
    def set_navigation_btn_color(self) -> None:
        """Sets the corresponding button color of the page"""
        color = self.app.get_css_variables()["primary-darken-3"]
        self.navigation_bar.history_nav_btn.styles.background = color
