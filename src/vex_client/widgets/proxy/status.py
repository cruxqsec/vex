from textual.widgets import Static
from textual.reactive import reactive

class Status(Static):
    state = reactive("Shutdown")
    
    def render(self):
        return self.state
