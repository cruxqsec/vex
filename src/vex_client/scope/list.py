from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from vex_client.app import VexApp

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import (
    ListItem,
    ListView,
    Static,
)

from vex_cli.models.pydantic import Scope
from vex_client.widgets.button import VexButton
from vex_client.widgets.empty_message_widget import (
    EmptyMessageWidget,
    EmptyStateChanged,
)


class ScopeListWidget(Vertical):
    def compose(self) -> ComposeResult:
        with Horizontal(id="scope-list-header"):
            yield Static(" SCOPES ", id="scope-list-title")
            yield VexButton("\[c] Create", id="btn-create", classes="btn")
        yield ScopeListEmpty(id="empty-scope-list")
        yield Static("↵ to select a scope", id="scope-list-helper")


class ScopeListEmpty(EmptyMessageWidget):
    """
    Scope list widget used for displaying scopes, with an empty message when empty.
    """

    def __init__(self, **kwargs):
        self.scope_list = ScopeList(*[], id="scope-list")
        super().__init__(
            widget=self.scope_list,
            empty_message="No scopes available.",
            **kwargs,
        )


class ScopeList(ListView, can_focus=True):
    """
    ListView for displaying the scopes
    """

    BINDINGS: ClassVar = [
        Binding("enter", "select_cursor", "Start/Enter instance"),
        Binding("k", "cursor_up", "up"),
        Binding("j", "cursor_down", "down"),
    ]

    def on_mount(self) -> None:
        self.post_message(EmptyStateChanged(is_empty=self._is_empty()))

    def add_scopes(self, scopes: list[Scope]) -> None:
        for scope in scopes:
            self.append(ScopeListItem(scope))
        self.post_message(EmptyStateChanged(is_empty=self._is_empty()))

    def append_scope(self, scope_item: ScopeListItem) -> None:
        self.append(scope_item)
        self.post_message(EmptyStateChanged(is_empty=self._is_empty()))

        # select and highlight the item after it was created
        index = sum(1 for c in self.children if isinstance(c, ScopeListItem)) - 1
        self.post_message(ListView.Selected(self, scope_item, index))
        self.index = index

    def pop_scope(self, selected_item) -> None:
        try:
            index = self._nodes.index(selected_item)
        except ValueError:
            return

        # we have to count because otherwise the message is posted before
        # the element is fully removed causing it to fail the is_empty check
        count = sum(1 for c in self.children if isinstance(c, ScopeListItem))
        if count == 1:
            self.post_message(EmptyStateChanged(is_empty=True))

        self.pop(index)

    def deselect_selected(self) -> None:
        for list_item in self.children:
            if not isinstance(list_item, ScopeListItem):
                continue
            elif "selected" in list_item.classes:
                list_item.toggle_selected_off()

    def _is_empty(self) -> bool:
        return sum(1 for c in self.children if isinstance(c, ScopeListItem)) == 0


class ScopeListItem(ListItem):
    """
    Proxy list item with a status_dot.
    """

    def __init__(self, scope: Scope, active: bool = False, **kwargs) -> None:
        self.scope = scope
        self.scope_active = active
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal(classes="row-inner"):
            yield Static("○", id="scope-dot", classes="row-indicator")
            yield Static("", id="scope-name", classes="row-name")

    def on_mount(self) -> None:
        self.query_one("#scope-name", Static).content = self.scope.name

    def toggle_selected_on(self) -> None:
        self.query_one("#scope-dot", Static).content = "●"
        self.add_class("selected")

    def toggle_selected_off(self) -> None:
        self.query_one("#scope-dot", Static).content = "○"
        self.remove_class("selected")
