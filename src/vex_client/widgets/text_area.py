from textual import on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, TextArea
from textual.message import Message

from vex_client.widgets.center_middle import CenterMiddle

class VexTextAreaWidget(Widget, can_focus=False):
    """
    Widget that uses the extended VexTextArea and has a message when empty.
    """

    DEFAULT_CSS = """
    VexTextAreaWidget {
        layers: below above;
    }

    VexTextAreaWidget.empty {
        & TextArea {
            layer: below;
        }

        & #empty-message {
            color: $text-muted;
            hatch: right $surface-lighten-1 70%;
            display: block;
            layer: above;
      }
    }
    
    VexTextAreaWidget #empty-message {
        display: none;
    }
    """

    def __init__(self, empty_message: str, **kwargs):
        self.empty_message = empty_message
        self._read_only = kwargs.pop("read_only", False)
        self._tab_behavior = kwargs.pop("tab_behavior", "indent")
        super().__init__(**kwargs)

    def on_mount(self):
        self.update_empty_class()

    def compose(self) -> ComposeResult:
        yield VexTextArea(
            read_only=self._read_only,
            tab_behavior=self._tab_behavior,
        )
        yield CenterMiddle(Label(self.empty_message), id="empty-message")
        
    @on(TextArea.Changed)
    def update_empty(self, event: TextArea.Changed) -> None:
        self.update_empty_class()

    def on_vex_text_area_focused(self) -> None:
        self.add_class("inner-focused")

    def on_vex_text_area_blurred(self) -> None:
        self.remove_class("inner-focused")

    def update_empty_class(self) -> None:
        self.set_class(self.text == "", "empty")

    @property
    def text(self) -> str:
        return self.query_one(TextArea).text

    @text.setter
    def text(self, value: str) -> None:
        self.query_one(TextArea).text = value

    def on_focus(self) -> None:
        self.query_one(VexTextArea).focus()


class VexTextArea(TextArea, can_focus=True):
    """
    Vex text area with VIM keybindings and custom syntax highlight.
    """

    BINDINGS = []
    
    class Focused(Message):
        pass

    class Blurred(Message):
        pass

    def on_focus(self) -> None:
        self.post_message(self.Focused())

    def on_blur(self) -> None:
        self.post_message(self.Blurred())
    
            