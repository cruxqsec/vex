from typing import List
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Input, Button
from textual.containers import Container, Horizontal

from vex_client.proxy.inputs import AddressInput, PortInput


@dataclass
class InstanceData:  # internal (just for passing to modal screen and back)
    name: str
    address: str
    proxy_port: int
    api_port: int


class CreateUpdateProxyScreen(ModalScreen[InstanceData]):
    """Screen with a dialog to create a new project."""

    CSS_PATH = "css/proxy_modal.tcss"

    def __init__(self, instance_data: InstanceData | None, **kwargs):
        self.instance_data = instance_data
        super().__init__(**kwargs)

    @property
    def name_input(self) -> Input:
        return self.query_one("#name-input", Input)

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
                yield Label("Instance name: ", id="name-label")
                yield Input(
                    placeholder="Instance name",
                    max_length=20,
                    type="text",
                    id="name-input",
                )
            with Horizontal():
                yield Label("Listening address: ", id="name-label")
                yield AddressInput(placeholder="default: 127.0.0.1", id="address-input")
            with Horizontal():
                yield Label("Proxy port: ", id="proxy-port-label")
                yield PortInput(placeholder="default: 8080", id="proxy-port-input")
            with Horizontal():
                yield Label("API port: ", id="api-port-label")
                yield PortInput(placeholder="default: 9000", id="api-port-input")
            yield Label("", id="error-label")
            with Horizontal():
                yield Button("", classes="func-btn")
                yield Button("Cancel", classes="func-btn", id="cancel-btn")

    def on_mount(self):
        create_update_btn = self.query("Button").first(Button)
        if self.instance_data is not None:
            # we are updating an instance
            self.query_one("#title", Label).update("[b]Update proxy instance[/b]")
            create_update_btn.label = "Update"
            create_update_btn.id = "update-btn"

            self.name_input.value = self.instance_data.name
            self.address_input.value = self.instance_data.address
            self.proxy_port_input.value = str(self.instance_data.proxy_port)
            self.api_port_input.value = str(self.instance_data.api_port)
        else:
            self.query_one("#title", Label).update("[b]Create proxy instance[/b]")
            create_update_btn.label = "Create"
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
            instance_data = InstanceData(
                self.name_input.value,
                self.address_input.value,
                int(self.proxy_port_input.value),
                int(self.api_port_input.value),
            )
            self.dismiss(instance_data)

    @on(Button.Pressed, "#cancel-btn")
    def cancel_btn(self):
        self.app.pop_screen()
