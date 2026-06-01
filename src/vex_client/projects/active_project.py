from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Rule

from vex_client.widgets.button import VexButton
 
class ActiveProjectCard(Widget):
    """
    Left-border style card showing active project info.
    Hidden by default, shown when a project is active.
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="ap-name")
        yield Rule(id="ap-rule")
        with Horizontal(classes="ap-row"):
            yield Static("Flows", classes="ap-label")
            yield Static("", id="ap-flows", classes="ap-value ap-green")
        with Horizontal(classes="ap-row"):
            yield Static("Scopes", classes="ap-label")
            yield Static("", id="ap-scopes", classes="ap-value")
        with Horizontal(classes="ap-row"):
            yield Static("Replays", classes="ap-label")
            yield Static("", id="ap-replays", classes="ap-value")
        with Horizontal(classes="ap-row"):
            yield VexButton("\[e] Export", id="btn-export", classes="btn")
            yield VexButton("\[p] Copy path", id="btn-copy-path", classes="btn")

    def set_project(self, name: str, flows: str, scopes: str, replays: str) -> None:
        self.query_one("#ap-name", Static).update(f"● {name}")
        self.query_one("#ap-flows", Static).update(flows)
        self.query_one("#ap-scopes", Static).update(scopes)
        self.query_one("#ap-replays", Static).update(replays)

        self.remove_class("not-active")

    def set_empty(self) -> None:
        self.add_class("not-active")
        self.query_one("#ap-name", Static).update("● No project active")


class ActiveProjectWidget(Widget):
    """
    Right panel container — section title, active card or empty state.
    """

    def compose(self) -> ComposeResult:
        yield Static("Active project", id="ap-section-title")
        yield ActiveProjectCard(id="active-project-card")
