import uuid
from datetime import datetime
from typing import Any, Callable

from textual import on
from textual.app import ComposeResult
from textual.widgets.data_table import CellDoesNotExist, RowDoesNotExist
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from vex_cli.locations import vex_projects_directory
from vex_cli.models.pydantic import Project
from vex_client.get_size import get_directory_size, human_readable
from vex_client.widgets.table import VexDataTable, SortDirection
from vex_client.widgets.empty_message_widget import (
    EmptyMessageWidget,
    EmptyStateChanged,
)
from vex_client.widgets.button import VexButton


class VexProjectTableContainer(Vertical):
    def compose(self) -> ComposeResult:
        with Horizontal(id="project-table-header"):
            yield Static("── Projects ───", id="project-table-title")
            yield VexButton("\[c] Create", id="btn-create", classes="btn")
            yield VexButton("\[e] Edit", id="btn-edit", classes="btn")
            yield VexButton("\[d] Delete", id="btn-delete", classes="btn")
        yield VexProjectTableEmpty(id="project-table-empty")
        yield Static("↵ enter to select a project", id="project-table-helper")

    def on_mount(self) -> None:
        self.query_one("#project-table-helper", Static).add_class("empty")

    @on(EmptyStateChanged)
    def empty_state_changed(self, event: EmptyStateChanged):
        self.query_one("#project-table-helper", Static).set_class(
            event.is_empty, "empty"
        )


class VexProjectTableEmpty(EmptyMessageWidget):
    """Container that holds VexProjectTable and an empty message"""

    def __init__(self, **kwargs):
        self.table = VexProjectTable(
            cursor_type="row", zebra_stripes=True, id="project-table"
        )
        super().__init__(
            widget=self.table,
            empty_message="No projects found. Create a new one to begin.",
            **kwargs,
        )


class VexProjectTable(VexDataTable, can_focus=True):
    """
    Table containing project information.
    """

    def __init__(self, **kwargs):
        # column with percent ration, have to add to 100 for proper display
        projects_columns = (
            ("Name", 20),
            ("Size", 20),
            ("Created at", 30),
            ("Updated at", 30),
        )
        # parent constructor
        super().__init__(percent_columns=projects_columns, **kwargs)

    SORT_KEYS: dict[str, Callable[[Project], Any]] = {
        "Name": lambda p: p.name.lower(),
        "Created at": lambda p: p.created_at,
        "Updated at": lambda p: p.updated_at,
    }

    def sorted_projects(self, projects: list[Project]) -> list[Project]:
        if self._sort_column_key is None:
            return projects
        key_func = self.SORT_KEYS.get(self._sort_column_key)
        if key_func is None:
            return projects
        return sorted(
            projects,
            key=key_func,
            reverse=self._sort_direction == SortDirection.DESCENDING,
        )

    def insert(self, project: Project):
        """Calculate the size of the project directory and insert the row into the table."""
        size = get_directory_size(vex_projects_directory() / str(project.id))
        try:
            self.add_row(
                project.name,
                human_readable(size),
                project.created_at.strftime("%H:%M %d %B %Y"),
                project.updated_at.strftime("%H:%M %d %B %Y"),
                key=str(project.id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting project into table!", severity="error")

    def get_project(self, project_id: str) -> Project | None:
        try:
            project_data = self.get_row(project_id)
        except RowDoesNotExist:
            return None

        if len(project_data) != 4:
            return None

        created_at_tmp: str = project_data[2]
        updated_at_tmp: str = project_data[3]

        created_at: datetime = datetime.strptime(created_at_tmp, "%H:%M %d %B %Y")
        updated_at: datetime = datetime.strptime(updated_at_tmp, "%H:%M %d %B %Y")

        project = Project(
            id=uuid.UUID(project_id),
            name=project_data[0],
            # project_data[1] is the size which is calculated on the fly
            created_at=created_at,
            updated_at=updated_at,
        )

        return project

    def update_project_row(self, project: Project):
        size = get_directory_size(vex_projects_directory() / str(project.id))

        try:
            self.update_cell(str(project.id), "Name", project.name)
            self.update_cell(str(project.id), "Size", human_readable(size))
            self.update_cell(
                str(project.id),
                "Created at",
                project.created_at.strftime("%H:%M %d %B %Y"),
            )
            self.update_cell(
                str(project.id),
                "Updated at",
                project.updated_at.strftime("%H:%M %d %B %Y"),
            )
        except CellDoesNotExist:
            self.notify("Error updating cells!", severity="error")
            return
