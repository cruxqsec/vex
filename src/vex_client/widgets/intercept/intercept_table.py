from vex_client.widgets.table import VexDataTable

request_columns = (('#', None), ('Host', 20), ('Method', None), ('Path', 20), ('Query', 10),
                  ("Extension", 9))
response_columns = (('Status', None), ('Response size', None), ('MIME', None), ('Title', 10), 
                   ('Cookies', 7), ('Time', None))


class VexHTTPInterceptTable(VexDataTable, can_focus=True):
    """
    Table containing HTTP information for the corresponding request and response pair.
    """
    
    BORDER_TITLE = "Intercepted requests"
    
    def __init__(self,**kwargs):
        empty_message="Requests proxied through Vex are displayed here."
        # column with percent ration, have to add to 100 for proper display
        intercept_columns = (
            ('#', 5), ('Host', 25), ('Method', 10), ('Path', 25), ('Query', 25),
            ("Extension", 10) 
        )

        # parent constructor
        super().__init__(
            empty_message=empty_message,
            percent_columns=intercept_columns,
            **kwargs
        )
    