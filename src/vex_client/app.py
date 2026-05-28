import asyncio
import logging

from textual.app import App
from textual.binding import Binding
from textual.theme import BUILTIN_THEMES as TEXTUAL_BUILTIN_THEMES
from textual.reactive import reactive

from vex_cli.models.pydantic import Project
from vex_client.cli_controller import VexController
from vex_client.history.screen import VexHTTPHistoryScreen
from vex_client.intercept.screen import VexInterceptScreen
from vex_client.projects.screen import VexProjectsScreen
from vex_client.proxy.screen import VexProxyScreen
from vex_client.replay.screen import VexReplayScreen
from vex_client.scope.screen import VexScopeScreen
from vex_client.settings import Settings
from vex_client.themes.builtin import BUILTIN_THEMES
from vex_client.themes.models import VexTheme
from vex_client.widgets.text_area import VexTextArea
from vex_client.themes.models import MethodStyles, FileStyle
from vex_client.widgets.logs_panel import VexLogsPanel, LogMessage

logger = logging.getLogger(__name__)


class VexApp(App[str]):
    CSS_PATH = "vex.tcss"

    BINDINGS = [
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
        Binding("ctrl+c", "switch('proxy-screen')", "Quit"),
    ]

    SCREENS = {
        "proxy-screen": VexProxyScreen,
        "scope-screen": VexScopeScreen,
        "history-screen": VexHTTPHistoryScreen,
        "intercept-screen": VexInterceptScreen,
        "replay-screen": VexReplayScreen,
        "projects-screen": VexProjectsScreen,
    }

    is_project_active: reactive[bool] = reactive(False, init=False)
    server_online: reactive[bool] = reactive(False, init=False)
    _log_history: list[LogMessage] = []

    async def on_mount(self) -> None:
        self.vex_controller: VexController = VexController()
        self.settings: Settings = Settings()

        self.vex_active_project: Project | None = None
        self.is_project_active_event: asyncio.Event = asyncio.Event()

        self._register_themes()
        self.watch(self.app, "theme", self.on_theme_change, init=False)
        self.theme = self.settings.theme

        # preload all screens so we don't have widget
        # lookup problems and we can add data to tables
        for screen_name in self.SCREENS.keys():
            await self.preload_screen(screen_name)

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")

    def get_api_info(self) -> tuple[str, int] | tuple[None, None]:
        """Return the API info so we can call vex-cli API."""
        server_info = self.vex_controller.server_info

        if server_info is None:
            return None, None

        return server_info.server_address, server_info.api_port

    # ------------ Logs related -------------

    def log_vex(self, message: str, severity: str = "info") -> None:
        self._log_history.append(LogMessage(message, severity))
        for screen_name in self.app.SCREENS:
            screen = self.get_screen(screen_name)
            logs_panel = screen.query_one_optional(VexLogsPanel)
            if logs_panel:
                logs_panel.write_to_log(message, severity)

    def toggle_logs(self) -> None:
        for screen_name in self.app.SCREENS:
            screen = self.get_screen(screen_name)
            screen.query_one(VexLogsPanel).toggle_panel()

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

        for name, vex_theme in BUILTIN_THEMES.items():
            self.register_theme(vex_theme.to_textual_theme())

    # ------------ Project related -------------

    async def set_active_project(self, active_project: Project | None) -> None:
        """
        Sets the active project, fires the event that controls managers and fetches
        all the other project related information(flows, scopes).
        If set to None also performs cleanup.
        """
        self.vex_active_project = active_project
        if self.vex_active_project is None:
            self.is_project_active = False
            self.is_project_active_event.clear()  # set flag to off -> workers wait
            await self.project_switch_cleanup()
        else:
            self.is_project_active = True
            await self.project_switch_startup()
            self.is_project_active_event.set()  # set flag to on -> workers can work

    async def project_switch_cleanup(self) -> None:
        http_screen = self.get_screen("history-screen", VexHTTPHistoryScreen)
        http_screen.http_table.clear_table()

    async def project_switch_startup(self) -> None:
        await self.project_switch_cleanup()
        fetch_all_summaries_worker = self.get_screen(
            "history-screen", VexHTTPHistoryScreen
        ).fetch_all_summaries()
        await fetch_all_summaries_worker.wait()

    # ------------ Screen related -------------

    def get_screen_name(self) -> str:
        """Get screen name for the screen we use to install it and is defined in the SCREENS."""
        current_screen = self.app.screen

        for name, screen in self.app.SCREENS.items():
            if isinstance(current_screen, screen):  # type: ignore
                return name

        return ""

    async def preload_screen(self, screen_name: str) -> None:
        """
        Preload all the screens by pushing them waiting a bit and then popping them.
        We do this so we have all the main widgets of each screen mounted.
        """
        await self.push_screen(screen_name)
        await asyncio.sleep(0.5)
        await self.pop_screen()

    # ------------ Actions related -------------

    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)

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
            and not self.is_project_active
        ):
            return False
        return True
