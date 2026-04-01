from textual.widgets import Button


class NavigationButton(Button, can_focus=False):
    """
    The sidebar button for switching between screens.
    """

    DEFAULT_CSS = """
        NavigationButton {
            text-align: left;
            outline: thick transparent;
            background: $background-lighten-2 !important;
            width: 1fr;
            height: 1fr;
            max-height: 3;
        }    
    """
