from textual.app import ComposeResult
from textual.widgets import DataTable, Label

from vex_client.widgets.center_middle import CenterMiddle


class VexDataTable(DataTable, can_focus=True):
    """
    Custom table with a empty display message
    """
    
    DEFAULT_CSS = """
    VexDataTable.empty {
        & #empty-message {
          color: $text-muted;
          hatch: right $surface-lighten-1 70%;
          display: block;
      }
    }
    
    VexDataTable #empty-message {
        display: none;
    }
    """
    
    BINDINGS = [
        ("k", "cursor_up", "Cursor up"),
        ("j", "cursor_down", "Cursor down"),
        ("l", "cursor_right", "Cursor right"),
        ("h", "cursor_left", "Cursor left"),
        ("ctrl+u", "page_up", "Page up"),
        ("ctrl+f", "page_down", "Page down"),
        ("gg", "scroll_top", "Top"),
        ("G", "scroll_bottom", "Bottom"),
    ]

    def __init__(self, empty_message: str, **kwargs):
        self.empty_message = empty_message
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        self.set_class(self.row_count == 0, "empty")
        yield CenterMiddle(Label(self.empty_message), id="empty-message")
