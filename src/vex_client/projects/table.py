from datetime import datetime
from typing import Any, Callable, ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
from textual.widgets.data_table import CellDoesNotExist, RowDoesNotExist

from vex_cli.models.pydantic import Project
from vex_client.projects.active_project import ActiveProjectWidget
from vex_client.widgets.button import VexButton
from vex_client.widgets.empty_message_widget import (
    EmptyMessageWidget,
    EmptyStateChanged,
)
from vex_client.widgets.table import VexDataTable


class ProjectButtonRow(Horizontal):
    def compose(self) -> ComposeResult:
        with Horizontal(id="first-button-row"):
            yield VexButton("\[c] Create", id="btn-create", classes="btn")
            yield VexButton("\[e] Edit", id="btn-edit", classes="btn")
            yield VexButton("\[d] Delete", id="btn-delete", classes="btn")
            yield VexButton("\[i] Import", id="btn-import", classes="btn")
            yield VexButton("\[x] Export", id="btn-export", classes="btn")


class VexProjectTableHeader(Horizontal):
    def compose(self) -> ComposeResult:
        yield Static(" PROJECTS ", id="project-table-title")
        yield ActiveProjectWidget(id="active-project-widget")

class VexProjectTableContainer(Vertical):
    def compose(self) -> ComposeResult:
        yield VexProjectTableHeader(id="project-table-header")
        yield VexProjectTableEmpty(id="project-table-empty")
        yield Static("↵ enter to select a project", id="project-table-helper")
        yield ProjectButtonRow(id="button-row")

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

    SORT_KEYS: ClassVar[dict[str, Callable[[Project], Any]]] = {
        "Name": lambda p: p.name.lower(),
        "Created at": lambda p: p.created_at,
        "Updated at": lambda p: p.updated_at,
    }


    def insert(self, project: Project):
        """
        Insert the row with a placeholder size;
        the real size is filled in by the threaded size worker
        """
        try:
            created_at_formated = datetime.fromtimestamp(project.created_at).strftime(
                "%H:%M %d %B %Y"
            )

            updated_at_formated = datetime.fromtimestamp(project.updated_at).strftime(
                "%H:%M %d %B %Y"
            )

            self.add_row(
                project.name,
                "…",
                created_at_formated,
                updated_at_formated,
                key=str(project.id),
            )
            self.post_message(VexDataTable.RowAdded())
        except ValueError:
            self.notify("Error inserting project into table!", severity="error")

    def update_size(self, project_id: str, size_str: str) -> None:
        try:
            self.update_cell(project_id, "Size", size_str)
        except CellDoesNotExist:
            pass

    def get_cell_raw_value(self, column_key: str, row_key: str) -> str | None:
        try:
            row_data = self.get_row(row_key)
        except RowDoesNotExist:
            return None
        col_map = {
            "Name": 0,
            "Size": 1,
            "Created at": 2,
            "Updated at": 3,
        }
        idx = col_map.get(column_key)
        if idx is not None and idx < len(row_data):
            val = row_data[idx]
            return str(val) if val is not None else None
        return None
