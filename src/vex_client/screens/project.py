from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Vertical, Horizontal, Container, Grid
from textual.widgets import Footer, Button, Label, Input
from textual.widget import Widget
from textual.reactive import reactive
from textual import on, log, work
from textual.worker import Worker

from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.project_table import VexProjectsTable
from vex_client.widgets.search_bar import VexSearchBar

from vex_client.api.project_api import get_all_projects

from datetime import datetime
from uuid import uuid4

class CreateProjectScreen(ModalScreen[str]):
    """Screen with a dialog to create a new project."""

    def compose(self) -> ComposeResult:
        with Container(id="create-modal"):
            yield Label("[b]Create a project[/b]", id="title")
            with Horizontal(id="modal-input"):
                yield Label("Name: ", id="name")
                yield Input(placeholder="My project name", id="input")
            with Horizontal(id="modal-btns"):
                yield Button("Create", classes="func-btn", id="create")
                yield Button("Cancel", classes="func-btn", id="cancel")
                
    @on(Input.Submitted, "#input")
    def on_submit(self, event: Input.Submitted) -> None:
        if event.value != "":
            self.dismiss(event.value)
                
    @on(Button.Pressed, "#create")
    def create_btn(self):
        name_input = self.query_one("#input", Input)
        if name_input.value != "":
            self.dismiss(name_input.value)
           
    @on(Button.Pressed, "#cancel")
    def cancel_btn(self):
        self.app.pop_screen()


class ProjectCreateButton(Button, can_focus=False):
    """
    Button for creating a project
    """

class ActiveProject(Widget):
    
    DEFAULT_CSS = """
        #project-name {
            background: $success-darken-3;
            padding: 0 1;
        }
        
        #status-label {
            background: $background-lighten-2;
            padding: 0 1;
        }
    """
    
    project_name = reactive("")
    
    def set_active_project(self, name: str):
        self.project_name = name
        
    def watch_project_name(self, new_name: str) -> None:
        if self.is_mounted:
            label = self.query_one("#project-name", Label)
            label.update(new_name)
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Active project:", id="status-label")
            yield Label(self.project_name, id="project-name")

class VexProjectsScreen(Screen):
    
    CSS_PATH = "css/projects.tcss"
    
    def __init__(self, **kwargs):
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
            with Horizontal(id="projects-bar"):
                yield VexSearchBar()
                yield ProjectCreateButton("+ Create project", classes="func-btn", id="create-btn")
            yield VexProjectsTable(empty_message="No projects found. Create a new one to start.",
                                   id="projects-table")
        yield Footer(classes="vex-footer")

      
    def set_navigation_btn_color(self) -> None:
        """Sets the corresponding button color of the page"""
        color = self.app.get_css_variables()["primary-darken-3"]
        self.navigation_bar.project_nav_btn.styles.background = color

    @on(Button.Pressed, "#create-btn")
    def create_project_modal(self):
        
        def create_project(project_name: str):
            self.active_project.set_active_project(project_name)
        
        self.app.push_screen(CreateProjectScreen(), create_project) # type: ignore
    
    @work(exclusive=True)
    async def fetch_and_add_projects(self):
        project_table = self.projects_table
        projects = await get_all_projects()
        
        # Get the current datetime
        now = datetime.now()

        # Format: hour:minute day month year
        time_str = now.strftime("%H:%M %d %B %Y")
        
        for project in projects:
            project_table.add_row(project.name, "1MB", time_str, time_str, key=str(project.id))
  
    def on_mount(self):
        self.set_navigation_btn_color()
        
    async def on_screen_resume(self):
        self.fetch_and_add_projects()
