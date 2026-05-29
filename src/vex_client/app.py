import asyncio
import logging
import json
import websockets
from uuid import UUID
from pydantic import ValidationError

from textual import work
from textual.app import App
from textual.binding import Binding
from textual.theme import BUILTIN_THEMES as TEXTUAL_BUILTIN_THEMES
from textual.reactive import reactive

from vex_cli.models.pydantic import (
    RequestSummary,
    ResponseSummary,
    FlowSummary,
    Project,
)
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
from vex_client.api.summaries_api import get_all_summaries

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
        Binding(
            "ctrl+n",
            "check_workers()",
            "Test",
            priority=True,
        ),
        Binding(
            "ctrl+b",
            "check_screens()",
            "Test",
            priority=True,
        )
    ]

    SCREENS = {
        "proxy-screen": VexProxyScreen,
        "scope-screen": VexScopeScreen,
        "history-screen": VexHTTPHistoryScreen,
        "intercept-screen": VexInterceptScreen,
        "replay-screen": VexReplayScreen,
        "projects-screen": VexProjectsScreen,
    }

    is_project_active: reactive[bool] = reactive(False, init=False, always_update=True)
    server_online: reactive[bool] = reactive(False, init=False, always_update=False)

    async def on_mount(self) -> None:
        self.vex_controller: VexController = VexController()
        self.settings: Settings = Settings()

        self._log_history: list[LogMessage] = []
        self.active_project: Project | None = None
        self.history_summary_cache: dict[UUID, FlowSummary] = {}

        # reference to the history screen so we don't have to query it each time
        self.history_screen: VexHTTPHistoryScreen | None = None

        self._register_themes()
        self.watch(self.app, "theme", self.on_theme_change, init=False)
        self.theme = self.settings.theme

        # Start with the proxy selection screen
        self.push_screen("proxy-screen")

    def get_api_info(self) -> tuple[str, int] | tuple[None, None]:
        """Return the API info so we can call vex-cli API."""
        server_info = self.vex_controller.server_info

        if server_info is None:
            return None, None

        return server_info.server_address, server_info.api_port

    # ------------ Watcher methods -------------

    def watch_server_online(self, online: bool) -> None:
        self.log(f"RAW: watch_server_online fired: {online}")
        if online:
            self._history_websocket_manager()

    def watch_is_project_active(self, active: bool) -> None:
        if active:
            self._fetch_all_summaries()
        else:
            self.history_summary_cache.clear()

    # ------------ Project related -------------

    def set_active_project(self, active_project: Project | None) -> None:
        """Sets the project object and toggles reactive"""

        self.active_project = active_project
        if self.active_project is None:
            self.is_project_active = False
        else:
            self.is_project_active = True

    # ------------ Server monitor worker -------------

    @work(name="server_monitor", group="monitor", exclusive=True)
    async def _server_monitor(self):
        host, port = self.get_api_info()
        if host is None or port is None:
            return
        try:
            async with websockets.connect(
                f"ws://{host}:{port}/ws/ping",
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                self.server_online = True
                self.log_vex("Server connected")
                await ws.wait_closed()
                self.log_vex("Server shutdown")
        except websockets.ConnectionClosed:
            self.log_vex("Server closed connection unexpectedly", "warning")
        except OSError:
            self.log_vex("Could not reach server, is it running?", "error")
        except Exception as e:
            self.log_vex(f"Unexpected error in server monitor: {e}", "error")
        finally:
            self.server_online = False

    # ------------ History manager and summary cache -------------

    @work(name="history_manager", group="history", exclusive=True)
    async def _history_websocket_manager(self) -> None:

        self.log_vex("History manager: worker started")
        while self.server_online:
            #self.log_vex("History manager: active", "success")
            self.log_vex("History manager: attempting connection")
            await self._handle_history_connection()
            self.log_vex(f"History manager: post-connection, server_online={self.server_online}")
            await asyncio.sleep(5)  # so we don't spam the server after reconnect
        self.log_vex("History manager: exiting loop, server_online is False", "error")

    async def _handle_history_connection(self) -> None:
        """Connects to vex-cli websocket and processes messages (summaries)"""
        host, port = self.get_api_info()
        self.log_vex(f"History manager: connecting to {host}:{port}")
        if host is None or port is None:
            self.log_vex("History manager: no API info, aborting", "error")
            return

        self.uri = f"ws://{host}:{port}/ws/history"
        try:
            async with websockets.connect(self.uri) as websocket:
                #self.log_vex("History manager: connected", "success")
                self.log("RAW: connected")
                async for raw_message in websocket:
                    self.log("RAW: got message")
                    #self.log_vex(f"History manager: raw message received")
                    self._handle_message(raw_message)
                self.log_vex("History manager: connection closed cleanly")
        except Exception as e:
                self.log_vex(f"History manager: connection failed: {type(e).__name__}: {e}", "error")

    def _handle_message(self, raw_message: websockets.Data) -> None:
        # skips processing but keeps loop/connection alive
        if not self.is_project_active:
            return
        try:
            message = self.parse_summary_message(str(raw_message))
            self.add_to_summary_cache(message)

            self.log_vex("History manager: message parsed and added to cache")
            if self.history_screen is None:
                return

            self.log_vex("History manager: message parsed and added to cache")
            if isinstance(message, RequestSummary):
                self.history_screen.http_table.insert_request_summary(message)
            else:
                self.history_screen.http_table.insert_response_summary(message)
            self.log_vex("History manager: everything should work")
        except ValidationError as e:
            self.log_vex(f"History manager: received invalid JSON structure {e}")
        except json.JSONDecodeError:
            self.log_vex("History manager: received data that wasn't even JSON!")
        except Exception as e:
                self.log_vex(f"History manager: handling message failed: {type(e).__name__}: {e}", "error")


    def parse_summary_message(self, raw_data: str) -> RequestSummary | ResponseSummary:
        data = json.loads(raw_data)
        try:
            return RequestSummary.model_validate(data)
        except ValidationError:
            return ResponseSummary.model_validate(data)

    def add_to_summary_cache(
        self, summary: RequestSummary | ResponseSummary | FlowSummary
    ) -> None:
        if isinstance(summary, RequestSummary):
            self.history_summary_cache[summary.flow_id] = FlowSummary(
                **summary.model_dump()
            )
        elif isinstance(summary, ResponseSummary):
            if summary.flow_id in self.history_summary_cache:
                # get the unfinished summary
                unfinished_summary = self.history_summary_cache[summary.flow_id]
                # fill it
                unfinished_summary.status_code = summary.status_code
                unfinished_summary.response_size = summary.response_size
                unfinished_summary.mime = summary.mime
                unfinished_summary.http_title = summary.http_title
                unfinished_summary.cookie = summary.cookie
                unfinished_summary.duration_ms = summary.duration_ms
                unfinished_summary.timestamp = summary.timestamp
        elif isinstance(summary, FlowSummary):
            self.history_summary_cache[summary.flow_id] = summary

    @work(name="fetch_summaries", group="summaries", exclusive=True)
    async def _fetch_all_summaries(self) -> None:
        host, port = self.get_api_info()
        if host is None or port is None:
            return
        skip = 0
        while True:
            summaries = await get_all_summaries(host, port, skip, 50)
            if not summaries:
                break
            for summary in summaries:
                self.add_to_summary_cache(summary)
            skip += 50

        # only populate table after full fetch is done
        if self.history_screen is not None:
            self.history_screen.populate_table()

    # ------------ Screen related -------------

    def get_screen_name(self) -> str:
        """Get screen name for the screen we use to install it and is defined in the SCREENS."""
        current_screen = self.app.screen

        for name, screen in self.app.SCREENS.items():
            if isinstance(current_screen, screen):  # type: ignore
                return name
        return ""

    """
    async def preload_screen(self, screen_name: str) -> None:
        await self.push_screen(screen_name)
        await asyncio.sleep(0.5)
        await self.pop_screen()
    """

    # ------------ Actions related -------------

    def action_switch(self, screen_name: str) -> None:
        self.switch_screen(screen_name)

    def action_toggle_logs(self) -> None:
        self.toggle_logs()

    def action_check_workers(self) -> None:
        self.log_vex(f"{self.app.workers._workers}")

    def action_check_screens(self) -> None:
        self.log_vex(f"{self.app.screen_stack}")
        self.log_vex(f"installed: {self.app._installed_screens}")

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

        for name, vex_theme in BUILTIN_THEMES.items():
            self.register_theme(vex_theme.to_textual_theme())
