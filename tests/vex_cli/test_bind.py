import errno
import os
import socket

import pytest
from pytest_mock import MockerFixture

from vex_cli.bind import try_bind_ports
from vex_cli.models.pydantic import VexServerInfo


def test_try_bind_ports_checks_both_ports(server_info: VexServerInfo, mocker: MockerFixture):
    socket_factory = mocker.patch("vex_cli.bind.socket.socket")
    bound_socket = socket_factory.return_value.__enter__.return_value

    assert try_bind_ports(server_info) == (True, -1)
    assert bound_socket.bind.call_args_list == [
        mocker.call(("127.0.0.1", 8080)),
        mocker.call(("127.0.0.1", 8081)),
    ]
    assert socket_factory.call_count == 2
    assert socket_factory.call_args_list == [
        mocker.call(socket.AF_INET, socket.SOCK_STREAM),
        mocker.call(socket.AF_INET, socket.SOCK_STREAM),
    ]


@pytest.mark.parametrize(
    ("failed_port", "error"),
    [(8080, errno.EADDRINUSE), (8081, errno.EACCES)],
)
def test_try_bind_ports_reports_first_failed_port(
    server_info: VexServerInfo,
    mocker: MockerFixture,
    failed_port: int,
    error: int,
):
    socket_factory = mocker.patch("vex_cli.bind.socket.socket")
    bound_socket = socket_factory.return_value.__enter__.return_value

    def bind(address: tuple[str, int]) -> None:
        if address[1] == failed_port:
            raise OSError(error, os.strerror(error))

    bound_socket.bind.side_effect = bind

    assert try_bind_ports(server_info) == (False, failed_port)
    assert bound_socket.bind.call_count == (1 if failed_port == 8080 else 2)


def test_try_bind_ports_rejects_identical_ports(
    server_info: VexServerInfo, mocker: MockerFixture
):
    socket_factory = mocker.patch("vex_cli.bind.socket.socket")
    server_info.api_port = server_info.proxy_port

    assert try_bind_ports(server_info) == (False, server_info.proxy_port)
    socket_factory.assert_not_called()
