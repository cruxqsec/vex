from dataclasses import FrozenInstanceError
from typing import ClassVar
from unittest.mock import Mock
from uuid import uuid4

import pytest
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.geometry import Size
from textual.widgets import DataTable

from vex_cli.models.pydantic import Project
from vex_client.projects.table import VexProjectTable
from vex_client.widgets.table import SortOrder, VexDataTable


class NumberTable(VexDataTable):
    SORT_KEYS: ClassVar = {"Value": lambda item: item[1]}

    def __init__(self):
        super().__init__((("Value", 100),))


def test_active_sort_is_frozen_and_property_is_read_only():
    order = SortOrder("Value")
    assert not order.descending
    with pytest.raises(FrozenInstanceError):
        order.descending = True  # type: ignore[misc]  # Verify frozen dataclass at runtime.
    table = NumberTable()
    assert table.active_sort is None
    assert isinstance(table.sort_order, int)
    table.sort_order = 0
    assert table.active_sort is None
    with pytest.raises(AttributeError):
        table.active_sort = order  # type: ignore[assignment]  # Verify read-only API.


@pytest.mark.parametrize("descending", [False, True])
def test_sort_is_stable_with_none_last_and_zero_present(descending):
    table = NumberTable()
    items = [("missing1", None), ("two1", 2), ("zero", 0),
             ("missing2", None), ("two2", 2), ("negative", -1)]
    original = items.copy()
    table._toggle_sort("Value")
    if descending:
        table._toggle_sort("Value")
    expected = (["two1", "two2", "zero", "negative"] if descending
                else ["negative", "zero", "two1", "two2"])
    assert [item[0] for item in table.sort_items(iter(items))] == (
        expected + ["missing1", "missing2"]
    )
    assert items == original
    assert table.sort_items([]) == []
    assert table.sort_items(items[:1]) == items[:1]


def test_no_sort_preserves_input_order_and_reset_notifications():
    table = NumberTable()
    items = [("two", 2), ("one", 1)]
    assert table.sort_items(iter(items)) == items
    table.post_message = Mock()
    table._toggle_sort("Value")
    assert table.has_active_sort
    assert table.post_message.call_args.args[0].active_sort == SortOrder("Value")
    table.post_message.reset_mock()
    table.reset_sort()
    assert table.active_sort is None
    assert not table.has_active_sort
    table.post_message.assert_not_called()
    assert table.sort_items(items) == items
    table._toggle_sort("Value")
    table.post_message.reset_mock()
    table.reset_sort(notify=True)
    assert table.post_message.call_args.args[0].active_sort is None
    table.post_message.reset_mock()
    table.reset_sort(notify=True)
    table.post_message.assert_not_called()


def project(name, created, updated):
    return Project(id=uuid4(), name=name, created_at=created, updated_at=updated)


@pytest.mark.parametrize("column, expected", [
    ("Name", [1, 2, 0]),
    ("Created at", [2, 0, 1]),
    ("Updated at", [1, 0, 2]),
])
def test_project_rules(column, expected):
    table = VexProjectTable()
    items = [project("Zulu", 2, 2), project("alpha", 3, 0), project("ALPHA", 0, 3)]
    table._toggle_sort(column)
    assert table.sort_items(items) == [items[index] for index in expected]
    table._toggle_sort(column)
    descending = [0, 1, 2] if column == "Name" else list(reversed(expected))
    assert table.sort_items(items) == [items[index] for index in descending]
    table._toggle_sort(column)
    assert table.active_sort is None
    assert table.sort_items(items) == items


class TableApp(App):
    def __init__(self):
        super().__init__()
        self.sort_events: list[SortOrder | None] = []

    def compose(self) -> ComposeResult:
        yield VexProjectTable()

    @on(VexDataTable.SortChanged)
    def capture_sort_changed(self, event: VexDataTable.SortChanged) -> None:
        self.sort_events.append(event.active_sort)


async def test_project_header_keyboard_cycle_unsupported_and_styles():
    app = TableApp()
    async with app.run_test() as pilot:
        table = app.query_one(VexProjectTable)
        table.set_columns(Size(80, 24))
        table.focus()
        table.get_component_rich_style = Mock(return_value=Style(bold=True))
        original = table.ordered_columns[0].label.copy()

        await pilot.press("1")
        await pilot.pause()
        assert app.sort_events == [SortOrder("Name")]
        assert table.active_sort == SortOrder("Name")
        assert table.ordered_columns[0].label != original
        table.get_component_rich_style.assert_called_with("vex-datatable--sort-asc")

        header = DataTable.HeaderSelected(table, table.ordered_columns[0].key, 0, Text("Name"))
        table._on_column_header_selected(header)
        assert table.active_sort == SortOrder("Name", descending=True)
        table.get_component_rich_style.assert_called_with("vex-datatable--sort-desc")
        label = table.ordered_columns[0].label.copy()
        await pilot.pause()
        assert app.sort_events == [SortOrder("Name"), SortOrder("Name", descending=True)]
        app.sort_events.clear()
        await pilot.press("2")
        table._on_column_header_selected(
            DataTable.HeaderSelected(table, table.ordered_columns[1].key, 1, Text("Size"))
        )
        table._toggle_sort("Unknown")
        table.action_sort_column(-1)
        table.action_sort_column(99)
        assert table.active_sort == SortOrder("Name", descending=True)
        assert table.ordered_columns[0].label == label
        await pilot.pause()
        assert app.sort_events == []

        await pilot.press("1")
        assert table.active_sort is None
        assert table.ordered_columns[0].label == original
        await pilot.pause()
        assert app.sort_events == [None]
        app.sort_events.clear()

        await pilot.press("1", "3")
        assert table.active_sort == SortOrder("Created at")
        assert table.ordered_columns[0].label == original
        await pilot.pause()
        assert app.sort_events == [SortOrder("Name"), SortOrder("Created at")]
        app.sort_events.clear()
        table.reset_sort()
        assert table.ordered_columns[2].label == Text("Created at")
        await pilot.pause()
        assert app.sort_events == []
