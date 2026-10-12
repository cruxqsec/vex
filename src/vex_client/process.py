from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import psutil

if TYPE_CHECKING:
    from subprocess import Popen

logger = logging.getLogger(__name__)

# Constant
INACTIVE_PROCESS: Literal[-1] = -1

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def start_detached_process(cmd: list[str]) -> Popen | None:
    """
    Spawns a completely new process (detached child)
    and return the Popen handle or None if failed.
    """
    try:
        if sys.platform == "win32":
            # Windows-only kwargs
            proc = subprocess.Popen(
                cmd,
                creationflags=(
                    subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
                ),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            # POSIX-only kwargs
            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )

        return proc

    except FileNotFoundError:
        logger.exception("vex-cli could not be found in $PATH")
        return None
    except PermissionError:
        logger.exception("No permission to execute vex-cli")
        return None
    except Exception:
        logger.exception("Unexpected exception occurred trying to run vex-cli")
        return None


def _acquire_probe_lock(fd: int) -> None:
    """Take a non-blocking probe lock on the pid file fd.

    On POSIX a shared lock is taken: two clients probing concurrently both
    win when no server holds the file, and both are refused while a live
    server holds its exclusive lock. Windows msvcrt has no shared mode, so
    concurrent probes collide — an EACCES there means "somebody holds it",
    which errs on the side of "alive" and is sealed by the health probe.
    """
    if sys.platform == "win32":
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)


def is_vex_server_live(pid_file: Path) -> bool:
    """True iff a live vex server holds the exclusive lock on the pid file.

    The server takes an exclusive flock for its lifetime (pid_file_check);
    the kernel releases it on process death, so lock == live instance and
    the pid stored inside the file is never consulted for liveness — PID
    reuse cannot fool this probe. Missing file == nothing was ever started.
    """
    try:
        # O_RDWR mirrors the server's own open; never O_TRUNC: on an
        # acquired probe we hold no ownership of the content, and if a
        # server concurrently grabs the lock the file is its metadata.
        fd = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return False
    try:
        try:
            _acquire_probe_lock(fd)
        except OSError:
            return True  # contended: a live server holds the exclusive lock
        # We won the lock: no live server exists. Release before closing.
        if sys.platform == "win32":
            try:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def is_vex_process(pid: int) -> bool:
    """True if the pid exists and its cmdline looks like a vex process.

    Refuses to identify on psutil errors (AccessDenied etc.) — signal-side
    callers must not touch unverified pids.
    """
    try:
        process = psutil.Process(pid)
        cmdline = process.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    return "vex" in " ".join(cmdline).lower()


def terminate_process(pid: int, verify_vex: bool = True):
    """Terminate the process with SIGTERM.

    With verify_vex, a pid whose cmdline does not look like a vex process
    is refused (PID reuse makes the stale pid point at an unrelated process).
    """
    if verify_vex and not is_vex_process(pid):
        logger.warning(
            f"Refusing to terminate pid {pid}: cmdline is not a vex process"
        )
        return False

    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=2.0)
        return True

    except psutil.NoSuchProcess:
        logger.warning(f"No process with {pid} PID exists")
        return True
    except psutil.TimeoutExpired:
        return False
    except psutil.AccessDenied:
        logger.exception(f"Could not terminate process with {pid} PID")
        return False


def kill_process(pid: int, verify_vex: bool = True):
    """Kill the process with SIGKILL and reap it so no zombie remains.

    Same verify_vex contract as terminate_process.
    """
    if verify_vex and not is_vex_process(pid):
        logger.warning(f"Refusing to kill pid {pid}: cmdline is not a vex process")
        return False

    try:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=1.0)
        return True

    except psutil.NoSuchProcess:
        logger.warning(f"No process with {pid} PID exists")
        return True
    except psutil.TimeoutExpired:
        logger.warning(f"Process with {pid} PID survived SIGKILL (dying unreaped)")
        return True
    except psutil.AccessDenied:
        logger.exception(f"Could not kill process with {pid} PID")
        return False
