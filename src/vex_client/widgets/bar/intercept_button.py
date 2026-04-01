from textual.widgets import Button


class InterceptButton(Button, can_focus=False):
    """
    Button for interception. Can be in 2 states. Forwarding and intercepting.
    """

    DEFAULT_CSS = """
    
        InterceptButton {
            width: 1fr;
            height: 1fr;
            max-height: 3;
            max-width: 20;
            background: $background !important;
            outline: round $success;
            color: $success !important;

            &:hover {
                background: transparent !important;
                tint: $background 0%;
            }
        }
        
        InterceptButton.intercepting {
            outline: round $error;
            background: $background;
            color: $error !important;
            text-opacity: 0.8;
            
            &:hover {
                background: transparent !important;
                tint: $background 0%;
            }

        }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_active = True
        self.toggle()  # Toggle it to be forwarding by default

    def toggle(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.add_class("intercepting")
            self.label = "⏸ Intercepting"
        else:
            self.remove_class("intercepting")
            self.label = "⏩ Forwarding"

    def on_button_pressed(self):
        self.toggle()
