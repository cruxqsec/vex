from __future__ import annotations

import logging
import subprocess
import sys
from typing import TYPE_CHECKING, Literal

import psutil

if TYPE_CHECKING:
    from subprocess import Popen

logger = logging.getLogger(__name__)

# Constant
INACTIVE_PROCESS: Literal[-1] = -1


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


def terminate_process(pid: int):
    """Terminate the process with SIGTERM."""
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


def kill_process(pid: int):
    """Kill the process with SIGKILL and reap it so no zombie remains."""
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
