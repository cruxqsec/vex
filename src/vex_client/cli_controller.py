import asyncio
from subprocess import Popen

import psutil

from vex_cli.models.pydantic import VexServerInfo
from vex_client.process import (
    INACTIVE_PROCESS,
    kill_process,
    start_detached_process,
    terminate_process,
)


class VexController:
    """Controller for the vex-cli server."""

    def __init__(self):
        self.server_info: VexServerInfo | None = None
        self.cli_pid: int = INACTIVE_PROCESS
        self._proc: Popen | None = None

    @property
    def is_cli_running(self):
        if self.cli_pid == INACTIVE_PROCESS:
            return False

        if self._proc is not None:
            return self._proc.poll() is None

        try:
            process = psutil.Process(self.cli_pid)
        except psutil.NoSuchProcess:
            return False
        return process.status() != psutil.STATUS_ZOMBIE

    def start_vex_cli(self, server_info: VexServerInfo) -> bool:

        cmd = [
            "vex-cli",
            "start",
            "--address",
            server_info.server_address,
            "--proxy-port",
            str(server_info.proxy_port),
            "--api-port",
            str(server_info.api_port),
        ]

        proc = start_detached_process(cmd)
        if proc is None:
            self._proc = None
            self.cli_pid = INACTIVE_PROCESS
            return False

        self.server_info = server_info
        self._proc = proc
        self.cli_pid = proc.pid
        return True

    async def stop_vex_cli(self) -> bool:
        if self.cli_pid == INACTIVE_PROCESS:
            return False

        stopped = await asyncio.to_thread(self._stop_sync)

        if stopped:
            self._proc = None
            self.cli_pid = INACTIVE_PROCESS
            self.server_info = None
        return stopped

    def _stop_sync(self) -> bool:
        try:
            terminated = terminate_process(self.cli_pid)
            if terminated and not psutil.pid_exists(self.cli_pid):
                return True

            # if graceful termination doesn't work then we kill it
            return kill_process(self.cli_pid)
        except psutil.Error:
            return False