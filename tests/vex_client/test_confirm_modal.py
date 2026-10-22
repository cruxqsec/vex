import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from vex_client.modals.confirm import ConfirmModal


class ConfirmHarness(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.result: bool | None = None

    def compose(self) -> ComposeResult:
        yield Static("Test app")

    def on_mount(self) -> None:
        self.push_screen(ConfirmModal("Delete this item?"), self._save_result)

    def _save_result(self, result: bool | None) -> None:
        self.result = result


@pytest.fixture
def confirm_app() -> ConfirmHarness:
    return ConfirmHarness()


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("yes", True),
        ("no", False),
        ("escape", False),
    ],
)
async def test_confirm_modal_returns_expected_result(
    confirm_app: ConfirmHarness,
    action: str,
    expected: bool,
) -> None:
    async with confirm_app.run_test() as pilot:
        if action == "yes":
            await pilot.click("#confirm-yes")
        elif action == "no":
            await pilot.click("#confirm-no")
        else:
            await pilot.press("escape")

        await pilot.pause()

    assert confirm_app.result is expected
