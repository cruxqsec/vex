from vex_client.widgets.text_area import VexTextArea


class RequestArea(VexTextArea, can_focus=True):
    """
    Request area widget used for displaying the raw HTTP request.
    """

    BORDER_TITLE = "Request"
