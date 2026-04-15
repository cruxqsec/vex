from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.empty_message_widget import EmptyMessageWidget

class ResponseAreaContainer(EmptyMessageWidget):
    """
    Response area widget used for displaying the raw HTTP response.
    """

    BORDER_TITLE = "Response"
    def __init__(self, **kwargs):
        self.table = VexTextArea(
            read_only=True,
            tab_behavior="focus",
        )
        super().__init__(
            widget=self.table,
            empty_message="No response to display.",
            **kwargs
        )

