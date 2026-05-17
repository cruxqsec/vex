from textual.reactive import reactive
from textual.widgets import Static


class Status(Static):
    state = reactive("Shutdown")

    def render(self):
        return self.state
