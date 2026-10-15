from textual.app import App, ComposeResult

from vex_client.widgets.navigation_bar import InterceptButton


class InterceptButtonHarness(App[None]):
    def compose(self) -> ComposeResult:
        yield InterceptButton("Intercept")


async def test_intercept_button_starts_in_forwarding_state() -> None:
    app = InterceptButtonHarness()

    async with app.run_test():
        button = app.query_one(InterceptButton)

        assert button.is_active is False
        assert str(button.label) == " Forwarding"
        assert not button.has_class("intercepting")


async def test_intercept_button_click_toggles_to_intercepting() -> None:
    app = InterceptButtonHarness()

    async with app.run_test() as pilot:
        button = app.query_one(InterceptButton)
        await pilot.click(button)
        await pilot.pause()

        assert button.is_active is True
        assert str(button.label) == " Intercepting"
        assert button.has_class("intercepting")
