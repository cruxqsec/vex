from vex_client.widgets.text_area import VexTextArea


class ResponseArea(VexTextArea, can_focus=True):
    """
    Response area widget used for displaying the raw HTTP response.
    """

    BORDER_TITLE = "Response"
