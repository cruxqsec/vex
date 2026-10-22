from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

if TYPE_CHECKING:
    from vex_client.app import VexApp

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, TextArea
from textual.widgets.text_area import Selection

from vex_client.get_syntax import get_highlight_query, get_http_lang
from vex_client.widgets.empty_message_widget import EmptyStateChanged


class VexTextArea(TextArea, can_focus=True):
    """
    Vex text area with VIM keybindings and custom syntax highlight.
    """

    BINDINGS: ClassVar = [
        Binding("up,k", "cursor_up", "Cursor Up", show=False),
        Binding("down,j", "cursor_down", "Cursor Down", show=False),
        Binding("right,l", "cursor_right", "Cursor Right", show=False),
        Binding("left,h", "cursor_left", "Cursor Left", show=False),
        Binding("shift+up,K", "cursor_up(True)", "cursor up select", show=False),
        Binding("shift+down,J", "cursor_down(True)", "cursor down select", show=False),
        Binding("shift+left,H", "cursor_left(True)", "cursor left select", show=False),
        Binding(
            "shift+right,L", "cursor_right(True)", "cursor right select", show=False
        ),
        Binding("ctrl+left,b", "cursor_word_left", "cursor word left", show=False),
        Binding("ctrl+right,w", "cursor_word_right", "cursor word right", show=False),
        Binding(
            "home,ctrl+a,0,^", "cursor_line_start", "cursor line start", show=False
        ),
        Binding("end,ctrl+e,$", "cursor_line_end", "cursor line end", show=False),
        Binding("pageup,ctrl+b", "cursor_page_up", "cursor page up", show=False),
        Binding("pagedown,ctrl+f", "cursor_page_down", "cursor page down", show=False),
        Binding(
            "ctrl+shift+left,B",
            "cursor_word_left(True)",
            "cursor left word select",
            show=False,
        ),
        Binding(
            "ctrl+shift+right,W",
            "cursor_word_right(True)",
            "cursor right word select",
            show=False,
        ),
        Binding("f6,V", "select_line", "select line", show=False),
        Binding(
            "v",
            "toggle_visual_mode",
            description="Toggle visual mode",
            show=False,
        ),
        Binding(
            "y,c",
            "copy_to_clipboard",
            description="Copy selection",
            show=False,
        ),
        Binding("g", "cursor_top", "Go to top", show=False),
        Binding("G", "cursor_bottom", "Go to bottom", show=False),
        Binding("ctrl+y", "copy", "Copy", show=False),
    ]

    """
    The vim visual mode implementation and the other functions are taken from the amazing Posting project.
    Reference: https://github.com/darrenburns/posting/blob/main/src/posting/widgets/text_area.py
    """

    def on_mount(self) -> None:
        self.register_language(
            name="http",
            language=get_http_lang(),
            highlight_query=get_highlight_query(),
        )
        self.language = "http"

        self.apply_vex_theme()

    def apply_vex_theme(self) -> None:
        app = cast("VexApp", self.app)
        vex_theme = app.get_vex_theme()
        if vex_theme is None:
            return
        ta_theme = vex_theme.to_text_area_theme()
        self.register_theme(ta_theme)
        self.theme = ta_theme.name


    """ ! IMPORTANT ! Visual mode for now works only if read_only=True! """
    @dataclass
    class VisualModeToggled(Message):
        value: bool
        text_area: TextArea

        @property
        def control(self) -> TextArea:
            return self.text_area

    visual_mode = reactive(False, init=False)

    def action_toggle_visual_mode(self):
        self.visual_mode = not self.visual_mode

    def watch_visual_mode(self, value: bool) -> None:
        self.cursor_blink = value
        if not value:
            self.selection = Selection.cursor(self.selection.end)

        self.set_class(value, "visual-mode")
        self.post_message(self.VisualModeToggled(value, self))

    def action_cursor_up(self, select: bool = False) -> None:
        return super().action_cursor_up(self.visual_mode or select)

    def action_cursor_right(self, select: bool = False) -> None:
        return super().action_cursor_right(self.visual_mode or select)

    def action_cursor_down(self, select: bool = False) -> None:
        return super().action_cursor_down(self.visual_mode or select)

    def action_cursor_left(self, select: bool = False) -> None:
        return super().action_cursor_left(self.visual_mode or select)

    def action_cursor_line_end(self, select: bool = False) -> None:
        return super().action_cursor_line_end(self.visual_mode or select)

    def action_cursor_line_start(self, select: bool = False) -> None:
        return super().action_cursor_line_start(self.visual_mode or select)

    def action_cursor_word_left(self, select: bool = False) -> None:
        return super().action_cursor_word_left(self.visual_mode or select)

    def action_cursor_word_right(self, select: bool = False) -> None:
        return super().action_cursor_word_right(self.visual_mode or select)

    def action_copy_to_clipboard(self) -> None:
        if self.visual_mode and not self.selection.is_empty:
            start, end = sorted([self.selection.start, self.selection.end])

            inclusive_end = (end[0], end[1] + 1)
            text_to_copy = self.get_text_range(start, inclusive_end)
        else:
            text_to_copy = self.selected_text
        if text_to_copy:
            message = f"Copied {len(text_to_copy)} characters."
            title = "Selection copied"
        else:
            text_to_copy = self.text
            message = f"Copied ({len(text_to_copy)} characters)."
            title = "Text copied"

        try:
            import pyperclip

            pyperclip.copy(text_to_copy)
        except pyperclip.PyperclipException as exc:
            self.notify(
                str(exc),
                title="Clipboard error",
                severity="error",
                timeout=10,
            )
        else:
            self.notify(message, title=title)

        self.visual_mode = False

    def action_cursor_top(self) -> None:
        self.selection = Selection.cursor((0, 0))

    def action_cursor_bottom(self) -> None:
        self.selection = Selection.cursor((self.document.line_count - 1, 0))

    class Focused(Message):
        pass

    class Blurred(Message):
        pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self.post_message(EmptyStateChanged(is_empty=self.text == ""))

    def on_focus(self) -> None:
        self.post_message(self.Focused())

    def on_blur(self) -> None:
        self.post_message(self.Blurred())


class VexTextAreaWidget(Vertical):
    """
    Widget that uses VexTextArea plus a vim like status bar
    """

    def __init__(self, text_area: VexTextArea, **kwargs):
        self.text_area = text_area
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield self.text_area
        with Horizontal(id="vim-status-bar"):
            yield Static("NORMAL", id="vim-mode")
            yield Static("", id="vim-position")

    def on_mount(self) -> None:
        mode = "VISUAL" if self.text_area.visual_mode else "NORMAL"
        self._update_mode(mode)
        self._update_position()

    @on(VexTextArea.VisualModeToggled, selector="VexTextArea")
    def _on_visual_mode_toggled(self, event: VexTextArea.VisualModeToggled):
        mode = "VISUAL" if event.value else "NORMAL"
        self._update_mode(mode)

    def _update_mode(self, mode: str) -> None:
        label = self.query_one("#vim-mode", Static)
        label.update(f"{mode}")
        label.set_class(mode == "VISUAL", "vim-visual")

    @on(TextArea.SelectionChanged, selector="VexTextArea")
    def _on_selection_changed(self, event: TextArea.SelectionChanged):
        if event.text_area is not self.text_area:
            return
        self._update_position()

    def _update_position(self) -> None:
        cursor = self.text_area.cursor_location
        pos = self.query_one("#vim-position", Static)
        row, col = cursor  # 0-based
        pos.update(f"{row + 1}:{col + 1}")
