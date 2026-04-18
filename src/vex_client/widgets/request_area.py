from vex_client.widgets.text_area import VexTextArea
from vex_client.widgets.empty_message_widget import EmptyMessageWidget


class RequestAreaContainer(EmptyMessageWidget):
    """
    Request area widget used for displaying the raw HTTP request.
    """

    BORDER_TITLE = "Request"

    def __init__(self, **kwargs):
        self.text_area = VexTextArea(
            read_only=True,
            tab_behavior="focus",
        )
        self.text_area.cursor_blink = False
        super().__init__(
            widget=self.text_area,
            empty_message="No request to display.",
            **kwargs
        )

