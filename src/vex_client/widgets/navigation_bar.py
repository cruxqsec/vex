from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Select


class NavigationButton(Button, can_focus=False):
    """
    The sidebar button for switching between screens.
    """


class InterceptButton(Button, can_focus=False):
    """
    Button for interception. Can be in 2 states. Forwarding and intercepting.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_active = True
        self.toggle()  # Toggle it to be forwarding by default

    def toggle(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.add_class("intercepting")
            self.label = " Intercepting"
        else:
            self.remove_class("intercepting")
            self.label = " Forwarding"

    def on_button_pressed(self):
        self.toggle()


class ScopeSelect(Select, can_focus=False):
    """Select the scope"""


class VexNavigationBar(Widget):
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
            # 🎯
            "󰓾  Intercept",
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

        self.set_navigation_btn_color()

        # all buttons except the project one are disabled until a project is picked
        self.watch(app, "is_project_active", self.on_project_active)
        self.buttons_disabled(not app.is_project_active)

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

        app = cast("VexApp", self.app)
        screen_name = app.get_screen_name()

        if screen_name == "history-screen":
            self.history_nav_btn.add_class("active")
        elif screen_name == "intercept-screen":
            self.intercept_nav_btn.add_class("active")
        elif screen_name == "replay-screen":
            self.replay_nav_btn.add_class("active")
        elif screen_name == "scope-screen":
            self.scope_nav_btn.add_class("active")
        elif screen_name == "projects-screen":
            self.project_nav_btn.add_class("active")