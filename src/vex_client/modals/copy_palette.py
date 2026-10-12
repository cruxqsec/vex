from textual.app import ComposeResult
from textual.binding import Binding
from textual.command import CommandInput, CommandList, SearchIcon
from textual.containers import Horizontal, Vertical
from textual.fuzzy import Matcher
from textual.screen import ModalScreen
from textual.widgets.option_list import Option

import logging

import pyperclip

logger = logging.getLogger(__name__)


class CopyPalette(ModalScreen[None]):
    CSS_PATH = "css/copy_palette.tcss"

    AUTO_FOCUS = "CommandInput"

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
    ]

    def __init__(self, column_values: list[tuple[str, str]]):
        super().__init__()
        self.column_values = column_values

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="--input"):
                yield SearchIcon()
                yield CommandInput(
                    placeholder="Type a column to copy...",
                    select_on_focus=False,
                )
            yield CommandList()

    def on_mount(self) -> None:
        self._populate_options()

    def _populate_options(self, filter_text: str = "") -> None:
        cl = self.query_one(CommandList)
        cl.clear_options()

        if not filter_text:
            for col_name, raw_value in self.column_values:
                display = str(raw_value) if raw_value else "(empty)"
                prompt = f"{col_name}  →  {display}"
                cl.add_option(Option(prompt, id=col_name))
        else:
            matcher = Matcher(filter_text)
            scored: list[tuple[float, str, str]] = []
            for col_name, raw_value in self.column_values:
                score = matcher.match(col_name)
                if score > 0:
                    scored.append((score, col_name, raw_value))
            scored.sort(key=lambda x: x[0], reverse=True)
            for score, col_name, raw_value in scored:
                display = str(raw_value) if raw_value else "(empty)"
                prompt = matcher.highlight(f"{col_name}  →  {display}")
                cl.add_option(Option(prompt, id=col_name))

        if cl.option_count > 0:
            cl.highlighted = 0
            cl.add_class("--visible")
        else:
            cl.remove_class("--visible")

    def on_input_changed(self, event: CommandInput.Changed) -> None:
        self._populate_options(event.value)

    def on_input_submitted(self, event: CommandInput.Submitted) -> None:
        event.stop()
        self._select_highlighted()

    def on_option_list_option_selected(self, event: CommandList.OptionSelected) -> None:
        event.stop()
        if event.option_id:
            self._copy_and_dismiss(event.option_id)

    def action_cursor_up(self) -> None:
        cl = self.query_one(CommandList)
        if cl.option_count > 0:
            cl.action_cursor_up()

    def action_cursor_down(self) -> None:
        cl = self.query_one(CommandList)
        if cl.option_count > 0:
            cl.action_cursor_down()

    def action_dismiss(self) -> None:
        self.dismiss()

    def _select_highlighted(self) -> None:
        cl = self.query_one(CommandList)
        if cl.highlighted is not None:
            try:
                option = cl.get_option_at_index(cl.highlighted)
                if option.id:
                    self._copy_and_dismiss(option.id)
            except Exception:
                pass

    def _copy_and_dismiss(self, col_name: str) -> None:
        value = ""
        for n, v in self.column_values:
            if n == col_name:
                value = str(v) if v is not None else ""
                break
        if value:
            try:
                pyperclip.copy(value)
            except pyperclip.PyperclipException:
                self.app.notify(
                    "Clipboard unavailable. Check logs.", severity="error"
                )
                logger.exception("pyperclip.copy failed")
            else:
                self.app.notify(f"Copied {col_name}: {value}", title="Vex")
        self.dismiss()
