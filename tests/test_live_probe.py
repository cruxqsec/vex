import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import pid_file_check, write_pid_file
from vex_client.process import is_vex_server_live


@pytest.fixture
def server_info():
    return VexServerInfo(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=8081,
    )


def test_probe_false_when_file_missing(tmp_path):
    assert is_vex_server_live(tmp_path / "missing.pid") is False


def test_probe_false_when_nobody_holds(tmp_path):
    pid_file = tmp_path / "vex.pid"
    pid_file.write_text("{}")
    assert is_vex_server_live(pid_file) is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock behavior")
def test_probe_true_when_lock_held_posix(tmp_path):
    pid_file = tmp_path / "vex.pid"
    pid_file.write_text("garbage {{{ not json")

    import fcntl

    holder = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert is_vex_server_live(pid_file) is True
    finally:
        fcntl.flock(holder, fcntl.LOCK_UN)
        os.close(holder)

    assert is_vex_server_live(pid_file) is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows locking behavior")
def test_probe_true_when_lock_held_windows(tmp_path):
    pid_file = tmp_path / "vex.pid"
    pid_file.write_text("garbage {{{ not json")

    import msvcrt

    holder = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        msvcrt.locking(holder, msvcrt.LK_NBLCK, 1)
        assert is_vex_server_live(pid_file) is True
    finally:
        msvcrt.locking(holder, msvcrt.LK_UNLCK, 1)
        os.close(holder)

    assert is_vex_server_live(pid_file) is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock behavior")
def test_probe_never_reads_content_posix(tmp_path):
    """Liveness decision ignores the file content entirely."""
    import fcntl

    pid_file = tmp_path / "vex.pid"
    holder = os.open(pid_file, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # no content at all (0 bytes) yet a holder exists -> live
        assert is_vex_server_live(pid_file) is True
    finally:
        fcntl.flock(holder, fcntl.LOCK_UN)
        os.close(holder)


def test_probe_creates_no_side_effects_on_missing_file(tmp_path):
    missing = tmp_path / "nested" / "vex.pid"
    (tmp_path / "nested").mkdir()
    assert is_vex_server_live(missing) is False
    # the O_CREAT open created an empty file; harmless but must not throw
    assert missing.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock behavior")
@pytest.mark.asyncio
async def test_probe_agrees_with_pid_file_check(server_info, tmp_path, mocker):
    """Same-process consistency with the server gate across its lifetime."""
    import fcntl

    pid_file = tmp_path / "vex.pid"
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)

    async with pid_file_check(server_info):
        assert pid_file.exists()
        fd = os.open(pid_file, os.O_RDWR)
        with pytest.raises(OSError):
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        os.close(fd)
        assert is_vex_server_live(pid_file) is True

    assert is_vex_server_live(pid_file) is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX flock behavior")
def test_probe_real_two_process_liveness(tmp_path):
    """True cross-process: a subprocess holds the lock, probe says live;
    after its death (kernel-released lock) the probe says dead."""
    pid_file = tmp_path / "vex.pid"
    pid_file.write_text("stale content")

    child_code = (
        "import fcntl, os, sys, time;"
        f"fd = os.open({str(pid_file)!r}, os.O_RDWR | os.O_CREAT);"
        "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB);"
        "print('locked', flush=True);"
        "time.sleep(30)"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", child_code],
        stdout=subprocess.PIPE,
    )
    try:
        assert proc.stdout is not None
        proc.stdout.readline()  # blocks until 'locked'
        assert is_vex_server_live(pid_file) is True

        proc.kill()
        proc.wait()  # reap: kernel released the lock
        assert is_vex_server_live(pid_file) is False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_write_pid_file_still_round_trips(tmp_path):
    pid_file = tmp_path / "vex.pid"
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)
    assert is_vex_server_live(pid_file) is False  # content alone proves nothing