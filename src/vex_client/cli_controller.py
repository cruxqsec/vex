import psutil
import socket

from vex_cli.models import VexServerInfo
from vex_cli.bind import try_bind_ports

from vex_client.process import (
    start_detached_process,
    terminate_process,
    kill_process,
    INACTIVE_PROCESS
)

class VexController():
    """
    Controller for the vex-cli server
    """

    def __init__(self):
        self.server_info: VexServerInfo | None = None
        self.cli_pid: int = INACTIVE_PROCESS
    
    @property
    def is_cli_running(self):
        if self.cli_pid == INACTIVE_PROCESS:
            return False
        return True
    
    def get_server_info(self) -> VexServerInfo | None:
        return self.server_info

    def set_server_info(self, server_info: VexServerInfo) -> None:
        self.server_info = server_info
    
    def get_pid(self) -> int:
        return self.cli_pid
    
    def set_pid(self, pid: int) -> None:
        self.cli_pid = pid

    def try_bind_ports(self, server_info: VexServerInfo) -> tuple[bool,int]:
        """Check if we can bind to both ports"""
        address = server_info.server_address
        to_check = [(address, server_info.proxy_port),
                    (address, server_info.api_port)]

        for address, port in to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((address, port))
            except OSError:
                return False, port
        return True, -1
        
    def start_vex_cli(self, server_info: VexServerInfo) -> bool:
        
        cmd = ["vex-cli", "start", "--address", server_info.server_address,
               "--proxy-port", str(server_info.proxy_port),
               "--api-port", str(server_info.api_port)
        ]

        pid = start_detached_process(cmd) 
        
        if pid == INACTIVE_PROCESS:
            self.cli_pid = INACTIVE_PROCESS
            return False
        
        self.server_info = server_info
        self.cli_pid = pid
        return True

    def stop_vex_cli(self) -> bool:
        if self.cli_pid == INACTIVE_PROCESS:
            return False

        try:
            terminated = terminate_process(self.cli_pid)

            if terminated and not psutil.pid_exists(self.cli_pid):
                return True

            # if graceful termination doesn't work then we kill it
            kill_process(self.cli_pid)
            return True

        finally:
            self.cli_pid = INACTIVE_PROCESS
            self.server_info = None
        