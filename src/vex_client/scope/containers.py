from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    ListView,
    TextArea,
)

from vex_client.widgets.text_area import VexTextArea

class ScopeInputWidget(Widget, can_focus=False):
    BORDER_TITLE = "Name"

    def on_compose(self) -> ComposeResult:
        self.scope_input = Input(placeholder="Scope name...")
        yield self.scope_input


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

