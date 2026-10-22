import socket

from vex_cli.models.pydantic import VexServerInfo


def try_bind_ports(server_info: VexServerInfo) -> tuple[bool, int]:
    """Check if we can bind to both ports"""
    if server_info.proxy_port == server_info.api_port and server_info.proxy_port != 0:
        return False, server_info.api_port

    to_check = [
        (server_info.server_address, server_info.proxy_port),
        (server_info.server_address, server_info.api_port),
    ]

    for address, port in to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((address, port))
        except OSError:
            return False, port
    return True, -1
