from textual.app import ComposeResult
from textual.widgets import Button
from textual.widget import Widget

from textual import log

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

class InterceptButton(Button, can_focus = False):
    """
    Button for interception. Can be in 2 states. Forwarding and intercepting.
    """
    
    DEFAULT_CSS = """
    
        InterceptButton {
            width: 1fr;
            height: 1fr;
            max-height: 3;
            max-width: 20;
            background: $background !important;
            outline: round $success;
            color: $success !important;

            &:hover {
                background: transparent !important;
                tint: $background 0%;
            }
        }
        
        InterceptButton.intercepting {
            outline: round $error;
            background: $background;
            color: $error !important;
            text-opacity: 0.8;
            
            &:hover {
                background: transparent !important;
                tint: $background 0%;
            }

        }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_active = True
        self.toggle() # Toggle it to be forwarding by default
    
    def toggle(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.add_class("intercepting")
            self.label = "⏸ Intercepting"
        else:
            self.remove_class("intercepting")
            self.label = "⏩ Forwarding"
        
    def on_button_pressed(self):
        self.toggle()

class NavigationButton(Button, can_focus=False):
    """
        The sidebar button for switching between screens.
    """

class VexNavigationBar(Widget):
    
    DEFAULT_CSS = """
    
        VexNavigationBar.top {
            layout: horizontal;
            dock: top;
            width: 1fr;
            height: 1fr;
            max-height: 3;
            InterceptButton {
                offset-x: 0.5fr;
            }
        }
    
        VexNavigationBar.bottom {
            layout: horizontal;
            dock: bottom;
            width: 1fr;
            height: 1fr;
            max-height: 3;
            InterceptButton {
                offset-x: 0.5fr;
            }

        }
        
        VexNavigationBar.left {
            layout: vertical;
            dock: left;
            width: 20;
            height: 1fr;
        }
        
        VexNavigationBar.right {
            layout: vertical;
            dock: right;
            width: 20;
            height: 1fr;
        }

        .nav-btn {
            text-align: left;
            outline: thick transparent;
            background: $background-lighten-2 !important;
            width: 1fr;
            height: 1fr;
            max-height: 3;
        }
    """
    
    def __init__(self, dock_position: str, **kwargs):
        self.dock_position = dock_position
        self.last_class = None

        super().__init__(**kwargs)
    
    @property
    def logo_btn(self) -> LogoButton:
        return self.query_one("#logo-btn", LogoButton)

    @property
    def history_nav_btn(self) -> NavigationButton:
        return self.query_one("#history-nav-btn", NavigationButton)
    
    @property
    def intercept_nav_btn(self) -> NavigationButton:
        return self.query_one("#intercept-nav-btn", NavigationButton)
        
    @property
    def replay_nav_btn(self) -> NavigationButton:
        return self.query_one("#replay-nav-btn", NavigationButton)
    
    @property
    def scope_nav_btn(self) -> NavigationButton:
        return self.query_one("#scope-nav-btn", NavigationButton)
    
    @property
    def project_nav_btn(self) -> NavigationButton:
        return self.query_one("#project-nav-btn", NavigationButton)

    def compose(self) -> ComposeResult:
        yield LogoButton("𝙑𝙚𝙭", id="logo-btn", disabled=True, compact=True)
        yield NavigationButton("  HTTP History", compact=True, classes="nav-btn",
                                id="history-nav-btn", action="app.switch('history-screen')")
        yield NavigationButton("🎯 Intercept", compact=True, classes="nav-btn",
                                id="intercept-nav-btn", action="app.switch('intercept-screen')")
        yield NavigationButton("  Replay", compact=True, classes="nav-btn",
                                id="replay-nav-btn", action="app.switch('replay-screen')")
        yield NavigationButton("  Scope", compact=True, classes="nav-btn",
                                id="scope-nav-btn", action="app.switch('scope-screen')")
        yield NavigationButton("  Projects", compact=True, classes="nav-btn",
                                id="project-nav-btn", action="app.switch('projects-screen')")
        yield InterceptButton("", compact=True) 

    def set_bar_position(self, position: str = "top"):
        if self.last_class is None:
            self.add_class(position)
        else:
            self.remove_class(self.last_class)
            self.add_class(position)

        self.last_class = position
            
    def on_mount(self):
        self.set_bar_position(self.dock_position)
 