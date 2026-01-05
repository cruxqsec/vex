from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Footer, DataTable
from textual import on, work, log

from vex_client.widgets.bar.navigation_bar import VexNavigationBar
from vex_client.widgets.project.project_table import VexProjectsTable
from vex_client.widgets.project.active_project import ActiveProject
from vex_client.screens.modals.project_modal import CreateUpdateProjectScreen
from vex_client.api.project_api import (
    get_all_projects,
    create_project,
    update_project,
    delete_project,
    select_project,
    get_active_project
)

from vex_cli.models import Project

class VexProjectsScreen(Screen):
    
    CSS_PATH = "css/projects.tcss"
    
    BINDINGS = [
        Binding("c", "create_project", "Create project", show=True, priority=True),
        Binding("d", "delete_project", "Delete project", show=True, priority=True),
        Binding("u", "update_project", "Update project", show=True, priority=True),
        Binding("t", "test_update", "Update project", show=True, priority=True),
    ]
    
    def __init__(self, **kwargs):
        self.first_mount = True
        # parent constructor
        super().__init__(**kwargs)
        
    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)
     
    @property
    def projects_table(self) -> VexProjectsTable:
        return self.query_one("#projects-table", VexProjectsTable)

    @property
    def active_project(self) -> ActiveProject:
        return self.query_one("#active-project", ActiveProject)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar("top", id="navigation-bar")
        with Container(id="main-container"):
            yield ActiveProject(id="active-project")
            #with Horizontal(id="projects-bar"):
                #yield ProjectCreateButton("+ Create project", classes="func-btn", id="create-btn")
            yield VexProjectsTable(cursor_type="row", zebra_stripes=True,id="projects-table")
        yield Footer(classes="vex-footer")
        
    async def on_mount(self):
        self.set_navigation_btn_color()
        self.call_after_refresh(self.projects_table.set_columns)
        self.projects_table.set_loading(True)
        self.call_after_refresh(self.fetch_and_add_projects)
        self.call_after_refresh(self.check_active_project)

        self.first_mount = False
        
    async def on_screen_resume(self):
        if self.first_mount:
            return

        self.projects_table.set_loading(True)
        self.call_after_refresh(self.fetch_and_add_projects)
        self.call_after_refresh(self.check_active_project)
      
    def set_navigation_btn_color(self) -> None:
        """Sets the corresponding button color of the page on mount."""
        color = self.app.get_css_variables()["primary-darken-3"]
        self.navigation_bar.project_nav_btn.styles.background = color

    def action_create_project(self):
        
        async def create(project_name: str):
            new_project = Project(name=project_name) # type: ignore
            host, port = self.app.get_api_info() # type: ignore
            successfully_created = await create_project(new_project, host, port)
            
            if successfully_created:
                self.projects_table.insert(new_project)
                self.projects_table.update_empty_class()
            else:
                self.notify("Error creating project.", severity="error")
        
        self.app.push_screen(CreateUpdateProjectScreen(None), create) # type: ignore
    
    def action_update_project(self):
        
        selected_project = self.projects_table.get_highlighted_row()
        project_name = ""
        
        if selected_project is None:
            return
        
        if len(selected_project) == 4:
            project_name = selected_project[0]
        
        async def update(updated_name: str):
            selected_project_row_key = self.projects_table.get_highlighted_row_key()
            if selected_project_row_key is None:
                return

            project = self.projects_table.get_project(selected_project_row_key)
            if project is None:
                return
            
            project.name = updated_name

            host, port = self.app.get_api_info() # type: ignore
            successfully_updated = await update_project(project, host, port)

            if successfully_updated:
                self.projects_table.update_project_row(project)
            else:
                self.notify("Error updating project.", severity="error")


        self.app.push_screen(CreateUpdateProjectScreen(project_name), update) # type: ignore
        
    async def action_delete_project(self):
        project_id = self.projects_table.get_highlighted_row_key()
        
        if project_id is None:
            return
        
        host, port = self.app.get_api_info() # type: ignore
        is_deleted = await delete_project(project_id, host, port)
        
        app = cast("VexApp", self.app)
        active_project = app.get_active_project()

        if is_deleted:
            self.projects_table.remove_row(project_id)
            self.projects_table.update_empty_class()
        else:
            self.notify("Project couldn't be deleted", severity="error")
            return
        
        if active_project is not None and str(active_project.id) == project_id:
            self.active_project.set_active_project("")
            app.set_active_project(None)

        
    @on(DataTable.RowSelected)
    async def select_project(self, event: DataTable.RowSelected) -> None:
        app = cast("VexApp", self.app)
        host, port = self.app.get_api_info() # type: ignore
        project_id = event.row_key.value
        
        if project_id is None:
            return

        project = self.projects_table.get_project(project_id)
        successfully_selected = await select_project(project_id, host, port)
        
        if successfully_selected and project is not None:
            self.active_project.set_active_project(project.name)
            app.set_active_project(project)
        else:
            self.notify("Project couldn't be selected", severity="error")
    
    @work(name="fetch_projects")
    async def fetch_and_add_projects(self):
        host, port = self.app.get_api_info() # type: ignore
        projects = await get_all_projects(host, port)
        
        for project in projects:
            if self.projects_table.row_exists(str(project.id)):
                continue

            self.projects_table.insert(project)

        self.projects_table.set_loading(False)
        self.projects_table.update_empty_class()
            
    @work(name="check_active_project")
    async def check_active_project(self):
        app = cast("VexApp", self.app)
        
        host, port = self.app.get_api_info() # type: ignore
        active_project = await get_active_project(host, port)
        
        name = active_project.name if active_project is not None else ""
        
        self.active_project.set_active_project(name)
        app.set_active_project(active_project)