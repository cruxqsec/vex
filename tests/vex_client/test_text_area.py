from textual.app import App, ComposeResult
from textual.widgets import Static

from vex_client.widgets.text_area import VexTextArea, VexTextAreaWidget


class TextAreaHarness(App[None]):
    def get_vex_theme(self):
        return None

    def compose(self) -> ComposeResult:
        yield VexTextAreaWidget(
            VexTextArea("abc", read_only=True, id="test-text-area"),
            id="test-text-area-widget",
        )


async def test_v_key_toggles_visual_mode_and_status() -> None:
    app = TextAreaHarness()

    async with app.run_test() as pilot:
        text_area = app.query_one("#test-text-area", VexTextArea)
        mode_label = app.query_one("#vim-mode", Static)
        text_area.focus()

        await pilot.press("v")
        await pilot.pause()

        assert text_area.visual_mode is True
        assert text_area.has_class("visual-mode")
        assert mode_label.has_class("vim-visual")

        await pilot.press("v")
        await pilot.pause()

        assert text_area.visual_mode is False
        assert not text_area.has_class("visual-mode")
        assert not mode_label.has_class("vim-visual")


async def test_movement_in_visual_mode_selects_text() -> None:
    app = TextAreaHarness()

    async with app.run_test() as pilot:
        text_area = app.query_one("#test-text-area", VexTextArea)
        text_area.focus()

        await pilot.press("v", "l")
        await pilot.pause()

        assert text_area.visual_mode is True
        assert not text_area.selection.is_empty
        assert text_area.selected_text == "a"

        await pilot.press("v")
        await pilot.pause()

        assert text_area.visual_mode is False
        assert text_area.selection.is_empty
