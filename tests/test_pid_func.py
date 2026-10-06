import os
import sys
from pathlib import Path

import pytest

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import (
    delete_pid_file,
    pid_file_check,
    read_pid_file,
    write_pid_file,
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
async def test_pid_file_check_writes_metadata(server_info, tmp_path, mocker):
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info) as pf:
        assert pf.exists()
        data = read_pid_file(pf)
        assert data.pid == os.getpid()
        assert data.host == "127.0.0.1"
        assert data.proxy_port == 8080
        assert data.api_port == 8081


@pytest.mark.asyncio
async def test_pid_file_check_replaces_stale_content(server_info, tmp_path, mocker):
    """Content from a crashed instance is rewritten once we hold the lock."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    pid_file.write_text("this is not valid json {{{{")

    async with pid_file_check(server_info):
        data = read_pid_file(pid_file)  # must now parse
        assert data.pid == os.getpid()


@pytest.mark.asyncio
async def test_pid_file_check_persists_file_after_clean_exit(
    server_info, tmp_path, mocker
):
    """The file survives exit; the lock (not the file) decides liveness."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info):
        pass

    assert pid_file.exists()


@pytest.mark.asyncio
async def test_pid_file_check_second_start_raises_while_held(
    server_info, tmp_path, mocker
):
    """A held lock excludes any concurrent pid_file_check."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info):
        with pytest.raises(RuntimeError, match="already running"):
            async with pid_file_check(server_info):
                pass


@pytest.mark.asyncio
async def test_pid_file_check_lock_released_after_exit(server_info, tmp_path, mocker):
    """After exit a new instance can acquire the gate (no stale-file lock)."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info):
        pass

    async with pid_file_check(server_info):
        pass


@pytest.mark.asyncio
async def test_pid_file_check_raises_if_lock_contended(
    server_info, tmp_path, mocker
):
    """BlockingIOError/OSError from the lock attempt maps to RuntimeError."""
    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    mocker.patch(
        "vex_cli.pid_func._acquire_file_lock",
        side_effect=BlockingIOError,
    )

    with pytest.raises(RuntimeError, match="already running"):
        async with pid_file_check(server_info):
            pass


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock behavior")
@pytest.mark.asyncio
async def test_pid_file_check_real_two_process_exclusion(
    server_info, tmp_path, mocker
):
    """True cross-process contention: a subprocess holds the lock, we must fail."""
    import subprocess

    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    # Child opens + flocks the same file and sleeps; parent must lose.
    child_code = (
        "import fcntl, os, sys, time;"
        f"fd = os.open({str(pid_file)!r}, os.O_RDWR | os.O_CREAT);"
        "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB);"
        "print('locked', flush=True);"
        "time.sleep(30)"
    )
    proc = subprocess.Popen([sys.executable, "-c", child_code])
    try:
        # wait until the child actually holds the lock
        import time as _time

        deadline = _time.time() + 5
        while _time.time() < deadline:
            with open(pid_file, "a"):
                pass
            probe = os.open(pid_file, os.O_RDWR)
            try:
                import fcntl as _fcntl

                _fcntl.flock(probe, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
                _fcntl.flock(probe, _fcntl.LOCK_UN)
            except OSError:
                break  # child holds it
            finally:
                os.close(probe)
            _time.sleep(0.05)

        with pytest.raises(RuntimeError, match="already running"):
            async with pid_file_check(server_info):
                pass
    finally:
        proc.kill()
        proc.wait()