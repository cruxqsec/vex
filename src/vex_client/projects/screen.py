from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Button

from vex_cli.models.pydantic import ProjectCreate, Project
from vex_cli.locations import vex_projects_directory
from vex_client.api.project_api import (
    create_project,
    delete_project,
    get_active_project,
    get_all_projects,
    select_project,
    update_project,
)
from vex_client.modals.project_modal import CreateUpdateProjectScreen
from vex_client.modals.confirm import ConfirmModal
from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.projects.table import (
    VexProjectTableContainer,
    VexProjectTable,
)
from vex_client.projects.active_project import ActiveProjectWidget, ActiveProjectCard
from vex_client.widgets.table import VexDataTable
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel


class VexProjectsScreen(Screen):
    CSS_PATH = "projects.tcss"

    BINDINGS = [
        Binding("c", "create_project", "Create project", priority=True),
        Binding("d", "delete_project", "Delete project", priority=True),
        Binding("e", "update_project", "Update project", priority=True),
        Binding("p", "copy_path", "Copy project path", priority=True),
    ]

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def projects_table(self) -> VexProjectTable:
        return self.query_one("#project-table", VexProjectTable)

    @property
    def active_project_card(self) -> ActiveProjectCard:
        return self.query_one("#active-project-card", ActiveProjectCard)

    def __init__(self, **kwargs):
        # parent constructor
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        with Horizontal(id="main-container"):
            yield VexProjectTableContainer(id="project-table-container")
            yield ActiveProjectWidget(id="active-project-container")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.projects_table.set_columns(self.size)
        self.active_project_card.set_empty()

    async def on_screen_resume(self):
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

        project: Project | None = self.projects_table.get_project(project_id)
        successfully_selected: bool = await select_project(project_id, host, port)

        if successfully_selected and project is not None:
            self.active_project_card.set_project(project.name, "0", "0", "0")
            app.set_active_project(project)
        else:
            self.active_project_card.set_empty()
            self.notify("Project couldn't be selected", severity="error")

    @work(name="fetch_projects", group="fetch_projects", exclusive=True)
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

    @work(name="check_active_project", group="check_active_projects", exclusive=True)
    async def _check_active_project(self):
        """
        Worker function that checks if any project is active,
        if it is then we set it as active project
        """
        app = cast("VexApp", self.app)

        host, port = app.get_api_info()
        if host is None or port is None:
            return

        fetched_active_project: Project | None = await get_active_project(host, port)

        if fetched_active_project is None:
            self.active_project_card.set_empty()
            return

        # check if already set so we don't do startup/cleanup if it's the same
        active_project = app.active_project
        if active_project and fetched_active_project.id == active_project.id:
            return

        self.active_project_card.set_project(fetched_active_project.name, "0", "0", "0")
        app.set_active_project(fetched_active_project)

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
        app = cast("VexApp", self.app)
        project_id = self.projects_table.get_highlighted_row_key()

        if project_id is None:
            return

        host, port = app.get_api_info()
        if host is None or port is None:
            return

        project = self.projects_table.get_project(project_id)
        project_name = project.name if project else "this project"

        async def do_delete(confirmed: bool):
            if not confirmed:
                return

            is_deleted = await delete_project(project_id, host, port)
            active_project = app.active_project

            if is_deleted:
                self.projects_table.remove_row(project_id)
                self.projects_table.post_message(VexDataTable.RowRemoved())
            else:
                self.notify("Project couldn't be deleted", severity="error")
                return
            if active_project and str(active_project.id) == project_id:
                self.active_project_card.set_empty()
                app.set_active_project(None)

        app.push_screen(ConfirmModal(f'Delete project "{project_name}"?'), do_delete) # type: ignore

    def action_copy_path(self):
        try:
            import pyperclip

            app = cast("VexApp", self.app)
            project_id = (
                str(app.active_project.id)
                if app.active_project is not None
                else ""
            )
            pyperclip.copy(str(vex_projects_directory() / project_id))
        except pyperclip.PyperclipException as exc:
            self.notify(
                str(exc),
                title="Clipboard error",
                severity="error",
                timeout=10,
            )
        else:
            self.notify("Project directory path copied to clipboard")

    # ------------- BUTTON ACTIONS -----------------

    @on(Button.Pressed, "#btn-create")
    async def on_create(self, event: Button.Pressed) -> None:
        self.action_create_project()

    @on(Button.Pressed, "#btn-edit")
    async def on_edit(self, event: Button.Pressed) -> None:
        self.action_update_project()

    @on(Button.Pressed, "#btn-delete")
    async def on_delete(self, event: Button.Pressed) -> None:
        await self.action_delete_project()

    @on(Button.Pressed, "#btn-export")
    async def on_export(self, event: Button.Pressed) -> None:
        # TODO: implement project exporting and importing
        pass

    @on(Button.Pressed, "#btn-copy-path")
    async def on_copy_path(self, event: Button.Pressed) -> None:
        self.action_copy_path()