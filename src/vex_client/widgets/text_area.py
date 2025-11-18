from textual.app import ComposeResult
from textual.widgets import TextArea, Label

from vex_client.widgets.center_middle import CenterMiddle


class VexTextArea(TextArea, can_focus=True):
    """
    Custom text area that has an empty message.
    """
    
    DEFAULT_CSS = """
    VexTextArea.empty {
        & #empty-message {
          color: $text-muted;
          hatch: right $surface-lighten-1 70%;
          display: block;
      }
    }
    
    VexTextArea #empty-message {
        display: none;
    }
    """
    

    def __init__(self, empty_message: str, **kwargs):
        self.empty_message = empty_message
        
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        self.set_class(self.text == "", "empty")
        yield CenterMiddle(Label(self.empty_message), id="empty-message")
