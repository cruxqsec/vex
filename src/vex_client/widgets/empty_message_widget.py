from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label

from vex_client.widgets.center_middle import CenterMiddle

class EmptyStateChanged(Message):
    def __init__(self, is_empty: bool):
        self.is_empty = is_empty
        super().__init__()


class EmptyMessageWidget(Widget, can_focus=False):
    """
    Generic widget that takes another widget and displays an empty message over it.
    """

    DEFAULT_CSS = """
        EmptyMessageWidget {
            layers: below above;
        }

        EmptyMessageWidget.empty {
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
        
        EmptyMessageWidget #empty-message {
            display: none;
        }
    """

    def __init__(self, widget: Widget, empty_message: str, **kwargs):
        self._widget = widget
        self.empty_message = empty_message
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield self._widget
        yield CenterMiddle(Label(self.empty_message), id="empty-message")

    def on_mount(self) -> None:
        self.set_class(True, "empty") 
    
    def on_vex_data_table_focused(self) -> None:
            self.add_class("inner-focused")

    def on_vex_data_table_blurred(self) -> None:
        self.remove_class("inner-focused")

    def on_vex_text_area_focused(self) -> None:
            self.add_class("inner-focused")

    def on_vex_text_area_blurred(self) -> None:
        self.remove_class("inner-focused")

    @on(EmptyStateChanged)
    def empty_state_changed(self, event: EmptyStateChanged):
        self.set_class(event.is_empty, "empty")
