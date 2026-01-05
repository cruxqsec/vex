from vex_client.widgets.table import VexDataTable

request_columns = (('#', None), ('Host', 20), ('Method', None), ('Path', 20), ('Query', 10),
                  ("Extension", 9))
response_columns = (('Status', None), ('Response size', None), ('MIME', None), ('Title', 10), 
                   ('Cookies', 7), ('Time', None))


class VexHTTPTable(VexDataTable, can_focus=True):
    """
    Table containing HTTP information for the corresponding request and response pair.
    """
    
    BORDER_TITLE = "HTTP History"
    
    def __init__(self,**kwargs):
        empty_message="Requests proxied through Vex are displayed here."
        # column with percent ration, have to add to 100 for proper display
        history_columns = (
            ('#', 5), ('Host', 20), ('Method', 5), ('Path', 20), ('Query', 10),
            ("Extension", 5), ('Status', 5), ('Response size', 10), ('MIME', 5),
            ('Title', 5), ('Cookies', 5), ('Time', 5)
        )

        # parent constructor
        super().__init__(
            empty_message=empty_message,
            percent_columns=history_columns,
            **kwargs
        )
    