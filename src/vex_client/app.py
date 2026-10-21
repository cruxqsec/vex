import logging
from collections import deque
from typing import ClassVar

import httpx
from textual import on, work
from textual.app import App
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.theme import BUILTIN_THEMES as TEXTUAL_BUILTIN_THEMES
from textual.widgets import Select

from vex_cli.models.pydantic import Project, RequestSummary, ResponseSummary, Scope
from vex_client.cli_controller import LocalServerController
from vex_client.connection_manager import ConnectionManager, ConnectionState
from vex_client.history.manager import HistoryManager
from vex_client.history.screen import VexHistoryScreen
from vex_client.intercept.screen import VexInterceptScreen
from vex_client.logging_config import configure_logging
from vex_client.modals.confirm import ConfirmModal
from vex_client.projects.screen import VexProjectsScreen
from vex_client.proxy.screen import VexProxyScreen
from vex_client.replay.screen import VexReplayScreen
from vex_client.scope.screen import VexScopeScreen
from vex_client.settings import Settings
from vex_client.themes.builtin import BUILTIN_THEMES
from vex_client.themes.models import FileStyle, MethodStyles, VexTheme
from vex_client.widgets.logs_panel import (
    MAX_LOG_HISTORY,
    LogMessage,
    VexLogsPanel,
)
from vex_client.widgets.text_area import VexTextArea


class ConnectionStateChanged(Message):
    def __init__(self, state: ConnectionState) -> None:
        super().__init__()
        self.state = state


logger = logging.getLogger(__name__)

