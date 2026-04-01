import ipaddress

from textual.validation import Number, ValidationResult, Validator
from textual.widgets import Input


class IPv4Address(Validator):
    def validate(self, value: str) -> ValidationResult:
        """Check if a string is valid IPv4 address."""
        if self.is_valid_ipv4(value):
            return self.success()
        else:
            return self.failure("Not a valid IPv4 address!")

    @staticmethod
    def is_valid_ipv4(ip: str) -> bool:
        try:
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False


class PortInput(Input, can_focus=True):
    """Input to enter a port."""

    def on_mount(self):
        self.type = "integer"
        self.validators = [
            Number(minimum=0, maximum=65535, failure_description="Not a valid port!")
        ]


class AddressInput(Input, can_focus=True):
    """Input to enter an IP address."""

    def on_mount(self):
        self.type = "text"
        self.validators = [IPv4Address()]
