import pytest

from vex_cli.bind import try_bind_ports
from vex_cli.models.pydantic import VexServerInfo


@pytest.fixture
def mock_vex_server_info():
    return VexServerInfo(server_address="127.0.0.1", proxy_port=8080, api_port=8090)


def test_try_bind_ports(mock_vex_server_info):
    assert try_bind_ports(mock_vex_server_info) == (True, -1)


def test_try_bind_ports_no_permission(mock_vex_server_info):
    mock_vex_server_info.api_port = 80
    assert try_bind_ports(mock_vex_server_info) == (False, 80)