_SEVERITY_TO_LEVEL = {
    "info": logging.INFO,
    "success": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


class VexApp(App[str]):
    def __init__(self, *args, **kwargs) -> None:
        configure_logging()
        super().__init__(*args, **kwargs)

    CSS_PATH = "vex.tcss"

    BINDINGS: ClassVar = [
        Binding(
            "ctrl+q",
            "switch('history-screen')",
            "Navigate to HTTP History screen",
            priority=True,
        ),
        Binding(
            "ctrl+w",
            "switch('intercept-screen')",
            "Navigate to Intercept screen",
            priority=True,
        ),
        Binding(
            "ctrl+e",
            "switch('replay-screen')",
            "Navigate to Replay screen",
            priority=True,
        ),
        Binding(
            "ctrl+r",
            "switch('scope-screen')",
            "Navigate to Scope screen",
            priority=True,
        ),
        Binding(
            "ctrl+t",
            "switch('projects-screen')",
            "Navigate to Projects screen",
            priority=True,
        ),
        Binding(
            "ctrl+l",
            "toggle_logs()",
            "Toggle logs menu",
            priority=True,
        ),
        Binding("ctrl+c", "switch('proxy-screen')", "Quit", priority=True),
        Binding("ctrl+s", "select_scope()", "Select scope", priority=True),
    ]

    SCREENS: ClassVar = {
        "proxy-screen": VexProxyScreen,
        "scope-screen": VexScopeScreen,
        "history-screen": VexHistoryScreen,
        "intercept-screen": VexInterceptScreen,
        "replay-screen": VexReplayScreen,
        "projects-screen": VexProjectsScreen,
    }

    @property
    def projects_screen(self) -> VexProjectsScreen:
        screen = self.get_screen("projects-screen")
        assert isinstance(screen, VexProjectsScreen)
        return screen

    @property
    def history_screen(self) -> VexHistoryScreen:
        screen = self.get_screen("history-screen")
        assert isinstance(screen, VexHistoryScreen)
        return screen

    @property
    def intercept_screen(self) -> VexInterceptScreen:
        screen = self.get_screen("intercept-screen")
        assert isinstance(screen, VexInterceptScreen)
        return screen

    @property
    def replay_screen(self) -> VexReplayScreen:
        screen = self.get_screen("replay-screen")
        assert isinstance(screen, VexReplayScreen)
        return screen

    @property
    def proxy_screen(self) -> VexProxyScreen:
        screen = self.get_screen("proxy-screen")
        assert isinstance(screen, VexProxyScreen)
        return screen

    @property
    def scope_screen(self) -> VexScopeScreen:
        screen = self.get_screen("scope-screen")
        assert isinstance(screen, VexScopeScreen)
        return screen

    active_project: reactive[Project | None] = reactive(
        None, init=False, always_update=True
    )
    active_scope: reactive[Scope | None] = reactive(
        None, init=False, always_update=False
    )
    server_online: reactive[bool] = reactive(False, init=False, always_update=False)
    scope_cache: reactive[dict[int, Scope]] = reactive(
        dict, init=False, always_update=False
    )

    async def on_mount(self) -> None:
        self.cli_controller: LocalServerController = LocalServerController()
        self.connection_manager: ConnectionManager = ConnectionManager(
            on_state_changed=self._notify_state_changed
        )
        self._log_history: deque[LogMessage] = deque(maxlen=MAX_LOG_HISTORY)
        self.history_manager = HistoryManager(
            on_summary_received=self._on_history_summary_received,
            on_loading_changed=self._on_history_loading_changed,
        )

        self.settings: Settings = Settings()
        self._register_themes()
        self.watch(self.app, "theme", self.on_theme_change, init=False)
        self.theme = self.settings.theme

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")

    async def on_unmount(self) -> None:
        await self.connection_manager.disconnect()

    def _notify_state_changed(self, state: ConnectionState) -> None:
        """Callback which posts the message to signal a connection state change."""
        self.post_message(ConnectionStateChanged(state))

    def get_screen_name(self) -> str:
        """Get screen name for the screen we use to install it and is defined in the SCREENS."""
        current_screen = self.app.screen

        for name, screen in self.app.SCREENS.items():
            if isinstance(current_screen, screen):  # type: ignore
                return name
        return ""

    # ------------ Session and cleanup functions -------------

    def _start_session(self) -> None:
        server_info = self.connection_manager.server_info
        if server_info is not None:
            self.run_worker(
                self.history_manager.receive_summaries(server_info),
                name="history_connection",
                group="history_connection",
                exclusive=True,
            )
        self.refresh_active_project()

    def _end_session(self) -> None:
        for group in ("history_connection", "active_project"):
            self.workers.cancel_group(self, group)
        self._cancel_project_workers()
        self.history_manager.stop()
        self.set_project(None)
        self.projects_screen.clear_screen()

    def set_project(self, project: Project | None) -> None:
        previous = self.active_project

        # Refresh metadata without restarting project work.
        if previous is not None and project is not None and previous.id == project.id:
            self.active_project = project
            return

        self._clear_session()
        self.active_project = project

        if project is None:
            if self.server_online:
                self.history_manager.clear_project()
                self.history_screen.reset_project_view()
            return

        self.history_screen.reset_project_view()
        api = self.connection_manager.api_client
        if api is not None:
            self.history_manager.start_project()
            self.run_worker(
                self.history_manager.load_summaries(api),
                name="history_load",
                group="history_load",
                exclusive=True,
            )
        self._fetch_scopes()
        self._fetch_active_scope()

    def _clear_session(self) -> None:
        self._cancel_project_workers()
        self.history_screen.invalidate_pending_work()
        self.active_scope = None
        self.scope_cache = {}

        self.scope_screen.clear_screen()
        self.intercept_screen.clear_screen()
        self.replay_screen.clear_screen()

    def _cancel_project_workers(self) -> None:
        for group in ("history_load", "fetch_scopes", "fetch_active_scope"):
            self.workers.cancel_group(self, group)

    # ------------ Message handlers -------------

    @on(ConnectionStateChanged)
    def connection_state_changed(self, message: ConnectionStateChanged):
        was_online = self.server_online
        self.server_online = message.state is ConnectionState.CONNECTED

        if was_online and not self.server_online:
            self._end_session()
        elif not was_online and self.server_online:
            self._start_session()

        if message.state is ConnectionState.CONNECTED:
            self.log_vex(
                "Successfuly connected to vex-cli",
                severity="success",
                write_to_log=False,
            )
        elif (
            message.state is ConnectionState.RECONNECTING
            and was_online
            and self.connection_manager.state is ConnectionState.RECONNECTING
        ):
            self.log_vex("Connection lost; reconnecting", "warning", write_to_log=False)

        self.proxy_screen.refresh_connection_status()

    # ------------ History UI callbacks -------------

    def _on_history_summary_received(
        self, summary: RequestSummary | ResponseSummary
    ) -> None:
        if self.history_screen.is_mounted:
            self.history_screen.request_refresh()

    def _on_history_loading_changed(self, loading: bool) -> None:
        if self.history_screen.is_mounted:
            self.history_screen.history_loading_changed(loading)

    # ------------ Project worker -------------
    #
    @work(name="get_active_project", group="active_project", exclusive=True)
    async def refresh_active_project(self):
        """
        Worker function that queries the server at /api/project/active/
        to see if there is a project active
        """
        api = self.connection_manager.api_client
        if api is None:
            self.log_vex("An error occured. Cannot get active project!", "error")
            return

        try:
            fetched_active_project: (
                Project | None
            ) = await api.projects.get_active_project()
        except httpx.HTTPError:
            self.log_vex(
                "Could not load the active project.", "warning", write_to_log=False
            )
            return

        if api is not self.connection_manager.api_client:
            return
        self.set_project(fetched_active_project)

    # ------------ Scope worker -------------

    @work(name="fetch_scopes", group="fetch_scopes", exclusive=True)
    async def _fetch_scopes(self):
        api = self.connection_manager.api_client
        if api is None:
            return

        all_scopes: list[Scope] = []
        skip = 0
        try:
            while True:
                batch = await api.scope.get_all_scopes(skip=skip, size=50)
                if not batch:
                    break
                all_scopes += batch
                if len(batch) < 50:
                    break
                skip += 50
        except httpx.HTTPError:
            return

        self.scope_cache = {scope.id: scope for scope in all_scopes}

        try:
            scope_screen: VexScopeScreen = self.get_screen("scope-screen")  # type: ignore
            if scope_screen.is_mounted:
                scope_screen.add_new_scopes_to_list()
        except NoMatches:
            pass

    @work(name="fetch_active_scope", group="fetch_active_scope", exclusive=True)
    async def _fetch_active_scope(self):
        api = self.connection_manager.api_client
        if api is None:
            return
        try:
            active = await api.scope.get_active_scope()
        except httpx.HTTPError:
            return
        self.active_scope = active

    # ------------ Actions related -------------

    async def action_quit(self) -> None:
        """Prompt to stop a still-running server before quitting."""
        # TODO: use connection manager
        if not self.cli_controller.is_cli_running:
            self.exit()
            return

        async def on_confirm(stop: bool) -> None:
            if stop:
                await self.connection_manager.disconnect()
                stopped = await self.cli_controller.stop_vex_cli()
                if not stopped:
                    self.log_vex(
                        "Server kept running. It can be adopted next launch.",
                        "warning",
                    )
            self.exit()

        self.push_screen(
            ConfirmModal("Server still running. Stop it before quitting?"), on_confirm
        )  # type: ignore

    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)

    def action_select_scope(self) -> None:
        scope_select = self.screen.query_one_optional("#scope-select", Select)
        if scope_select:
            scope_select.action_show_overlay()

    def action_toggle_logs(self) -> None:
        self.toggle_logs()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Check if we can switch screen."""
        if action == "switch" and (
            self.screen.is_modal or isinstance(self.screen, VexProxyScreen)
        ):
            return False
        elif (
            action == "switch"
            and len(parameters) == 1
            and parameters[0] not in {"proxy-screen", "projects-screen"}
            and self.active_project is None
        ):
            return False
        return True

    # ------------ Logs related -------------

    def log_vex(
        self,
        message: str,
        severity: str = "info",
        *,
        write_to_log: bool = True,
        log_message: str | None = None,
        exc_info: bool = False,
    ) -> None:
        if write_to_log:
            diagnostic = log_message if log_message is not None else message
            if exc_info:
                logger.exception(diagnostic)
            else:
                logger.log(_SEVERITY_TO_LEVEL.get(severity, logging.INFO), diagnostic)
        self._log_history.append(LogMessage(message, severity))
        for screen_name in self.app.SCREENS:
            screen = self.get_screen(screen_name)
            logs_panel = screen.query_one_optional(VexLogsPanel)
            if logs_panel:
                logs_panel.write_to_log(message, severity)

    def toggle_logs(self) -> None:
        for screen_name in self.app.SCREENS:
            screen = self.get_screen(screen_name)
            logs_panel = screen.query_one_optional(VexLogsPanel)
            if logs_panel:
                logs_panel.toggle_panel()

    # ------------ Theme related -------------

    def get_vex_theme(self) -> VexTheme:
        return BUILTIN_THEMES[self.theme]

    def get_theme_variable_defaults(self) -> dict[str, str]:
        nightfly = BUILTIN_THEMES["nightfly"]
        m = nightfly.method or MethodStyles()
        f = nightfly.file_extension or FileStyle()
        return {
            "method-get": m.get or "#0ea5e9",
            "method-post": m.post or "#22c55e",
            "method-put": m.put or "#f59e0b",
            "method-delete": m.delete or "#ef4444",
            "method-patch": m.patch or "#14b8a6",
            "method-options": m.options or "#8b5cf6",
            "method-head": m.head or "#d946ef",
            "ext-html": f.html or "#22c55e",
            "ext-css": f.css or "#ef4444",
            "ext-js": f.js or "#f5da0b",
            "ext-ts": f.ts or "#0ea5e9",
            "ext-php": f.php or "#00537a",
            "ext-json": f.json_ext or "#d58317",
            "ext-pdf": f.pdf or "#ff4646",
            "ext-png": f.png or "#14b8a6",
            "ext-jpg": f.jpg or "#8b5cf6",
            "ext-svg": f.svg or "#d946ef",
        }

    def on_theme_change(self, old_value: str, new_value: str) -> None:
        if new_value not in BUILTIN_THEMES:
            return

        new_theme = BUILTIN_THEMES[new_value]
        ta_theme = new_theme.to_text_area_theme()
        for screen_name in self.app.SCREENS:
            screen = self.get_screen(screen_name)
            for text_area in screen.query(VexTextArea):
                text_area.register_theme(ta_theme)
                text_area.theme = ta_theme.name

    def _register_themes(self) -> None:
        # first unregister the textual themes
        for theme in TEXTUAL_BUILTIN_THEMES.values():
            self.unregister_theme(theme.name)

        for vex_theme in BUILTIN_THEMES.values():
            self.register_theme(vex_theme.to_textual_theme())
