from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    ListItem,
    ListView,
    Static,
    TextArea,
)

from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel


class ScopeInput(Input, can_focus=True):
    """
    Input for the scope name
    """

    BORDER_TITLE = "Name"


class InScopeArea(TextArea, can_focus=True):
    """
    TextArea for the user to input in scope domains, ips, etc.
    """

    BORDER_TITLE = "In Scope"


class OutOfScopeArea(TextArea, can_focus=True):
    """
    TextArea for the user to input in out of scope domains, ips, etc.
    """

    BORDER_TITLE = "Out of Scope"


class ScopeButton(Button, can_focus=False):
    """
    Buttons for saving, deleting and duplicating scopes
    """


class ScopeList(ListView, can_focus=True):
    """
    ListView for displaying the scopes
    """

    BORDER_TITLE = "Scopes"


class VexScopeScreen(Screen):
    CSS_PATH = "css/scope.tcss"

    def __init__(self, **kwargs):
        self.is_first_mount = True
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def scope_list(self) -> ScopeList:
        return self.query_one("#scope-list", ScopeList)

    @property
    def name_input(self) -> Input:
        return self.query_one("#name-input", Input)

    @property
    def in_scope_area(self) -> InScopeArea:
        return self.query_one("#in-scope-area", InScopeArea)

    @property
    def out_of_scope_area(self) -> OutOfScopeArea:
        return self.query_one("#out-of-scope-area", OutOfScopeArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        with Horizontal(id="main-container"):
            yield ScopeList(ListItem(Static("Test preset")), id="scope-list")
            with Vertical(id="in-out-container"):
                yield ScopeInput(placeholder="Scope name...", id="name-input")
                with Horizontal():
                    yield InScopeArea(
                        placeholder="Add a domain, IP, one per line...",
                        id="in-scope-area",
                    )
                    yield OutOfScopeArea(
                        placeholder="Add a domain, IP, one per line...",
                        id="out-of-scope-area",
                    )
                with Horizontal(id="btn-area"):
                    yield ScopeButton("Save", classes="func-btn")
                    yield ScopeButton("Duplicate", classes="func-btn")
                    yield ScopeButton("Delete", classes="func-btn")
        yield VexLogsPanel()
        yield VexFooter()

    def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
