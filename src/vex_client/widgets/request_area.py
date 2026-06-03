from vex_client.widgets.text_area import VexTextArea, VexTextAreaWidget
from vex_client.widgets.empty_message_widget import EmptyMessageWidget


class RequestAreaContainer(EmptyMessageWidget):
    """
    Request area widget used for displaying the raw HTTP request.
    """

    def __init__(self, **kwargs):
        self.text_area = VexTextArea(
            read_only=True, tab_behavior="focus", id="request-area"
        )
        self.text_area.cursor_blink = False
        super().__init__(
            widget=VexTextAreaWidget(self.text_area),
            empty_message="[↵ in table] Select a request to display.",
            **kwargs,
        )
