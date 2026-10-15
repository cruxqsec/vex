from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class ActiveProjectWidget(Horizontal):
    """Widget that displays a dot and an active project name."""

    @property
    def active_project_name(self) -> Static:
        return self.query_one("#active-project-name", Static)

    @property
    def active_project_dot(self) -> Static:
        return self.query_one("#active-project-dot", Static)

    def compose(self) -> ComposeResult:
        yield Static("●", id="active-project-dot")
        yield Static("No project active", id="active-project-name")

    def set_active_project(self, name: str) -> None:
        self.active_project_dot.set_class(True, "active")
        self.active_project_name.update(name)

    def unset_active_project(self) -> None:
        self.active_project_dot.set_class(False, "active")
        self.active_project_name.update("No project active")
