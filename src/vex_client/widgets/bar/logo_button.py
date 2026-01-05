from textual.widgets import Button

class LogoButton(Button, can_focus=False):
    """
    Logo button that goes to vex.sh
    """

    DEFAULT_CSS = """
        LogoButton {
            outline: thick transparent;
            background: $error-darken-3 !important;
            width: 1fr;
            height: 1fr;
            max-height: 3;
            max-width: 20;
        }
    """

