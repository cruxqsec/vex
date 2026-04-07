import os
import pytest

from vex_cli.models.pydantic import PIDData
from vex_cli.pid_func import (
    delete_pid_file,
    is_process_running,
    read_pid_file,
    write_pid_file,
)


def test_write_and_read_pid_file(tmp_path):
    pid_file = tmp_path / "vex.pid"
    write_pid_file("127.0.0.1", 8080, 9090, pid_file)
    result = read_pid_file(pid_file)
    assert isinstance(result, PIDData)
    assert result.host == "127.0.0.1"
    assert result.proxy_port == 8080
    assert result.api_port == 9090
    assert result.pid == os.getpid()


def test_delete_pid_file(tmp_path):
    pid_file = tmp_path / "vex.pid"
    pid_file.write_text("{}")
    delete_pid_file(pid_file)
    assert not pid_file.exists()


def test_delete_pid_file_missing_ok(tmp_path):
    # shouldn't raise because we swallow errors
    delete_pid_file(tmp_path / "nonexistent.pid")

def test_is_process_running_current_process():
    assert is_process_running(os.getpid()) is True


def test_is_process_running_invalid_pid():
    assert is_process_running(-1) is False
    assert is_process_running(0) is False
    assert is_process_running(999999999) is False


