"""Process-level startup gate for vex-cli.

The pid file doubles as an advisory lock: the first line of defense is an
exclusive non-blocking file lock held for the lifetime of the server. The
kernel releases the lock when the owning process dies (crash or clean exit
alike), so a lock means "a live instance is running" and no lock means the
file may be stale — the pid stored inside is never trusted for liveness.

Locking primitives are platform-specific: fcntl.flock on POSIX, msvcrt
region locks on Windows. Note that uvicorn/mitmproxy stack still has other
POSIX-only dependencies (e.g. loop.add_signal_handler is gone now, but
signal handling is owned by uvicorn which handles both platforms' SIGINT;
SIGTERM delivery differs on Windows).
"""

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
    """Read server information from pid file.

    Liveness is never inferred from the pid: the file serves as metadata for
    clients (health adoption); the startup gate uses the file lock instead.
    """
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

    # O_RDWR|O_CREAT; never O_TRUNC here — truncating before we own the lock
    # would clobber a live instance's metadata.
    fd = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            _acquire_file_lock(fd)
        except OSError as e:
            raise RuntimeError("vex-cli is already running.") from e

        # We own the lock: any previous content is stale, rewrite it.
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
        os.close(fd)
        # Keep the file itself: clients use its metadata for adoption and
        # health checks. Staleness is decided by holding the lock, not by
        # inspecting the pid. The kernel has already released the lock.


def delete_pid_file(pid_file: Path) -> None:
    """Delete pid file (only meaningful while holding the lock)."""
    pid_file.unlink(missing_ok=True)