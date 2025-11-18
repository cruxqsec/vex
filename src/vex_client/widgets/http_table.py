from vex_client.widgets.table import VexDataTable

request_columns = (('#', None), ('Host', 20), ('Method', None), ('Path', 20), ('Query', 10),
                  ("Extension", 9))
response_columns = (('Status', None), ('Response size', None), ('MIME', None), ('Title', 10), 
                   ('Cookies', 7), ('Time', None))


class VexHTTPTable(VexDataTable, can_focus=True):
    """
    Table containing HTTP information for the corresponding request and response pair.
    This is used in the HTTP History and Intercept tab.
    """
    
    def __init__(
            self, title: str, 
            display_req : bool = True, 
            display_res: bool = True, 
            **kwargs
        ):
        self.title = title
        self.display_req = display_req
        self.display_res = display_res
                
        # parent constructor
        super().__init__(**kwargs)
    
    def on_mount(self):
        self.border_title = self.title
        
        if self.display_req:
            for name, width in request_columns:
                self.add_column(name, width=width)

        if self.display_res:
            for name, width in response_columns:
                self.add_column(name, width=width)
