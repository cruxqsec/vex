import asyncio
from typing import TYPE_CHECKING, ClassVar, cast
from uuid import UUID

import httpx

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, DataTable

from vex_cli.locations import vex_projects_directory
from vex_cli.models.pydantic import Project, ProjectCreate
from vex_client.get_size import get_directory_size, human_readable
from vex_client.modals.confirm import ConfirmModal
from vex_client.modals.project_modal import CreateUpdateProjectScreen
from vex_client.projects.active_project import ActiveProjectWidget
from vex_client.projects.table import (
    VexProjectTable,
    VexProjectTableContainer,
)
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.logs_panel import VexLogsPanel
from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.table import VexDataTable


class VexProjectsScreen(Screen):
    CSS_PATH = "projects.tcss"

    BINDINGS: ClassVar = [
        Binding("c", "create_project", "Create project", priority=True),
        Binding("d", "delete_project", "Delete project", priority=True),
        Binding("e", "update_project", "Update project", priority=True),
    ]

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def active_project_widget(self) -> ActiveProjectWidget:
        return self.query_one("#active-project-widget", ActiveProjectWidget)

    @property
    def projects_table(self) -> VexProjectTable:
        return self.query_one("#project-table", VexProjectTable)

    def __init__(self, **kwargs):
        self._projects_cache: dict[UUID, Project] = {}
        # parent constructor
        super().__init__(**kwargs)

    def get_cached_project(self, project_id: str | UUID) -> Project | None:
        """Look up a project in the cache. Table rows alone are display-only."""
        try:
            cache_id = project_id if isinstance(project_id, UUID) else UUID(project_id)
        except ValueError:
            return None
        return self._projects_cache.get(cache_id)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        yield VexProjectTableContainer(id="project-table-container")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.projects_table.set_columns(self.size)
        self.watch(
            self.app,
            "active_project",
            self._render_active_project,
            init=True,
        )

    def _render_active_project(self, project: Project | None) -> None:
        if project is None:
            self.active_project_widget.unset_active_project()
        else:
            self.active_project_widget.set_active_project(project.name)

    def clear_screen(self) -> None:
        """Clears the screen elements."""
        if not self.is_mounted:
            return

        for group in ("fetch_projects", "populate_projects", "project_sizes"):
            self.workers.cancel_group(self, group)

        self._projects_cache.clear()
        self.projects_table.clear_table()
        self.projects_table.set_loading(False)

    async def on_screen_resume(self):
        self._fetch_all_projects()
        app = cast("VexApp", self.app)
        app.refresh_active_project()

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

        api = app.connection_manager.api_client

        if api is None:
            return

        project: Project | None = self.get_cached_project(project_id)
        try:
            successfully_selected: bool = await api.projects.select_project(project_id)
        except httpx.HTTPError:
            self.active_project_widget.unset_active_project()
            self.notify("Could not select project.", severity="warning")
            return

        if successfully_selected and project is not None:
            app.set_project(project)
        else:
            self.notify("Project couldn't be selected", severity="error")

    @work(name="fetch_projects", group="fetch_projects", exclusive=True)
    async def _fetch_all_projects(self):
        """
        Worker function that fetches available projects through vex-cli API,
        updates the cache, and populates the table.
        """
        app = cast("VexApp", self.app)
        api = app.connection_manager.api_client
        if api is None:
            app.log_vex("Cannot load projects: no server info available", "error")
            return

        try:
            fetched_ids: set[UUID] = set()
            skip = 0
            while True:
                batch = await api.projects.get_all_projects(skip=skip, size=50)
                if not batch:
                    break
                for project in batch:
                    self._projects_cache[project.id] = project
                    fetched_ids.add(project.id)
                if len(batch) < 50:
                    break
                skip += 50
        except httpx.HTTPError:
            app.log_vex("Could not load projects.", "warning", write_to_log=False)
            self.projects_table.set_loading(False)
            return

        # server truth wins: drop cache entries for projects deleted elsewhere
        for cached_id in list(self._projects_cache):
            if cached_id not in fetched_ids:
                del self._projects_cache[cached_id]

        self.populate_table()

    @work(name="populate_projects", exclusive=True, group="populate_projects")
    async def populate_table(self) -> None:
        self.projects_table.set_loading(True)
        self.projects_table.clear_table()

        projects = self.projects_table.sort_items(
            list(self._projects_cache.values())
        )

        self.projects_table.begin_bulk_insert()
        for project in projects:
            self.projects_table.insert(project)
        self.projects_table.end_bulk_insert()

        self.projects_table.set_loading(False)
        self._fill_project_sizes()

    @work(name="project_sizes", exclusive=True, group="project_sizes")
    async def _fill_project_sizes(self) -> None:
        """Compute per-project directory sizes in a thread, then update rows."""
        projects_dir = vex_projects_directory()
        projects = list(self._projects_cache.values())

        sizes: dict[UUID, int] = {}
        for project in projects:
            size = await asyncio.to_thread(
                get_directory_size, projects_dir / str(project.id)
            )
            sizes[project.id] = size

        for project_id, size in sizes.items():
            self.projects_table.update_size(str(project_id), human_readable(size))

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
        app = cast("VexApp", self.app)

        # callback
        async def create(project_name: str):
            new_project = ProjectCreate(name=project_name)
            api = self.app.api_client  # type: ignore
            if api is None:
                app.log_vex("Cannot create project: no server info available", "error")
                return
            try:
                created_project = await api.projects.create_project(new_project)
            except httpx.HTTPError:
                self.notify("Could not create project.", severity="warning")
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
        app = cast("VexApp", self.app)
        selected_project_row_key = self.projects_table.get_highlighted_row_key()

        if selected_project_row_key is None:
            return

        project = self.get_cached_project(selected_project_row_key)
        project_name = project.name if project else ""

        # callback
        async def update(updated_name: str):
            project = self.get_cached_project(selected_project_row_key)
            if project is None:
                return

            project.name = updated_name

            api = app.connection_manager.api_client
            if api is None:
                app.log_vex("Cannot update project: no server info available", "error")
                return
            try:
                successfully_updated = await api.projects.update_project(project)
            except httpx.HTTPError:
                self.notify("Could not update project.", severity="warning")
                return

            if successfully_updated:
                self._projects_cache[project.id] = project
                self.populate_table()
            else:
                self.notify("Error updating project.", severity="error")

            if app.active_project and app.active_project.id == project.id:
                app.set_project(project)

        self.app.push_screen(CreateUpdateProjectScreen(project_name), update)  # type: ignore

    async def action_delete_project(self):
        app = cast("VexApp", self.app)
        project_id = self.projects_table.get_highlighted_row_key()

        if project_id is None:
            return

        project = self.get_cached_project(project_id)
        project_name = project.name if project else "this project"

        async def do_delete(confirmed: bool):
            if not confirmed:
                return

            api = app.connection_manager.api_client
            if api is None:
                return
            try:
                is_deleted = await api.projects.delete_project(project_id)
            except httpx.HTTPError:
                self.notify("Could not delete project.", severity="warning")
                return
            active_project = app.active_project

            if is_deleted:
                self._projects_cache.pop(UUID(project_id), None)
                self.populate_table()
            else:
                self.notify("Project couldn't be deleted", severity="error")
                return
            if active_project and str(active_project.id) == project_id:
                app.set_project(None)

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

    @on(Button.Pressed, "#btn-import")
    async def on_import(self, event: Button.Pressed) -> None:
        # TODO: implement project importing
        pass

    @on(Button.Pressed, "#btn-export")
    async def on_export(self, event: Button.Pressed) -> None:
        # TODO: implement project exporting
        pass
