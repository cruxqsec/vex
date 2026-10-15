import pytest

from vex_cli.bind import try_bind_ports
from vex_cli.models.pydantic import VexServerInfo


def test_try_bind_ports(server_info: VexServerInfo):
    assert try_bind_ports(server_info) == (True, -1)


def test_try_bind_ports_no_permission(server_info: VexServerInfo):
    server_info.api_port = 80
    assert try_bind_ports(server_info) == (False, 80)
