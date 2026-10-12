import httpx
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Select

from vex_cli.models.pydantic import Project, Scope


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

    @on(Select.Changed)
    async def select_changed(self, event: Select.Changed) -> None:
        app = cast("VexApp", self.app)
        value: int = cast(int, event.value)
        still_no_value = app.active_scope is None and value == Select.NULL
        no_change = app.active_scope and event.value == app.active_scope.id

        # no change happened
        if still_no_value or no_change:
            return

        api = app.api_client
        if api is None:
            return
        if value == Select.NULL:
            try:
                successfuly_unset = await api.scope.unset_scope()
            except httpx.HTTPError:
                app.log_vex("Failed to unset scope on server. Check logs", "error")
                return
            if successfuly_unset:
                app.active_scope = None
        else:
            scope = app.scope_cache.get(value)
            if not scope:
                return
            try:
                successfuly_set = await api.scope.set_scope(scope.id)
            except httpx.HTTPError:
                app.log_vex("Failed to set scope on server. Check logs.", "error")
                return

            if successfuly_set:
                app.active_scope = scope


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
        yield ScopeSelect(
            options=[],
            prompt="Select scope",
            value=Select.NULL,
            type_to_search=True,
            allow_blank=True,
            id="scope-select",
        )
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
        self.watch(app, "active_project", self.on_project_active)
        self.watch(app, "active_scope", self.update_scope_select, init=False)
        self.buttons_disabled(app.active_project is None)
        self.update_scope_select()

    def on_project_active(self, project: Project | None) -> None:
        self.buttons_disabled(project is None)

    def update_scope_select(self, *_args) -> None:
        app = cast("VexApp", self.app)
        options: list[tuple[str, int]] = []
        for scope_id, scope in app.scope_cache.items():
            options.append((scope.name, scope_id))
        scope_select = self.query_one(ScopeSelect)
        with scope_select.prevent(Select.Changed):
            scope_select.set_options(options)
            if app.active_scope is not None and app.active_scope.id in app.scope_cache:
                scope_select.value = app.active_scope.id
            else:
                scope_select.value = Select.NULL

    def clear_scope_select(self) -> None:
        scope_select = self.query_one(ScopeSelect)
        with scope_select.prevent(Select.Changed):
            scope_select.set_options([])
            scope_select.value = Select.NULL

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
