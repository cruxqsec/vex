import os
from pathlib import Path

from vex_cli.models import PIDData

def is_process_running(pid: int) -> bool:
    """ Check if a process with given PID is running. """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    
def write_pid_file(host: str, proxy_port: int, api_port: int, pid_file: Path) -> None:
    """ Write server information to pid file. """
    
    data = PIDData(
        pid=os.getpid(),
        host=host,
        proxy_port=proxy_port,
        api_port=api_port
    )
        
    pid_file.write_text(data.model_dump_json(indent=2))


def read_pid_file(pid_file: Path) -> PIDData:
    """ Read server information from pid file (we should check before that it exists) """
    data = PIDData.model_validate_json(pid_file.read_text())
    return data
    
def delete_pid_file(pid_file: Path) -> None:
    """ Delete pid file. """
    pid_file.unlink(missing_ok=True)
