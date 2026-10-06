import asyncio
import sys
from subprocess import Popen

import psutil

from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import VexServerInfo
from vex_client.process import (
    INACTIVE_PROCESS,
    is_vex_server_live,
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

    def attach(self, pid: int, server_info: VexServerInfo) -> None:
        """Adopt an already-running server (e.g. discovered via the pid file)."""
        self.cli_pid = pid
        self.server_info = server_info
        self._proc = None

    def clear(self) -> None:
        """Reset to no-server state once the server is gone."""
        self.cli_pid = INACTIVE_PROCESS
        self.server_info = None
        self._proc = None

    @property
    def is_cli_running(self):
        if self.cli_pid == INACTIVE_PROCESS:
            return False

        if self._proc is not None:
            # Own child: waitpid-based; correct across PID reuse and reaps
            # the zombie.
            return self._proc.poll() is None

        # Adopted (pid-file) server: liveness is the file lock, not the
        # pid — same kernel-guarantee as the client adoption gate.
        return is_vex_server_live(vex_pid_file())

    async def start_vex_cli(self, server_info: VexServerInfo) -> bool:

        cmd = [
            sys.executable,
            "-m",
            "vex_cli",
            "start",
            "--address",
            server_info.server_address,
            "--proxy-port",
            str(server_info.proxy_port),
            "--api-port",
            str(server_info.api_port),
        ]

        proc = await asyncio.to_thread(start_detached_process, cmd)
        if proc is None:
            self.clear()
            return False

        self.attach(proc.pid, server_info)
        self._proc = proc
        return True

    async def stop_vex_cli(self) -> bool:
        if self.cli_pid == INACTIVE_PROCESS:
            return False

        stopped = await asyncio.to_thread(self._stop_sync)

        if stopped:
            self.clear()
        return stopped

    def _stop_sync(self) -> bool:
        try:
            verify_vex = self._proc is None
            terminated = terminate_process(self.cli_pid, verify_vex=verify_vex)
            if terminated and not psutil.pid_exists(self.cli_pid):
                return True

            # if graceful termination doesn't work then we kill it
            return kill_process(self.cli_pid, verify_vex=verify_vex)
        except psutil.Error:
            return False