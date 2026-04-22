from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Button

from vex_cli.models.pydantic import ProjectCreate
from vex_client.api.project_api import (
    create_project,
    delete_project,
    get_active_project,
    get_all_projects,
    select_project,
    update_project,
)
from vex_client.screens.modals.project_modal import CreateUpdateProjectScreen
from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.project.active_project import ActiveProject
from vex_client.widgets.project.project_table import (
    VexProjectTableContainer,
    VexProjectTable,
)
from vex_client.widgets.table import VexDataTable


class VexProjectsScreen(Screen):
    CSS_PATH = "css/projects.tcss"

    BINDINGS = [
        Binding("c", "create_project", "Create project", show=True, priority=True),
        Binding("d", "delete_project", "Delete project", show=True, priority=True),
        Binding("u", "update_project", "Update project", show=True, priority=True),
        Binding("r", "test", "test", show=True, priority=True),
    ]

    def __init__(self, **kwargs):
        self.first_mount = True
        # parent constructor
        super().__init__(**kwargs)

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def projects_table(self) -> VexProjectTable:
        return self.query_one(VexProjectTable)

    @property
    def active_project(self) -> ActiveProject:
        return self.query_one("#active-project", ActiveProject)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        with Container(id="main-container"):
            #yield ActiveProject(id="active-project")
            # with Horizontal(id="projects-bar"):
            #yield Button("+ Create project", classes="func-btn", id="create-btn")
            yield VexProjectTableContainer(id="projects-table")
            yield Footer(classes="vex-footer")

    async def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.projects_table.set_columns(self.size)
        self.first_mount = False

    async def on_screen_resume(self):
        if self.first_mount:
            return

        self.projects_table.set_loading(True)
        self._fetch_all_projects()
        self._check_active_project()

        self.set_focus(self.projects_table)

    @on(DataTable.RowSelected)
    async def select_project(self, event: DataTable.RowSelected) -> None:
        """
        Select a project and set it as active by calling vex-cli API.
        If successful the is_project_active reactive in VexApp is set to True
        and the rest of the interface becomes active
        """
        app = cast("VexApp", self.app)
        project_id = event.row_key.value

        if project_id is None:
            return

        host, port = app.get_api_info()

        if host is None or port is None:
            return

        project = self.projects_table.get_project(project_id)
        successfully_selected = await select_project(project_id, host, port)

        if successfully_selected and project is not None:
            self.active_project.set_active_project(project.name)
            await app.set_active_project(project)
        else:
            self.notify("Project couldn't be selected", severity="error")

    @work(name="fetch_projects")
    async def _fetch_all_projects(self):
        """
        Worker function that fetches available projects through vex-cli API
        and adds them to the table.
        """
        app = cast("VexApp", self.app)
        host, port = app.get_api_info()
        if host is None or port is None:
            return

        projects = await get_all_projects(host, port)

        for project in projects:
            if self.projects_table.row_exists(str(project.id)):
                continue

            self.projects_table.insert(project)

        self.projects_table.set_loading(False)

    @work(name="check_active_project")
    async def _check_active_project(self):
        """
        Worker function that checks if any project is active,
        if it is then we set it as active project
        """
        app = cast("VexApp", self.app)

        host, port = app.get_api_info()
        if host is None or port is None:
            return

        fetched_active_project = await get_active_project(host, port)

        if fetched_active_project is None:
            return

        # check if already set so we don't do startup/cleanup if it's the same
        active_project = app.get_active_project()
        if active_project and fetched_active_project.id == active_project.id:
            return

        self.active_project.set_active_project(fetched_active_project.name)
        await app.set_active_project(fetched_active_project)

    # ------------- BINDING ACTIONS -----------------

    def action_create_project(self):
        """
        Create a new project by calling vex-cli API.
        If successful add it to the table.
        """

        # callback
        async def create(project_name: str):
            new_project = ProjectCreate(name=project_name)
            host, port = self.app.get_api_info()  # type: ignore
            created_project = await create_project(new_project, host, port)

            if created_project:
                self.projects_table.insert(created_project)
            else:
                self.notify("Error creating project.", severity="error")

        self.app.push_screen(CreateUpdateProjectScreen(None), create)  # type: ignore

    def action_update_project(self):
        """
        Update a project by calling vex-cli API.
        If successful update highlighted in the table.
        """
        selected_project = self.projects_table.get_highlighted_row()
        project_name = ""

        if selected_project is None:
            return

        if len(selected_project) == 4:
            project_name = selected_project[0]

        # callback
        async def update(updated_name: str):
            selected_project_row_key = self.projects_table.get_highlighted_row_key()
            if selected_project_row_key is None:
                return

            project = self.projects_table.get_project(selected_project_row_key)
            if project is None:
                return

            project.name = updated_name

            host, port = self.app.get_api_info()  # type: ignore
            successfully_updated = await update_project(project, host, port)

            if successfully_updated:
                self.projects_table.update_project_row(project)
            else:
                self.notify("Error updating project.", severity="error")

        self.app.push_screen(CreateUpdateProjectScreen(project_name), update)  # type: ignore

    async def action_delete_project(self):
        """
        Delete a project by calling vex-cli API.
        If successful delete highlighted in the table.
        """
        app = cast("VexApp", self.app)
        project_id = self.projects_table.get_highlighted_row_key()

        if project_id is None:
            return

        host, port = app.get_api_info()
        if host is None or port is None:
            return

        is_deleted = await delete_project(project_id, host, port)
        active_project = app.get_active_project()

        if is_deleted:
            self.projects_table.remove_row(project_id)
            self.projects_table.post_message(VexDataTable.RowRemoved())
        else:
            self.notify("Project couldn't be deleted", severity="error")
            return

        if active_project and str(active_project.id) == project_id:
            self.active_project.set_active_project("")
            await app.set_active_project(None)
