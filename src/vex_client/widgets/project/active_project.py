from textual.app import ComposeResult
from textual.containers import  Horizontal
from textual.widgets import Label
from textual.widget import Widget
from textual.reactive import reactive
from textual.widget import Widget

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

