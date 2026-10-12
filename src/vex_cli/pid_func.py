import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from vex_cli.locations import vex_pid_file
from vex_cli.models.pydantic import PIDData, VexServerInfo

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def _acquire_file_lock(pid_file_fd: int) -> None:
    """Take an exclusive non-blocking lock on the whole pid file.

    Raises BlockingIOError (OSError with errno EAGAIN/EACCES) if another
    live process holds the lock.
    """
    if sys.platform == "win32":
        msvcrt.locking(pid_file_fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(pid_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def write_pid_file(host: str, proxy_port: int, api_port: int, pid_file: Path) -> None:
    """Write server information to pid file."""
    data = PIDData(pid=os.getpid(), host=host, proxy_port=proxy_port, api_port=api_port)
    pid_file.write_text(data.model_dump_json(indent=2))


def read_pid_file(pid_file: Path) -> PIDData:
    """Read server information from pid file."""
    data = PIDData.model_validate_json(pid_file.read_text())
    return data


@asynccontextmanager
async def pid_file_check(server_info: VexServerInfo):
    """Acquire the singleton lock and write our pid file for the server's lifetime.

    Usage: ``async with pid_file_check(server_info) as pid_file:``

    Raises RuntimeError("vex-cli is already running.") when another live
    instance holds the lock. On success the lock is held and the pid file
    written; both are released (by the OS, even after a crash) when the
    context exits.
    """
    pid_file = vex_pid_file()

    fd = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            _acquire_file_lock(fd)
        except OSError as e:
            raise RuntimeError("vex-cli is already running.") from e

        data = PIDData(
            pid=os.getpid(),
            host=str(server_info.server_address),
            proxy_port=server_info.proxy_port,
            api_port=server_info.api_port,
        )
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, data.model_dump_json(indent=2).encode())

        yield pid_file
    finally:
        # we just close the file descriptor so we release the lock
        # but we leave the file intentionally staleness is decided by holding the lock,
        # not by inspecting the pid and the kernel has already released the lock.
        os.close(fd)


def delete_pid_file(pid_file: Path) -> None:
    """Delete pid file (only meaningful while holding the lock)."""
    pid_file.unlink(missing_ok=True)
