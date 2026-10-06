from typing import TYPE_CHECKING, cast
from uuid import UUID
import httpx

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Button, Static

from vex_cli.models.pydantic import ProjectCreate, Project
from vex_cli.locations import vex_projects_directory
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
        self._projects_cache: dict[UUID, Project] = {}
        # parent constructor
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        with Horizontal(id="projects-main-container"):
            yield VexProjectTableContainer(id="project-table-container")
            yield ActiveProjectWidget(id="active-project-container")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.projects_table.set_columns(self.size)
        self.active_project_card.set_empty()

    async def on_screen_resume(self):
        # self.projects_table.set_loading(True)
        self._fetch_all_projects()
        self._check_active_project()

        self.set_focus(self.projects_table)

    @on(DataTable.RowSelected)
    async def select_project(self, event: DataTable.RowSelected) -> None:
        """
        Select a project and set it as active by calling vex-cli API.
        If successful the active_project reactive in VexApp is set
        and the rest of the interface becomes active
        """
        app = cast("VexApp", self.app)
        project_id = event.row_key.value

        if project_id is None:
            return

        api = app.api_client

        if api is None:
            return

        project: Project | None = self.projects_table.get_project(project_id)
        try:
            successfully_selected: bool = await api.projects.select_project(project_id)
        except httpx.HTTPError:
            self.active_project_card.set_empty()
            self.notify(
                "Network error selecting project. Check logs.", severity="error"
            )
            return

        if successfully_selected and project is not None:
            self.active_project_card.set_project_name(project.name)
            app.active_project = project
        else:
            self.active_project_card.set_empty()
            self.notify("Project couldn't be selected", severity="error")

    @work(name="fetch_projects", group="fetch_projects", exclusive=True)
    async def _fetch_all_projects(self):
        """
        Worker function that fetches available projects through vex-cli API,
        updates the cache, and populates the table.
        """
        app = cast("VexApp", self.app)
        api = app.api_client
        if api is None:
            app.log_vex("Cannot load projects: no server info available", "error")
            return

        try:
            skip = 0
            while True:
                batch = await api.projects.get_all_projects(skip=skip, size=50)
                if not batch:
                    break
                for project in batch:
                    if project.id not in self._projects_cache:
                        self._projects_cache[project.id] = project
                if len(batch) < 50:
                    break
                skip += 50
        except httpx.HTTPError:
            app.log_vex("Failed to load projects. Check logs.", "error")
            self.projects_table.set_loading(False)
            return

        self.populate_table()

    @work(name="check_active_project", group="check_active_projects", exclusive=True)
    async def _check_active_project(self):
        """
        Worker function that checks if any project is active,
        if it is then we set it as active project
        """
        app = cast("VexApp", self.app)
        api = app.api_client
        if api is None:
            app.log_vex("Cannot check active project: no server info available", "error")
            return

        try:
            fetched_active_project: Project | None = await api.projects.get_active_project()
        except httpx.HTTPError:
            app.log_vex("Failed to check active project. Check logs.", "error")
            return

        if fetched_active_project is None:
            self.active_project_card.set_empty()
            return

        # check if already set so we don't do startup/cleanup if it's the same
        active_project = app.active_project
        if active_project and fetched_active_project.id == active_project.id:
            return

        self.active_project_card.set_project_name(fetched_active_project.name)
        self.fetch_flow_count()
        self.fetch_scope_count()
        app.active_project = fetched_active_project

    @work(name="populate_projects", exclusive=True, group="populate_projects")
    async def populate_table(self) -> None:
        self.projects_table.set_loading(True)
        self.projects_table.clear_table()

        projects = self.projects_table.sorted_projects(
            list(self._projects_cache.values())
        )

        self.projects_table.begin_bulk_insert()
        for project in projects:
            self.projects_table.insert(project)
        self.projects_table.end_bulk_insert()

        self.projects_table.set_loading(False)

    @work(name="flow_count", exclusive=True, group="flow_count")
    async def fetch_flow_count(self) -> None:
        app = cast("VexApp", self.app)
        api = app.api_client
        if api is None:
            app.log_vex("Cannot check active project: no server info available", "error")
            return

        try:
            fetched_flow_count: int = await api.summaries.count_flows()
            self.active_project_card.query_one("#ap-flows", Static).update(str(fetched_flow_count))
        except httpx.HTTPError:
            app.log_vex("Failed to check active project. Check logs.", "error")
            return

    @work(name="scope_count", exclusive=True, group="scope_count")
    async def fetch_scope_count(self) -> None:
        app = cast("VexApp", self.app)
        api = app.api_client
        if api is None:
            app.log_vex("Cannot check active project: no server info available", "error")
            return

        try:
            fetched_scope_count: int = await api.scope.count_scopes()
            self.active_project_card.query_one("#ap-scopes", Static).update(str(fetched_scope_count))
        except httpx.HTTPError:
            app.log_vex("Failed to check active project. Check logs.", "error")
            return

    @on(VexDataTable.SortChanged)
    def _on_sort_changed(self, event: VexDataTable.SortChanged) -> None:
        event.stop()
        self.populate_table()

    # ------------- BINDING ACTIONS -----------------

    def action_create_project(self):
        """
        Create a new project by calling vex-cli API.
        If successful add it to the table.
        """

        # callback
        async def create(project_name: str):
            new_project = ProjectCreate(name=project_name)
            api = self.app.api_client  # type: ignore
            if api is None:
                self.log_vex("Cannot create project: no server info available", "error")
                return
            try:
                created_project = await api.projects.create_project(new_project)
            except httpx.HTTPError:
                self.notify(
                    "Network error creating project. Check logs.", severity="error"
                )
                return

            if created_project:
                self._projects_cache[created_project.id] = created_project
                self.populate_table()
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

            api = self.app.api_client  # type: ignore
            if api is None:
                self.log_vex("Cannot update project: no server info available", "error")
                return
            try:
                successfully_updated = await api.projects.update_project(project)
            except httpx.HTTPError:
                self.notify(
                    "Network error updating project. Check logs.", severity="error"
                )
                return

            if successfully_updated:
                self._projects_cache[project.id] = project
                self.populate_table()
            else:
                self.notify("Error updating project.", severity="error")

        self.app.push_screen(CreateUpdateProjectScreen(project_name), update)  # type: ignore

    async def action_delete_project(self):
        app = cast("VexApp", self.app)
        project_id = self.projects_table.get_highlighted_row_key()

        if project_id is None:
            return

        project = self.projects_table.get_project(project_id)
        project_name = project.name if project else "this project"

        async def do_delete(confirmed: bool):
            if not confirmed:
                return

            api = app.api_client
            if api is None:
                return
            try:
                is_deleted = await api.projects.delete_project(project_id)
            except httpx.HTTPError:
                self.notify(
                    "Network error deleting project. Check logs.", severity="error"
                )
                return
            active_project = app.active_project

            if is_deleted:
                project_uuid = UUID(project_id)
                self._projects_cache.pop(project_uuid, None)
                self.populate_table()
            else:
                self.notify("Project couldn't be deleted", severity="error")
                return
            if active_project and str(active_project.id) == project_id:
                self.active_project_card.set_empty()
                app.active_project = None

        app.push_screen(ConfirmModal(f'Delete project "{project_name}"?'), do_delete)  # type: ignore

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

    