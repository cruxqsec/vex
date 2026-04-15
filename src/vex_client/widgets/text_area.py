from textual.widgets import TextArea
from textual.message import Message


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
    
            