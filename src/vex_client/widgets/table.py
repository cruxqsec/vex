from typing import Any, Tuple

from textual import events, on
from textual.geometry import Size
from textual.binding import Binding
from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist
from textual.message import Message

from vex_client.widgets.empty_message_widget import EmptyStateChanged


class VexDataTable(DataTable, can_focus=True):
    """
    Extended DataTable with extra functionality like empty display message
    and columns that support percent ratio.
    """

    class Focused(Message):
        pass

    class Blurred(Message):
        pass

    def _on_focus(self, event: events.Focus) -> None:
        self.post_message(self.Focused())

    def _on_blur(self, event: events.Blur) -> None:
        self.post_message(self.Blurred())

    class RowAdded(Message):
        pass

    class RowRemoved(Message):
        pass

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
        self, percent_columns: Tuple[Tuple[str, int], ...], **kwargs
    ):
        self.percent_columns = (
            percent_columns  # custom columns with (name, percent_ratio)
        )

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
        self.post_message(EmptyStateChanged(is_empty=self.row_count == 0))
        #self.set_class(self.row_count == 0, "empty")


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

        for name, percent_width in self.percent_columns:
            width = round(percent_width * one_percent)
            self.add_column(label=name, width=width, key=name)
