import httpx
from pydantic import ValidationError
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Static, ListView

from vex_cli.models.pydantic import Scope, ScopeCreate, endpoint_adapter

from vex_client.api.scope_api import (
    create_scope,
    delete_scope,
    update_scope,
)
from vex_client.widgets.navigation_bar import VexNavigationBar
from vex_client.widgets.footer import VexFooter
from vex_client.widgets.button import VexButton
from vex_client.widgets.logs_panel import VexLogsPanel
from vex_client.widgets.text_area import VexTextArea, VexTextAreaWidget
from vex_client.scope.list import (
    ScopeList,
    ScopeListItem,
    ScopeListWidget,
)


class VexScopeScreen(Screen):
    CSS_PATH = "scope.tcss"

    BINDINGS = [
        Binding("c", "create_scope", "Create scope", priority=True),
        Binding("s", "save_scope", "Save scope", priority=True),
        Binding("y", "duplicate_scope", "Duplicate scope", priority=True),
        Binding("d", "delete_scope", "Delete scope", priority=True),
    ]

    @property
    def navigation_bar(self) -> VexNavigationBar:
        return self.query_one("#navigation-bar", VexNavigationBar)

    @property
    def scope_list(self) -> ScopeList:
        return self.query_one("#scope-list", ScopeList)

    @property
    def name_input(self) -> Input:
        return self.query_one("#scope-name-input", Input)

    @property
    def in_scope_area(self) -> VexTextArea:
        return self.query_one("#in-scope-area", VexTextArea)

    @property
    def out_of_scope_area(self) -> VexTextArea:
        return self.query_one("#out-of-scope-area", VexTextArea)

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="navigation-bar")
        with Horizontal(id="scope-main-container"):
            yield ScopeListWidget(id="scope-list-widget")
            with Vertical(id="in-out-container"):
                yield Static("+ Add a new scope", id="in-out-header")
                with Horizontal(id="name-input-container"):
                    yield Static("Name*", id="scope-name-label")
                    yield Input(placeholder="Enter scope name", id="scope-name-input")
                with Horizontal(id="text-areas-container"):
                    with Vertical():
                        yield Static("● In scope", id="in-scope-label")
                        yield VexTextAreaWidget(
                            VexTextArea(
                                placeholder="Add a domain, IP, one per line...",
                                id="in-scope-area",
                            ),
                            id="in-scope-widget",
                        )
                    with Vertical():
                        yield Static("● Out of scope", id="out-of-scope-label")
                        yield VexTextAreaWidget(
                            VexTextArea(
                                placeholder="Add a domain, IP, one per line...",
                                id="out-of-scope-area",
                            ),
                            id="out-of-scope-widget",
                        )
                with Horizontal(id="btn-area-container"):
                    yield VexButton("\[s] Save", id="btn-save", classes="btn")
                    yield VexButton("\[y] Duplicate", id="btn-duplicate", classes="btn")
                    yield VexButton("\[d] Delete", id="btn-delete", classes="btn")
        yield VexLogsPanel()
        yield VexFooter()

    async def on_mount(self):
        self.navigation_bar.set_navigation_btn_color()
        self.selected_scope_item: ScopeListItem | None = None
        self.inserted_scopes_ids: set[int] = set()

    def on_screen_resume(self) -> None:
        app = cast("VexApp", self.app)
        app._fetch_scopes()
        self.scope_list.focus()

        if len(self.scope_list) == 0:
            self.query_one("#in-out-header", Static).update("+ Add a new scope")

    def add_new_scopes_to_list(self) -> None:
        app = cast("VexApp", self.app)
        for scope_id, scope in app.scope_cache.items():
            if scope_id not in self.inserted_scopes_ids:
                self.scope_list.append_scope(ScopeListItem(scope))
                self.inserted_scopes_ids.add(scope_id)

    def reset(self) -> None:
        self.scope_list.clear()
        self.selected_scope_item = None
        self.name_input.value = ""
        self.in_scope_area.text = ""
        self.out_of_scope_area.text = ""
        self.query_one("#in-out-header", Static).update("+ Add a new scope")

    # ------------------- Action logic ------------------------

    @on(ListView.Selected)
    async def select_scope(self, event: ListView.Selected) -> None:
        selected_item: ScopeListItem = cast(ScopeListItem, event.item)

        # we deselect the previous
        self.scope_list.deselect_selected()

        # and select the next one
        selected_item.toggle_selected_on()

        self.selected_scope_item = selected_item
        await self.fill_scope_data(selected_item)

    async def fill_scope_data(self, list_item: ScopeListItem) -> None:
        self.query_one("#in-out-header", Static).update("Edit scope")
        self.name_input.value = list_item.scope.name
        self.in_scope_area.text = "\n".join(list_item.scope.allow_endpoints)
        self.out_of_scope_area.text = "\n".join(list_item.scope.deny_endpoints)

    async def unfill_scope_data(self) -> None:
        if len(self.scope_list) == 0:
            self.query_one("#in-out-header", Static).update("+ Add a new scope")

        self.name_input.value = ""
        self.in_scope_area.text = ""
        self.out_of_scope_area.text = ""

    async def create_duplicate_scope(self, scope: Scope | None = None) -> None:
        scope_to_create = None
        if scope is None:
            # create new
            scope_to_create = ScopeCreate(
                name="New scope", allow_endpoints=[], deny_endpoints=[]
            )
        else:
            # duplicate
            scope_to_create = ScopeCreate(
                name=scope.name + " (Copy)",
                allow_endpoints=scope.allow_endpoints,
                deny_endpoints=scope.deny_endpoints,
            )

        app = cast("VexApp", self.app)
        host, port = app.get_api_info()

        if host is None or port is None:
            return

        try:
            created_scope = await create_scope(scope_to_create, host, port)
        except httpx.HTTPError:
            self.notify("Network error creating scope. Check logs.", severity="error")
            return

        if created_scope:
            app.scope_cache[created_scope.id] = created_scope
            self.inserted_scopes_ids.add(created_scope.id)
            created_scope_item = ScopeListItem(created_scope)
            self.scope_list.append_scope(created_scope_item)
            # we select it immediately after creation/duplication
            self.selected_scope_item = created_scope_item
        else:
            app.log_vex("Couldn't create scope! Check logs.", severity="error")

    async def action_create_scope(self) -> None:
        # Create, pass no new scope
        await self.create_duplicate_scope(None)

    async def action_duplicate_scope(self) -> None:
        if self.selected_scope_item is None:
            self.notify("No scope selected!")
            return

        # pass the scope to duplicate
        await self.create_duplicate_scope(self.selected_scope_item.scope)

    async def action_delete_scope(self) -> None:
        # we are deleting the selected item
        if self.selected_scope_item is None:
            self.notify("No scope selected!")
            return

        app = cast("VexApp", self.app)
        host, port = app.get_api_info()

        if host is None or port is None:
            return

        try:
            successfully_deleted = await delete_scope(
                self.selected_scope_item.scope.id, host, port
            )
        except httpx.HTTPError:
            app.log_vex("Network error creating scope. Check logs.", severity="error")
            return

        if not successfully_deleted:
            app.log_vex("Error deleting. Check logs.", severity="error")
            return

        self.query_one("#in-out-header", Static).update("+ Add a new scope")
        app.scope_cache.pop(self.selected_scope_item.scope.id, None)
        self.scope_list.pop_scope(self.selected_scope_item)

        if app.active_scope and self.selected_scope_item.id == app.active_scope.id:
            app.active_scope = None

        await self.unfill_scope_data()
        self.selected_scope_item = None

    async def action_save_scope(self) -> None:
        if self.selected_scope_item is None:
            self.notify("No scope selected!")
            return

        allow_raw = [
            line.strip() for line in self.in_scope_area.text.split("\n") if line.strip()
        ]
        deny_raw = [
            line.strip()
            for line in self.out_of_scope_area.text.split("\n")
            if line.strip()
        ]
        try:
            endpoint_adapter.validate_python(allow_raw)
        except ValidationError:
            self.notify("Invalid data in 'In scope' field.", severity="error")
            return
        try:
            endpoint_adapter.validate_python(deny_raw)
        except ValidationError:
            self.notify("Invalid data in 'Out of scope' field.", severity="error")
            return

        updated_scope = Scope(
            id=self.selected_scope_item.scope.id,
            name=self.name_input.value,
            allow_endpoints=allow_raw,
            deny_endpoints=deny_raw,
        )

        app = cast("VexApp", self.app)
        host, port = app.get_api_info()

        if host is None or port is None:
            return

        try:
            successfully_updated = await update_scope(updated_scope, host, port)
        except httpx.HTTPError:
            app.log_vex("Network error creating scope. Check logs.", severity="error")
            return

        if successfully_updated:
            self.notify("Scope updated!")
            app.scope_cache[updated_scope.id] = updated_scope
            self.selected_scope_item.scope = updated_scope
            self.selected_scope_item.query_one("#scope-name", Static).update(
                updated_scope.name
            )
            if app.active_scope and app.active_scope.id == updated_scope.id:
                app.active_scope = updated_scope
        else:
            app.log_vex("Error saving scope. Check logs.", severity="error")

    # ------------------- Button logic ------------------------

    @on(Button.Pressed, "#btn-create")
    async def on_create(self, event: Button.Pressed) -> None:
        await self.action_create_scope()

    @on(Button.Pressed, "#btn-save")
    async def on_save(self, event: Button.Pressed) -> None:
        await self.action_save_scope()

    @on(Button.Pressed, "#btn-duplicate")
    async def on_duplicate(self, event: Button.Pressed) -> None:
        await self.action_duplicate_scope()

    @on(Button.Pressed, "#btn-delete")
    async def on_delete(self, event: Button.Pressed) -> None:
        await self.action_delete_scope()
