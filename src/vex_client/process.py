import sys
import subprocess
import psutil
from typing import Literal

import logging
logger = logging.getLogger(__name__)

# Constant
INACTIVE_PROCESS: Literal[-1] = -1

def start_detached_process(cmd: list[str]) -> int:
    """
    Spawns a completely new process (detached child) 
    and return the PID or -1 if failed.
    """
    try:
        if sys.platform == "win32":
            # Windows-only kwargs
            proc = subprocess.Popen(
                cmd,
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NO_WINDOW
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

        return proc.pid

    except FileNotFoundError:
        logger.error("vex-cli could not be found in $PATH")
        return -1
    except PermissionError:
        logger.error("No permission to execute vex-cli")
        return -1
    except Exception as e:
        logger.error(f"Unexpected exception occurred trying to run vex-cli {e}")
        return -1

def terminate_process(pid: int):
    """Terminate the process with SIGTERM."""
    try:
        process = psutil.Process(pid)
        process.terminate()
        process.wait(timeout=2.0)
        return True

    except psutil.NoSuchProcess:
        logger.error(f"No process with {pid} PID exists")
        return True
    except psutil.TimeoutExpired:
        return False
    except psutil.AccessDenied:
        logger.error(f"Could not terminate process with {pid} PID")
        return False

def kill_process(pid: int):
    """Kill the process with SIGKILL."""
    try:
        process = psutil.Process(pid)
        process.kill()
        return True

    except psutil.NoSuchProcess:
        logger.error(f"No process with {pid} PID exists")
        return True
    except psutil.AccessDenied:
        logger.error(f"Could not kill process with {pid} PID")
        return False
