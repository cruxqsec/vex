import uuid
from datetime import datetime

from textual import on
from textual.widgets.data_table import RowDoesNotExist, CellDoesNotExist
from vex_client.widgets.table import VexDataTable
from vex_client.get_size import human_readable, get_directory_size

from vex_cli.models import Project
from vex_cli.locations import vex_projects_directory

class VexProjectsTable(VexDataTable, can_focus=True):
    """
    Table containing project information.
    """
    
    BORDER_TITLE = "Projects"
    
    def __init__(self, **kwargs):
        empty_message = "No projects found. Create a new one to start."
        # column with percent ration, have to add to 100 for proper display
        projects_columns = (('Name', 40), ('Size', 10), 
                            ('Created at', 25), ("Updated at", 25))
        # parent constructor
        super().__init__(
            empty_message=empty_message,
            percent_columns=projects_columns,
            **kwargs
        )
    
    def insert(self, project: Project):
        """Calculate the size of the project directory and insert the row into the table."""
        size = get_directory_size(vex_projects_directory() / str(project.id))

        self.add_row(project.name, human_readable(size), 
                     project.created_at.strftime("%H:%M %d %B %Y"),
                     project.updated_at.strftime("%H:%M %d %B %Y"),
                     key=str(project.id),
        )
    
    def get_project(self, project_id: str) -> Project | None:
        try:
            project_data = self.get_row(project_id) 
        except RowDoesNotExist:
            return None
        
        if len(project_data) != 4:
            return None

        created_at_str = project_data[2]
        updated_at_str = project_data[3]
        
        created_at_dt:datetime = datetime.strptime(created_at_str, "%H:%M %d %B %Y")
        updated_at_dt:datetime = datetime.strptime(created_at_str, "%H:%M %d %B %Y")
        
        project = Project(
            id=uuid.UUID(project_id),
            name=project_data[0],
            # project_data[1] is the size which is calculated on the fly
            created_at=created_at_dt,
            updated_at=updated_at_dt
        )
        
        return project

    def update_project_row(self, project: Project):
        size = get_directory_size(vex_projects_directory() / str(project.id))

        try: 
            self.update_cell(str(project.id), "Name", project.name)
            self.update_cell(str(project.id), "Size", human_readable(size))
            self.update_cell(str(project.id),
                             "Created at", project.created_at.strftime("%H:%M %d %B %Y"))
            self.update_cell(str(project.id),
                             "Updated at", project.updated_at.strftime("%H:%M %d %B %Y"))
        except CellDoesNotExist:
            self.notify("Error updating cells", severity="error")
            return
