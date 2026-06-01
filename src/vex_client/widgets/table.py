from typing import Any, Tuple
from dataclasses import dataclass
from rich.text import Text

from textual import events, on
from textual.geometry import Size
from textual.binding import Binding
from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist
from textual.message import Message

from vex_client.widgets.empty_message_widget import EmptyStateChanged


@dataclass
class IconColumnCell:
    icon: Text
    name: str


class VexDataTable(DataTable, can_focus=True):
    """
    Extended DataTable with extra functionality like empty display message
    and columns that support percent ratio.
    """

    class RowAdded(Message):
        pass

    class RowRemoved(Message):
        pass

    class Focused(Message):
        pass

    class Blurred(Message):
        pass

    def _on_focus(self, event: events.Focus) -> None:
        self.post_message(self.Focused())

    def _on_blur(self, event: events.Blur) -> None:
        self.post_message(self.Blurred())

    BINDINGS = [
        Binding("k", "cursor_up", "Cursor up", show=False),
        Binding("j", "cursor_down", "Cursor down", show=False),
        Binding("l", "cursor_right", "Cursor right", show=False),
        Binding("h", "cursor_left", "Cursor left", show=False),
        Binding("ctrl+u", "page_up", "Page up", show=False),
        Binding("ctrl+f", "page_down", "Page down", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    def __init__(
        self, percent_columns: Tuple[Tuple[str | IconColumnCell, int], ...], **kwargs
    ):
        self.percent_columns = (
            percent_columns  # custom columns with (name, percent_ratio)
        )
        self._bulk_mode: bool = False

        super().__init__(**kwargs)

    def row_exists(self, key: str) -> bool:
        try:
            self.get_row(key)
            return True
        except RowDoesNotExist:
            return False

    def get_highlighted_row(self) -> list[Any] | None:
        try:
            result = self.get_row_at(self.cursor_row)
            return result
        except RowDoesNotExist:
            return None

    def get_highlighted_row_key(self) -> str | None:
        """Returns the key of the highlighted row"""
        try:
            return self.ordered_rows[self.cursor_row].key.value
        except IndexError:
            return None

    @on(RowRemoved)
    @on(RowAdded)
    def _on_rows_added_removed(self, event: RowAdded | RowRemoved) -> None:
        if self._bulk_mode:
            return
        self.post_message(EmptyStateChanged(is_empty=self.row_count == 0))

    def begin_bulk_insert(self) -> None:
        self._bulk_mode = True

    def end_bulk_insert(self) -> None:
        self._bulk_mode = False
        self.post_message(EmptyStateChanged(is_empty=self.row_count == 0))

    def on_resize(self, event: events.Resize) -> None:
        """Resize while keeping the percentage ratios."""

        total_width = event.size.width
        total_padding = 2 * (self.cell_padding * len(self.percent_columns)) + 1
        one_percent = (total_width - total_padding) / 100

        for (_, percent_width), column in zip(
            self.percent_columns, self.columns.values()
        ):
            column.auto_width = False
            column.width = round(percent_width * one_percent)

        self.refresh()

    def set_columns(self, size: Size):
        """Set the columns with percent ratio."""
        if size.width == 0:
            return

        total_width = self.size.width
        total_padding = 2 * (self.cell_padding * len(self.percent_columns))
        one_percent = (total_width - total_padding) / 100

        for column, percent_width in self.percent_columns:
            width = round(percent_width * one_percent)
            if isinstance(column, IconColumnCell):
                self.add_column(label=column.icon, width=width, key=column.name)
            else:
                self.add_column(label=column, width=width, key=column)
