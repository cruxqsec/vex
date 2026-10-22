import asyncio
import logging
import sys
from subprocess import Popen

import psutil

from vex_cli.models.pydantic import VexServerInfo
from vex_client.process import (
    INACTIVE_PROCESS,
    kill_process,
    start_detached_process,
    terminate_process,
)

logger = logging.getLogger(__name__)



class LocalServerController:
    """
    Local controller for the vex-cli server.

    Controls the local vex-cli server that was spawned
    or already running and adopted. Operates only on a local process
    and has nothing to do with connecting to the server.
    """

    def __init__(self):
        self.server_info: VexServerInfo | None = None
        self.cli_pid: int = INACTIVE_PROCESS
        self._starting = False

        # set if this process spawns a new vex-cli
        self._proc: Popen | None = None

        # set if we attach to an already running vex-cli
        self._adopted_proc: psutil.Process | None = None

    @property
    def is_cli_running(self) -> bool:
        if self._proc is not None:
            return self._proc.poll() is None

        if self._adopted_proc is not None:
            try:
                return (
                    self._adopted_proc.is_running()
                    and self._adopted_proc.status() != psutil.STATUS_ZOMBIE
                )
            except psutil.NoSuchProcess:
                return False

        return False

    def attach_to_running(
        self, process: psutil.Process, server_info: VexServerInfo
    ) -> bool:
        """Track a local process whose identity was verified during discovery."""
        if self._starting:
            return False
        if self.server_info is not None:
            raise RuntimeError("Disconnect the current instance first.")

        if not process.is_running():
            return False

        self.server_info = server_info.model_copy()
        self.cli_pid = process.pid
        self._proc = None
        self._adopted_proc = process
        return True

    async def spawn_vex_cli(self, server_info: VexServerInfo) -> bool:
        """Spawn and track a local vex-cli server; readiness is checked separately."""

        if self._starting:
            return False
        if self._proc is not None or self._adopted_proc is not None:
            raise RuntimeError("A local process is already tracked; stop it first.")

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

        # Prevent another start or adoption while the launch is awaiting a process.
        self._starting = True
        try:
            proc = await asyncio.to_thread(start_detached_process, cmd)
            if proc is None:
                return False

            self.server_info = server_info
            self.cli_pid = proc.pid
            self._proc = proc
            self._adopted_proc = None
            return True
        finally:
            self._starting = False


    async def stop_vex_cli(self) -> bool:
        """Stop the tracked local process, escalate if necessary."""
        process = self._proc if self._proc is not None else self._adopted_proc

        if process is None:
            return False

        stopped = await asyncio.to_thread(terminate_process, process)

        if not stopped:
            stopped = await asyncio.to_thread(kill_process, process)

        if stopped and (self._proc is process or self._adopted_proc is process):
            self.clear()

        return stopped

    def clear(self) -> None:
        """Reset to no-server state once the server is gone."""
        self.cli_pid = INACTIVE_PROCESS
        self.server_info = None
        self._proc = None
        self._adopted_proc = None
