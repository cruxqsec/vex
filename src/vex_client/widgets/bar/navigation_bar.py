from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button

from vex_client.widgets.bar.intercept_button import InterceptButton
from vex_client.widgets.bar.navigation_button import NavigationButton
from vex_client.widgets.bar.scope_select import ScopeSelect


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
        """

    def __init__(self, dock_position: str, **kwargs):
        self.dock_position = dock_position
        self.last_class = None

        super().__init__(**kwargs)

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
        yield ScopeSelect(options=[("No scope", 0)], value=0)
        yield NavigationButton(
            "  History",
            compact=True,
            id="history-nav-btn",
            action="app.switch('history-screen')",
        )
        yield NavigationButton(
            #🎯
            "󰓾 Intercept",
            compact=True,
            id="intercept-nav-btn",
            action="app.switch('intercept-screen')",
        )
        yield NavigationButton(
            "  Replay",
            compact=True,
            id="replay-nav-btn",
            action="app.switch('replay-screen')",
        )
        yield NavigationButton(
            "  Scope",
            compact=True,
            id="scope-nav-btn",
            action="app.switch('scope-screen')",
        )
        yield NavigationButton(
            "  Projects",
            compact=True,
            id="project-nav-btn",
            action="app.switch('projects-screen')",
        )
        yield InterceptButton("", compact=True)

    def on_mount(self):
        app = cast("VexApp", self.app)

        self.set_bar_position(self.dock_position)
        self.set_navigation_btn_color()

        # all buttons except the project one are disabled until a project is picked
        self.watch(app, "is_project_active", self.on_project_active)
        self.buttons_disabled(not app.is_project_active)

    def set_bar_position(self, position: str = "top") -> None:
        if self.last_class is None:
            self.add_class(position)
        else:
            self.remove_class(self.last_class)
            self.add_class(position)

        self.last_class = position

    def on_project_active(self, active: bool) -> None:
        self.buttons_disabled(not active)

    def buttons_disabled(self, enabled: bool) -> None:
        for button in self.query(Button):
            # all except the Project button
            if button.id == "project-nav-btn":
                continue
            button.disabled = enabled

    def set_navigation_btn_color(self) -> None:
        """Sets the corresponding button color of the page we're on"""
        color = self.app.get_css_variables()["primary-darken-3"]

        app = cast("VexApp", self.app)
        screen_name = app.get_screen_name()

        if screen_name == "history-screen":
            self.history_nav_btn.styles.background = color
        elif screen_name == "intercept-screen":
            self.intercept_nav_btn.styles.background = color
        elif screen_name == "replay-screen":
            self.replay_nav_btn.styles.background = color
        elif screen_name == "scope-screen":
            self.scope_nav_btn.styles.background = color
        elif screen_name == "projects-screen":
            self.project_nav_btn.styles.background = color
