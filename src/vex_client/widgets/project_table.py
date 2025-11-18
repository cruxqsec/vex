from vex_client.widgets.table import VexDataTable

projects_columns = (('Name', 45), ('Size', 10), ('Created at', 30),
                  ("Updated at", 30))

class VexProjectsTable(VexDataTable, can_focus=True):
    """
    Table containing project information.
    """
    
    BORDER_TITLE = "Projects"
    
    def __init__(self, **kwargs):
        # parent constructor
        super().__init__(**kwargs)
        
        for name, width in projects_columns:
            self.add_column(name, width=width)