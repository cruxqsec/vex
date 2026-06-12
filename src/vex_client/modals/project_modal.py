from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Horizontal, Container
from textual.widgets import Button, Label, Input


class CreateUpdateProjectScreen(ModalScreen[str]):
    """Screen with a dialog to create a new project."""

    CSS_PATH = "css/project_modal.tcss"

    BINDINGS = [
        ("escape", "cancel", "Close"),
        ("ctrl+c", "create", "Create project"),
        ("ctrl+y", "update", "Update project"),
    ]

    def __init__(self, project_name: str | None, **kwargs):
        self.project_name = project_name
        super().__init__(**kwargs)

    @property
    def name_input(self) -> Input:
        return self.query_one("#project-modal-name-input", Input)

    def compose(self) -> ComposeResult:
        with Container(id="modal-window"):
            yield Label("[b]Create a project[/b]", id="title")
            with Horizontal():
                yield Label("Name: ", id="project-modal-name-label")
                yield Input(
                    placeholder="My project name",
                    type="text",
                    max_length=20,
                    id="project-modal-name-input",
                )
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("", classes="btn")
                yield Button("\[esc] Cancel", classes="btn", id="cancel-btn")

    def on_mount(self):
        create_update_btn = self.query("Button").first(Button)
        if self.project_name is not None and self.project_name != "":
            # we are updating the project
            self.query_one("#title", Label).update("[b]Update the project[/b]")
            create_update_btn.label = "\[ctrl+y] Update"
            create_update_btn.id = "update-btn"

            self.name_input.value = self.project_name
        else:
            self.query_one("#title", Label).update("[b]Create a project[/b]")
            create_update_btn.label = "\[ctrl+c] Create"
            create_update_btn.id = "create-btn"

    @on(Input.Blurred)
    def name_input_empty(self, event: Input.Blurred):
        error_label = self.query_one("#error-label", Label)
        if self.name_input.value == "":
            error_label.update("Project name cannot be empty")
        else:
            error_label.update("")

    @on(Button.Pressed, "#update-btn")
    @on(Button.Pressed, "#create-btn")
    def create_btn(self):
        if self.name_input.value == "":
            self.query_one("#error-label", Label).update("Project name cannot be empty")
        else:
            self.dismiss(self.name_input.value)

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self):
        self.app.pop_screen()

    def action_create(self):
        self.create_btn()

    def action_update(self):
        self.create_btn()

    def action_cancel(self):
        self.app.pop_screen()
