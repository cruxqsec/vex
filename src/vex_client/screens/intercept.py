from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Placeholder

from vex_client.widgets.http_table import VexHTTPTable
from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.request_area import RequestArea
from vex_client.widgets.response_area import ResponseArea

class VexInterceptScreen(Screen):
    
    CSS_PATH = "css/intercept.tcss"
    
    def __init__(self, **kwargs):
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)
    
    @property
    def intercept_table(self) -> VexHTTPTable:
        return self.query_one("#intercept-table", VexHTTPTable)
    
    @property
    def intercept_req_area(self) -> RequestArea:
        return self.query_one("#intercept-req-area", RequestArea)
    
    def set_navigation_btn_color(self) -> None:
        """Sets the corresponding button color of the page"""
        color = self.app.get_css_variables()["primary-darken-3"]
        self.navigation_bar.intercept_nav_btn.styles.background = color
     
    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        with Vertical(id="main-container"):
            yield VexHTTPTable("Intercepted requests",
                               display_req=True, display_res=False,
                               empty_message="Intercepted requests will be displayed here.",
                               id="intercept-table")
            yield RequestArea(empty_message="No requests intercepted.",
                              id="intercept-req-area")
        yield Footer()
           
    def on_mount(self):
        self.set_navigation_btn_color()

