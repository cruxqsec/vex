from textual.widgets import Select

class ScopeSelect(Select, can_focus=False):
    """Select the scope"""

    DEFAULT_CSS = """
        ScopeSelect {
            max-height: 3;
            height: 1fr;
            width: 1fr;
            outline: none !important;

        }

    """
