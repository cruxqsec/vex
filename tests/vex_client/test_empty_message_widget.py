from textual.app import App, ComposeResult
from textual.widgets import Static

from vex_client.widgets.empty_message_widget import (
    EmptyMessageWidget,
    EmptyStateChanged,
)


class EmptyMessageHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield EmptyMessageWidget(
            Static("Items go here"),
            "No items",
            id="items-empty-state",
        )


async def test_empty_message_widget_tracks_empty_state() -> None:
    app = EmptyMessageHarness()

    async with app.run_test() as pilot:
        empty_widget = app.query_one("#items-empty-state", EmptyMessageWidget)
        assert empty_widget.has_class("empty")

        empty_widget.post_message(EmptyStateChanged(is_empty=False))
        await pilot.pause()
        assert not empty_widget.has_class("empty")

        empty_widget.post_message(EmptyStateChanged(is_empty=True))
        await pilot.pause()
        assert empty_widget.has_class("empty")
