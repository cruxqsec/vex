import os
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import ValidationError

from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import PIDData, VexServerInfo


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def write_pid_file(host: str, proxy_port: int, api_port: int, pid_file: Path) -> None:
    """Write server information to pid file."""

    data = PIDData(pid=os.getpid(), host=host, proxy_port=proxy_port, api_port=api_port)

    pid_file.write_text(data.model_dump_json(indent=2))


def read_pid_file(pid_file: Path) -> PIDData:
    """Read server information from pid file (we should check before that it exists)"""
    data = PIDData.model_validate_json(pid_file.read_text())
    return data


def delete_pid_file(pid_file: Path) -> None:
    """Delete pid file."""
    pid_file.unlink(missing_ok=True)


@asynccontextmanager
async def pid_file_check(server_info: VexServerInfo):
    pid_file = vex_pid_file()

    if pid_file.exists():
        try:
            pid_file_data = read_pid_file(pid_file)
            if is_process_running(pid_file_data.pid):
                raise RuntimeError("vex-cli is already running.")
            delete_pid_file(pid_file)
        except (OSError, ValidationError):
            delete_pid_file(pid_file)

    write_pid_file(
        str(server_info.server_address),
        server_info.proxy_port,
        server_info.api_port,
        pid_file,
    )

    try:
        yield pid_file
    finally:
        delete_pid_file(pid_file)
