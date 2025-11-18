from textual.widget import Widget

class CenterMiddle(Widget, inherit_bindings=False):
    """
    A container which aligns children on both axes.
    Code from Posting.
    """

    DEFAULT_CSS = """
    CenterMiddle {
        align: center middle;
        width: 1fr;
        height: 1fr;
    }
    """
