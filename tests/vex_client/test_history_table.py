from unittest.mock import Mock
from uuid import uuid4

import pytest
from rich.style import Style
from textual.app import App
from textual.widgets import DataTable

from vex_cli.models.pydantic import FlowSummary
from vex_client.history.table import VexHTTPTable
from vex_client.widgets.empty_message_widget import EmptyStateChanged

COLUMNS = tuple((name, 9) for name in VexHTTPTable.SORT_KEYS)


def summary(number, **kwargs):
    return FlowSummary(
        id=number, flow_id=uuid4(), host="example.test", method="GET",
        path="/", request_size=0, is_tls=False, query=None,
        file_extension=None, timestamp=0, **kwargs,
    )


class TableApp(App):
    def __init__(self):
        super().__init__()
        self.delivered_highlights: list[DataTable.RowHighlighted] = []

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        self.delivered_highlights.append(event)

    def compose(self):
        table = VexHTTPTable(columns=COLUMNS)
        table._style_for = Mock(return_value=Style())
        yield table


@pytest.mark.asyncio
async def test_reconcile_preserves_rows_highlight_and_batches_notifications():
    app = TableApp()
    async with app.run_test() as pilot:
        table = pilot.app.query_one(VexHTTPTable)
        for name, _ in COLUMNS:
            table.add_column(name, key=name)
        first, second, third = [summary(i) for i in range(3)]
        table.synchronize_summaries([first, second, third])
        table.move_cursor(row=1)
        await pilot.pause()
        app.delivered_highlights.clear()
        retained_row = table.rows[next(r.key for r in table.ordered_rows if r.key.value == str(second.flow_id))]
        table.clear = Mock(side_effect=AssertionError("must not clear"))
        table.update_cell = Mock(wraps=table.update_cell)
        table.post_message = Mock(wraps=table.post_message)
        table.synchronize_summaries([third, first, second])
        assert table.get_highlighted_row_key() == str(second.flow_id)
        assert table.ordered_rows[2] is retained_row
        table.update_cell.assert_not_called()
        messages = [call.args[0] for call in table.post_message.call_args_list]
        assert len([m for m in messages if isinstance(m, EmptyStateChanged)]) == 1
        await pilot.pause()
        assert app.delivered_highlights == []

        changed = first.model_copy(update={"response_size": 0, "duration_ms": 0})
        table.synchronize_summaries([third, changed])
        assert table.cursor_row == 1
        assert table.get_highlighted_row_key() == str(first.flow_id)
        assert table.get_cell(str(first.flow_id), "Size").plain == "0"
        assert table.update_cell.call_count == 2
        table.post_message.reset_mock()
        table.synchronize_summaries([])
        assert table.row_count == 0
        messages = [call.args[0] for call in table.post_message.call_args_list]
        empty = [m for m in messages if isinstance(m, EmptyStateChanged)]
        assert len(empty) == 1 and empty[0].is_empty


@pytest.mark.asyncio
async def test_theme_forces_updates_including_false_cookie():
    async with TableApp().run_test() as pilot:
        table = pilot.app.query_one(VexHTTPTable)
        for name, _ in COLUMNS:
            table.add_column(name, key=name)
        flow = summary(1)
        table.synchronize_summaries([flow])
        assert table.get_cell(str(flow.flow_id), "Size").plain == ""
        assert table.get_cell(str(flow.flow_id), "Time(ms)").plain == ""
        table.update_cell = Mock(wraps=table.update_cell)
        table._recolor_cells()
        assert table.update_cell.call_count == len(COLUMNS)
        assert "Cookie" in [call.args[1].value for call in table.update_cell.call_args_list]


@pytest.mark.parametrize("column, field", [
    ("Status", "status_code"), ("Size", "response_size"),
    ("Time(ms)", "duration_ms"), ("Sent at", "timestamp"),
])
def test_numeric_sort_keys_preserve_zero_and_none(column, field):
    flow = summary(1)
    key = VexHTTPTable.SORT_KEYS[column]
    assert key(flow.model_copy(update={field: 0})) == 0
    assert key(flow.model_copy(update={field: None})) is None


def test_cookie_and_optional_string_sort_keys():
    flow = summary(1)
    assert VexHTTPTable.SORT_KEYS["Cookie"](flow) is False
    assert VexHTTPTable.SORT_KEYS["Cookie"](flow.model_copy(update={"cookie": ""})) is False
    assert VexHTTPTable.SORT_KEYS["Cookie"](flow.model_copy(update={"cookie": "a=b"})) is True
    assert VexHTTPTable.SORT_KEYS["Query"](flow) is None
    assert VexHTTPTable.SORT_KEYS["Query"](flow.model_copy(update={"query": ""})) == ""
