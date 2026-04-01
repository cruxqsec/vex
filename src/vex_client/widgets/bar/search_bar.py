from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, Input
from textual_autocomplete import AutoComplete, DropdownItem


class VexSearchBar(Widget):
    DEFAULT_CSS = """
        
        SearchBar {
            height: 1;
            width: 1fr;
            outline: none;
            border: none;
        }
        
        #search-bar {
            width: 10fr;
            padding: 0 1;
            height: 1;
            border: none;
        }
        
        #search-icon {
            width: 1fr;
            height: 1fr;
            background: $surface-darken-2
        }

    """

    def __init__(self, **kwargs):
        self.search_bar = Input(placeholder="Search...", id="search-bar")
        self.auto_complete = AutoComplete(self.search_bar, candidates=[])
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("🔍", id="search-icon", compact=True, disabled=True)
            yield self.search_bar
