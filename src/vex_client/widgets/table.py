from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, ClassVar, TypeVar

from rich.text import Text
from textual import events, on
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets.data_table import RowDoesNotExist

from vex_client.widgets.empty_message_widget import EmptyStateChanged

T = TypeVar("T")


@dataclass(frozen=True)
class SortOrder:
    column: str
    descending: bool = False


@dataclass
class IconColumnCell:
    icon: Text
    name: str


class VexDataTable(DataTable, can_focus=True):
    """
    Extended DataTable with extra functionality like empty display message,
    columns that support percent ratio, and column sorting.
    """

    class RowAdded(Message):
        pass

    class RowRemoved(Message):
        pass

    class Focused(Message):
        pass

    class Blurred(Message):
        pass

    class SortChanged(Message):
        def __init__(self, active_sort: SortOrder | None) -> None:
            self.active_sort = active_sort
            super().__init__()

    SORT_KEYS: ClassVar[dict[str, Callable[[Any], Any]]] = {}

    COMPONENT_CLASSES: ClassVar = {
        "vex-datatable--sort-asc",
        "vex-datatable--sort-desc",
    }

    def _on_focus(self, event: events.Focus) -> None:
        self.post_message(self.Focused())

    def _on_blur(self, event: events.Blur) -> None:
        self.post_message(self.Blurred())

    BINDINGS: ClassVar = [
        Binding("k", "cursor_up", "Cursor up", show=False),
        Binding("j", "cursor_down", "Cursor down", show=False),
        Binding("l", "cursor_right", "Cursor right", show=False),
        Binding("h", "cursor_left", "Cursor left", show=False),
        Binding("ctrl+u", "page_up", "Page up", show=False),
        Binding("ctrl+f", "page_down", "Page down", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
        Binding("1", "sort_column(0)", show=False),
        Binding("2", "sort_column(1)", show=False),
        Binding("3", "sort_column(2)", show=False),
        Binding("4", "sort_column(3)", show=False),
        Binding("5", "sort_column(4)", show=False),
        Binding("6", "sort_column(5)", show=False),
        Binding("7", "sort_column(6)", show=False),
        Binding("8", "sort_column(7)", show=False),
        Binding("9", "sort_column(8)", show=False),
        Binding("0", "sort_column(9)", show=False),
        Binding("-", "sort_column(10)", show=False),
        Binding("=", "sort_column(11)", show=False),
        Binding("y", "yank()", "Copy field", show=True),
    ]

    def __init__(
        self, percent_columns: tuple[tuple[str | IconColumnCell, int], ...], **kwargs
    ):
        self.percent_columns = (
            percent_columns  # custom columns with (name, percent_ratio)
        )
        self._bulk_mode: bool = False
        self._active_sort: SortOrder | None = None
        self._original_labels: dict[str, Text | str] = {}

        super().__init__(**kwargs)

    def row_exists(self, key: str) -> bool:
        try:
            self.get_row(key)
            return True
        except RowDoesNotExist:
            return False

    @property
    def active_sort(self) -> SortOrder | None:
        return self._active_sort

    @property
    def has_active_sort(self) -> bool:
        return self._active_sort is not None

    def sort_items(self, items: Iterable[T]) -> list[T]:
        """Return a stable sorted copy, with None keys last in either direction."""
        order = self._active_sort
        if order is None:
            return list(items)

        key_func = self.SORT_KEYS[order.column]
        present: list[tuple[Any, T]] = []
        missing: list[T] = []
        for item in items:
            value = key_func(item)
            if value is None:
                missing.append(item)
            else:
                present.append((value, item))
        present.sort(key=lambda pair: pair[0], reverse=order.descending)
        return [item for _, item in present] + missing

    def reset_sort(self, *, notify: bool = False) -> None:
        """Clear sorting and restore its label; optionally emit SortChanged(None).

        An already unsorted table is a no-op. This does not reorder existing rows.
        """
        if self._active_sort is None:
            return
        self._restore_column_label(self._active_sort.column)
        self._active_sort = None
        if notify:
            self.post_message(self.SortChanged(None))

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

    def clear_table(self) -> None:
        self.clear(columns=False)
        self.post_message(VexDataTable.RowRemoved())

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
        total_padding = 2 * (self.cell_padding * len(self.percent_columns)) + 1
        one_percent = (total_width - total_padding) / 100

        for column, percent_width in self.percent_columns:
            width = round(percent_width * one_percent)
            if isinstance(column, IconColumnCell):
                self.add_column(label=column.icon, width=width, key=column.name)
                self._original_labels[column.name] = column.icon
            else:
                self.add_column(label=column, width=width, key=column)
                self._original_labels[column] = column

    @on(DataTable.HeaderSelected)
    def _on_column_header_selected(self, event: DataTable.HeaderSelected) -> None:
        event.stop()
        col_str = event.column_key.value
        if col_str is None:
            return
        self._toggle_sort(col_str)

    def action_sort_column(self, col_index: int) -> None:
        if not 0 <= col_index < len(self.ordered_columns):
            return
        col_key = self.ordered_columns[col_index].key.value
        if col_key is None:
            return
        self._toggle_sort(col_key)

    def _toggle_sort(self, col_str: str) -> None:
        if col_str not in self.SORT_KEYS:
            return

        previous = self._active_sort
        if previous is not None and previous.column == col_str:
            if previous.descending:
                self.reset_sort(notify=True)
                return
            order = SortOrder(col_str, descending=True)
        else:
            order = SortOrder(col_str)

        if previous is not None:
            self._restore_column_label(previous.column)
        self._active_sort = order
        self._apply_sort_label(col_str, order.descending)
        self.post_message(self.SortChanged(order))

    def _restore_column_label(self, col_str: str) -> None:
        original = self._original_labels.get(col_str)
        if original is not None:
            self._write_column_label(col_str, original)

    def _apply_sort_label(self, col_str: str, descending: bool) -> None:
        original = self._original_labels.get(col_str)
        if original is None:
            return
        component = (
            "vex-datatable--sort-asc"
            if not descending
            else "vex-datatable--sort-desc"
        )
        try:
            sort_style = self.get_component_rich_style(component)
        except KeyError:
            return
        label = original.copy() if isinstance(original, Text) else Text(str(original))
        label.stylize(sort_style)
        self._write_column_label(col_str, label)

    def _write_column_label(self, col_str: str, label: Text | str) -> None:
        for col in self.ordered_columns:
            if col.key.value == col_str:
                col.label = label if isinstance(label, Text) else Text(str(label))
                self._update_count += 1
                self._clear_caches()
                self.refresh()
                return

    def get_cell_raw_value(self, column_key: str, row_key: str) -> str | None:
        """Override in subclasses to return the raw value for a column in a row."""
        return None

    def action_yank(self) -> None:
        row_key = self.get_highlighted_row_key()
        if row_key is None:
            self.app.notify("No row selected", title="Vex")
            return

        column_values: list[tuple[str, str]] = []
        for col in self.ordered_columns:
            col_key = col.key.value
            if col_key is None:
                continue
            raw_value = self.get_cell_raw_value(col_key, row_key)
            display_value = str(raw_value) if raw_value is not None else ""
            column_values.append((col_key, display_value))

        if not column_values:
            self.app.notify("No data to copy", title="Vex")
            return

        from vex_client.modals.copy_palette import CopyPalette

        self.app.push_screen(CopyPalette(column_values))
