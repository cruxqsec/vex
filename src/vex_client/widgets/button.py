from textual.widgets import Button

class VexButton(Button, can_focus=False):
    """Non-focusable button"""

    DEFAULT_CLASSES="btn"
