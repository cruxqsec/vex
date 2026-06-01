from vex_client.widgets.text_area import VexTextArea, VexTextAreaWidget
from vex_client.widgets.empty_message_widget import EmptyMessageWidget


class ResponseAreaContainer(EmptyMessageWidget):
    """
    Response area widget used for displaying the raw HTTP response.
    """

    def __init__(self, **kwargs):
        self.text_area = VexTextArea(
            text="", read_only=True, tab_behavior="focus", id="response-area"
        )
        self.text_area.cursor_blink = False
        super().__init__(
            widget=VexTextAreaWidget(self.text_area),
            empty_message="No response to display.",
            **kwargs,
        )
