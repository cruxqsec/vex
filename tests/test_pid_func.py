import os
from pathlib import Path
import pytest

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import (
    delete_pid_file,
    is_process_running,
    read_pid_file,
    write_pid_file,
    pid_file_check,
)


@pytest.fixture
def server_info():
    return VexServerInfo(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=8081,
    )


@pytest.fixture
def pid_file(tmp_path) -> Path:
    return tmp_path / "vex.pid"


def test_is_process_running_returns_false_for_zero():
    assert is_process_running(0) is False


def test_is_process_running_returns_false_for_negative():
    assert is_process_running(-1) is False


def test_is_process_running_returns_true_for_current_process():
    # current process is definitely running
    assert is_process_running(os.getpid()) is True


def test_is_process_running_returns_false_for_dead_process(mocker):
    mocker.patch("os.kill", side_effect=ProcessLookupError)
    assert is_process_running(99999) is False


def test_is_process_running_returns_false_on_os_error(mocker):
    mocker.patch("os.kill", side_effect=OSError)
    assert is_process_running(99999) is False


def test_write_and_read_pid_file(pid_file):
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)

    assert pid_file.exists()
    data = read_pid_file(pid_file)
    assert data.pid == os.getpid()
    assert data.host == "127.0.0.1"
    assert data.proxy_port == 8080
    assert data.api_port == 8081


def test_write_pid_file_creates_valid_json(pid_file):
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)
    content = pid_file.read_text()
    assert "pid" in content
    assert "host" in content


def test_delete_pid_file_removes_file(pid_file):
    pid_file.write_text("{}")
    delete_pid_file(pid_file)
    assert not pid_file.exists()


def test_delete_pid_file_does_not_raise_if_missing(pid_file):
    delete_pid_file(pid_file)  # should not raise


@pytest.mark.asyncio
async def test_pid_file_check_creates_pid_file(server_info, tmp_path, mocker):
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info) as pf:
        assert pf.exists()  # file exists during context


@pytest.mark.asyncio
async def test_pid_file_check_deletes_pid_file_on_exit(server_info, tmp_path, mocker):
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info):
        pass

    assert not pid_file.exists()


@pytest.mark.asyncio
async def test_pid_file_check_deletes_pid_file_on_exception(
    server_info, tmp_path, mocker
):
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    with pytest.raises(RuntimeError, match="test error"):
        async with pid_file_check(server_info):
            raise RuntimeError("test error")

    assert not pid_file.exists()


@pytest.mark.asyncio
async def test_pid_file_check_raises_if_already_running(server_info, tmp_path, mocker):
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    mocker.patch("vex_cli.pid_func.is_process_running", return_value=True)

    write_pid_file("127.0.0.1", 8080, 8081, pid_file)

    with pytest.raises(RuntimeError, match="already running"):
        async with pid_file_check(server_info):
            pass


@pytest.mark.asyncio
async def test_pid_file_check_cleans_stale_pid_file(server_info, tmp_path, mocker):
    """If pid file exists but process is dead, it should be cleaned up and proceed."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    mocker.patch("vex_cli.pid_func.is_process_running", return_value=False)

    write_pid_file("127.0.0.1", 8080, 8081, pid_file)

    async with pid_file_check(server_info):
        pass


@pytest.mark.asyncio
async def test_pid_file_check_cleans_corrupt_pid_file(server_info, tmp_path, mocker):
    """If pid file is corrupt/unreadable, it should be deleted and proceed."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    pid_file.write_text("this is not valid json {{{{")

    async with pid_file_check(server_info):
        pass
