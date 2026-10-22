from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmModal(ModalScreen[bool]):
    """Modal that asks a yes/no question and returns a bool."""

    CSS_PATH = "css/confirm.tcss"

    BINDINGS = [
        ("escape", "cancel", "Close"),
    ]

    def __init__(self, question: str, **kwargs):
        self.question = question
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Container(id="confirm-window"):
            yield Label("[b]Confirm action[/b]", id="title")
            yield Label(self.question, id="question-label")
            with Horizontal(id="buttons-row"):
                yield Button("Yes", id="confirm-yes", classes="btn")
                yield Button("\[esc] No", id="confirm-no", classes="btn")

    @on(Button.Pressed, "#confirm-yes")
    def on_yes(self):
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def on_no(self):
        self.dismiss(False)

    def action_cancel(self):
        self.dismiss(False)
