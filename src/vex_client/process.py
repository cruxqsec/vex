from __future__ import annotations

import logging
import subprocess
import sys
from typing import TYPE_CHECKING, Literal

import psutil

from vex_cli.locations import vex_log_directory

if TYPE_CHECKING:
    from subprocess import Popen

logger = logging.getLogger(__name__)

# Constant
INACTIVE_PROCESS: Literal[-1] = -1


def find_local_process(pid: int, expected_create_time: float) -> psutil.Process | None:
    """Find a local process matching the recorded identity.

    This verifies process identity, not server readiness.
    """
    try:
        process = psutil.Process(pid)

        if process.create_time() != expected_create_time:
            return None

        if not process.is_running():
            return None

        if process.status() == psutil.STATUS_ZOMBIE:
            return None

        return process
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied:
        logger.warning("Cannot verify local process %s: access denied", pid)
        return None


def start_detached_process(cmd: list[str]) -> Popen | None:
    """
    Spawns a completely new process (detached child)
    and return the Popen handle or None if failed.
    """
    # Capture errors that occur before vex-cli can configure its own file logger.
    try:
        output = (vex_log_directory() / "vex-cli-bootstrap.log").open("ab")
    except OSError:
        logger.exception("Could not open the backend output log")
        return None

    try:
        with output:
            if sys.platform == "win32":
                proc = subprocess.Popen(
                    cmd,
                    creationflags=(
                        subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
                    ),
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )
            else:
                proc = subprocess.Popen(
                    cmd,
                    start_new_session=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )

        return proc

    except FileNotFoundError:
        logger.exception(
            "Could not launch the backend process: Python executable not found (%s)",
            cmd[0],
        )
        return None
    except PermissionError:
        logger.exception(
            "Could not launch the backend process: no permission to execute %s",
            cmd[0],
        )
        return None
    except Exception:
        logger.exception("Could not launch the backend process")
        return None


def terminate_process(
    process: Popen | psutil.Process,
    timeout: float = 2.0,
) -> bool:
    """Request termination and wait.

    Return True if the process exited or was already gone.
    Return False if termination timed out or permission was denied.
    """
    try:
        process.terminate()
        process.wait(timeout=timeout)
        return True

    except (psutil.NoSuchProcess, ProcessLookupError):
        return True

    except (psutil.TimeoutExpired, subprocess.TimeoutExpired):
        logger.warning(
            "Process %s did not exit within %.1f seconds",
            process.pid,
            timeout,
        )
        return False

    except (psutil.AccessDenied, PermissionError):
        logger.exception(
            "Permission denied terminating process %s",
            process.pid,
        )
        return False


def kill_process(
    process: Popen | psutil.Process,
    timeout: float = 1.0,
) -> bool:
    """Force termination and wait, reaping a spawned child where applicable.

    Return True if the process exited or was already gone.
    Return False if waiting timed out or permission was denied.
    """
    try:
        process.kill()
        process.wait(timeout=timeout)
        return True

    except (psutil.NoSuchProcess, ProcessLookupError):
        return True

    except (psutil.TimeoutExpired, subprocess.TimeoutExpired):
        logger.warning(
            "Process %s did not exit within %.1f seconds after kill",
            process.pid,
            timeout,
        )
        return False

    except (psutil.AccessDenied, PermissionError):
        logger.exception(
            "Permission denied killing process %s",
            process.pid,
        )
        return False
