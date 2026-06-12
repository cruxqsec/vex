from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button
from textual.containers import Container, Horizontal

from vex_client.modals.inputs import AddressInput, PortInput
from vex_client.proxy.list import ProxyInstance


class CreateUpdateProxyScreen(ModalScreen[ProxyInstance]):
    """Screen with a dialog to create a new project."""

    CSS_PATH = "css/proxy_modal.tcss"
    BINDINGS = [
        ("escape", "cancel", "Close"),
        ("ctrl+c", "create", "Create proxy instance"),  # TODO: disable if update
        ("ctrl+u", "update", "Update proxy instance"),  # TODO: disable if create
    ]

    def __init__(self, instance: ProxyInstance | None, **kwargs):
        self.instance = instance
        super().__init__(**kwargs)

    @property
    def name_input(self) -> Input:
        return self.query_one("#proxy-modal-name-input", Input)

    @property
    def address_input(self) -> AddressInput:
        return self.query_one("#address-input", AddressInput)

    @property
    def proxy_port_input(self) -> PortInput:
        return self.query_one("#proxy-port-input", PortInput)

    @property
    def api_port_input(self) -> PortInput:
        return self.query_one("#api-port-input", PortInput)

    def compose(self) -> ComposeResult:
        with Container(id="create-modal"):
            yield Label("", id="title")
            with Horizontal():
                yield Label("Instance name: ", id="proxy-modal-name-label")
                yield Input(
                    placeholder="Instance name",
                    max_length=20,
                    type="text",
                    id="proxy-modal-name-input",
                )
            with Horizontal():
                yield Label("Listening address: ", id="address-label")
                yield AddressInput(placeholder="default: 127.0.0.1", id="address-input")
            with Horizontal():
                yield Label("Proxy port: ", id="proxy-port-label")
                yield PortInput(placeholder="default: 8080", id="proxy-port-input")
            with Horizontal():
                yield Label("API port: ", id="api-port-label")
                yield PortInput(placeholder="default: 9000", id="api-port-input")
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("", classes="btn")
                yield Button("\[Esc] Cancel", classes="btn", id="cancel-btn")

    def on_mount(self):
        create_update_btn = self.query("Button").first(Button)
        if self.instance:
            # we are updating an instance
            self.query_one("#title", Label).update("[b]Update proxy instance[/b]")
            create_update_btn.label = "\[ctrl+u] Update"
            create_update_btn.id = "update-btn"

            self.name_input.value = self.instance.name
            self.address_input.value = self.instance.server_address
            self.proxy_port_input.value = str(self.instance.proxy_port)
            self.api_port_input.value = str(self.instance.api_port)
        else:
            # we are creating
            self.query_one("#title", Label).update("[b]Create proxy instance[/b]")
            create_update_btn.label = "\[ctrl+c] Create"
            create_update_btn.id = "create-btn"

    @on(Input.Blurred)
    def name_input_empty(self, event: Input.Blurred):
        if self.name_input.value == "":
            self.query_one("#error-label", Label).update(
                "Instance name cannot be empty."
            )

    @on(AddressInput.Blurred)
    @on(PortInput.Blurred)
    def validate_inputs(self, event: PortInput.Blurred | AddressInput.Blurred):
        if event.validation_result is None:
            return

        error_label = self.query_one("#error-label", Label)
        if event.validation_result.is_valid:
            error_label.update("")
        else:
            error_label.update(event.validation_result.failure_descriptions[0])

    @on(Button.Pressed, "#update-btn")
    @on(Button.Pressed, "#create-btn")
    def create_update_instance(self):

        if (
            self.address_input.is_valid
            and self.proxy_port_input.is_valid
            and self.api_port_input.is_valid
            and len(self.name_input.value) != 0
        ):
            instance_data = ProxyInstance(
                self.name_input.value,
                self.address_input.value,
                int(self.proxy_port_input.value),
                int(self.api_port_input.value),
                self.instance.running if self.instance is not None else False,
            )
            self.dismiss(instance_data)

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self):
        self.app.pop_screen()

    def action_create(self):
        self.create_update_instance()

    def action_update(self):
        self.create_update_instance()

    def action_cancel(self):
        self.app.pop_screen()
