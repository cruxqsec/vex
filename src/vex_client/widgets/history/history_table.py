from rich.text import Text
from datetime import datetime
from textual.widgets.data_table import RowDoesNotExist, CellDoesNotExist

from vex_client.widgets.table import VexDataTable
from vex_cli.models import RequestSummary, ResponseSummary

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
            ('#', 4), ('Host', 18), ('Method', 5), ('Path', 18), ('Query', 10),
            ('Status', 5), ('Size', 5), ('Title', 8),
            ('Time(ms)', 8), ('Sent at', 13), ('Cookie', 4), ("Ext", 2),

        )

        # parent constructor
        super().__init__(
            empty_message=empty_message,
            percent_columns=history_columns,
            **kwargs
        )
    
    def cookie_display(self, has_cookie: bool) -> Text:
        if has_cookie:
            return Text("✅", style=self.app.theme_variables['success-darken-3'], justify="right")  
        else:
            return Text("❌", style=self.app.theme_variables['error-darken-3'], justify="right")
    
    def status_display(self, status: int) -> Text:
        style = ""
        if 200 <= status < 300:
            style = self.app.theme_variables["success-darken-3"]
        elif 300 <= status < 400:
            style = self.app.theme_variables["warning-darken-3"]
        else:
            style = self.app.theme_variables["error-darken-3"]
        return Text(str(status), style=style, justify="right")
        
    def time_display(self, timestamp: float) -> Text:
        dt_object = datetime.fromtimestamp(timestamp)
        # Format: HH:MM:SS Day Month Year
        return Text(dt_object.strftime("%H:%M:%S %d %b %Y"), style="italic")
    
    def insert_request_summary(self, request_summary: RequestSummary):
        self.add_row(
            request_summary.id,
            request_summary.host, 
            request_summary.method, 
            request_summary.path, 
            request_summary.query, 
            None,
            None,
            None,
            None,
            None,
            None,
            request_summary.file_extension, 
            key=str(request_summary.flow_id)
        )
        
        self.update_empty_class()
    
    def insert_response_summary(self, response_summary: ResponseSummary):
        flow_id = str(response_summary.flow_id)
        try: 
            self.update_cell(
                flow_id, "Status", self.status_display(response_summary.status_code)
            )
            self.update_cell(
                flow_id, "Size", Text(str(response_summary.response_size), justify="right")
            )
            self.update_cell(
                flow_id, "Title", response_summary.http_title
            )
            self.update_cell(
                flow_id, "Time(ms)", response_summary.duration_ms
            )
            self.update_cell(
                flow_id, "Sent at", self.time_display(response_summary.timestamp)
            )
            self.update_cell(
                flow_id, "Cookies", self.cookie_display(response_summary.has_cookie_set)
            )
        except CellDoesNotExist:
            self.notify("Could not find corresponding request summary!", severity="error")
            return


