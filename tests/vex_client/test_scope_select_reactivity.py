from types import SimpleNamespace
from unittest.mock import AsyncMock

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Select

from vex_cli.models.pydantic import Project, Scope
from vex_client.widgets.navigation_bar import ScopeSelect, VexNavigationBar


class ScopeSelectHarness(App[None]):
    active_project: reactive[Project | None] = reactive(None)
    active_scope: reactive[Scope | None] = reactive(None)
    scope_cache: reactive[dict[int, Scope]] = reactive(dict, init=False)

    def __init__(self) -> None:
        super().__init__()
        self.scope_api = SimpleNamespace(
            set_scope=AsyncMock(return_value=True),
            unset_scope=AsyncMock(return_value=True),
        )
        self.connection_manager = SimpleNamespace(
            api_client=SimpleNamespace(scope=self.scope_api)
        )

    def compose(self) -> ComposeResult:
        yield VexNavigationBar(id="first-navigation")
        yield VexNavigationBar(id="second-navigation")

    def get_screen_name(self) -> str:
        return "projects-screen"


def make_scope(scope_id: int, name: str) -> Scope:
    return Scope(id=scope_id, name=name, allow_endpoints=[], deny_endpoints=[])


def assert_options(app: ScopeSelectHarness, expected: list[tuple[str, int]]) -> None:
    for select in app.query(ScopeSelect):
        # Select includes its blank entry alongside the supplied options.
        options = [option for option in select._options if option[1] != Select.NULL]
        assert options == expected


async def test_cache_replacement_updates_all_scope_selects() -> None:
    app = ScopeSelectHarness()
    first = make_scope(1, "First")
    second = make_scope(2, "Second")

    async with app.run_test() as pilot:
        app.scope_cache = {first.id: first}
        app.active_scope = first
        await pilot.pause()
        assert_options(app, [("First", 1)])
        assert all(select.value == first.id for select in app.query(ScopeSelect))

        app.scope_cache = {**app.scope_cache, second.id: second}
        await pilot.pause()
        assert_options(app, [("First", 1), ("Second", 2)])
        assert all(select.value == first.id for select in app.query(ScopeSelect))

        renamed = first.model_copy(update={"name": "Renamed"})
        app.scope_cache = {**app.scope_cache, renamed.id: renamed}
        await pilot.pause()
        assert_options(app, [("Renamed", 1), ("Second", 2)])

        app.scope_cache = {second.id: second}
        await pilot.pause()
        assert_options(app, [("Second", 2)])
        assert all(select.value == Select.NULL for select in app.query(ScopeSelect))

        app.active_scope = None
        app.scope_cache = {}
        await pilot.pause()
        assert_options(app, [])
        assert all(select.value == Select.NULL for select in app.query(ScopeSelect))
        app.scope_api.set_scope.assert_not_awaited()
        app.scope_api.unset_scope.assert_not_awaited()


async def test_navigation_bar_mounted_later_reads_current_scope_state() -> None:
    app = ScopeSelectHarness()
    scope = make_scope(1, "Existing")

    async with app.run_test() as pilot:
        app.scope_cache = {scope.id: scope}
        app.active_scope = scope
        await pilot.pause()

        navigation = VexNavigationBar(id="late-navigation")
        await app.screen.mount(navigation)
        await pilot.pause()

        assert_options(app, [("Existing", 1)])
        assert navigation.query_one(ScopeSelect).value == scope.id
        app.scope_api.set_scope.assert_not_awaited()
        app.scope_api.unset_scope.assert_not_awaited()


async def test_selecting_scope_updates_other_navigation_bars() -> None:
    app = ScopeSelectHarness()
    scope = make_scope(1, "Selected")

    async with app.run_test() as pilot:
        app.scope_cache = {scope.id: scope}
        await pilot.pause()

        first_select = app.query_one("#first-navigation").query_one(ScopeSelect)
        first_select.value = scope.id
        await pilot.pause()

        assert app.active_scope == scope
        assert all(select.value == scope.id for select in app.query(ScopeSelect))
        app.scope_api.set_scope.assert_awaited_once_with(scope.id)
        app.scope_api.unset_scope.assert_not_awaited()

        first_select.value = Select.NULL
        await pilot.pause()

        assert app.active_scope is None
        assert all(select.value == Select.NULL for select in app.query(ScopeSelect))
        app.scope_api.set_scope.assert_awaited_once_with(scope.id)
        app.scope_api.unset_scope.assert_awaited_once_with()
