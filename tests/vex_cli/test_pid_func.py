import errno
import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import (
    pid_file_check,
    read_pid_file,
)


async def test_pid_file_check_writes_metadata(
    pid_file: Path, server_info: VexServerInfo, mocker: MockerFixture
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    async with pid_file_check(server_info) as pf:
        assert pf.exists()
        data = read_pid_file(pf)
        assert data.pid == os.getpid()
        assert data.host == "127.0.0.1"
        assert data.proxy_port == 8080
        assert data.api_port == 8081


async def test_pid_file_replaces_stale_content(
    pid_file: Path, server_info: VexServerInfo, mocker: MockerFixture
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    pid_file.write_text("this is not valid json {{{{")

    async with pid_file_check(server_info):
        data = read_pid_file(pid_file)  # must now parse
        assert data.pid == os.getpid()


async def test_pid_file_second_start_raises_while_held(
    pid_file: Path, server_info: VexServerInfo, mocker: MockerFixture
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    async with pid_file_check(server_info):
        with pytest.raises(RuntimeError, match="already running"):
            async with pid_file_check(server_info):
                pass


async def test_pid_file_check_lock_released_after_exit(
    pid_file: Path, server_info: VexServerInfo, mocker: MockerFixture
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    async with pid_file_check(server_info):
        pass

    async with pid_file_check(server_info):
        pass


@pytest.mark.parametrize("lock_errno", [errno.EACCES, errno.EAGAIN])
async def test_pid_file_check_raises_if_lock_contended(
    pid_file: Path,
    server_info: VexServerInfo,
    mocker: MockerFixture,
    lock_errno: int,
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    original = OSError(lock_errno, os.strerror(lock_errno))
    mocker.patch("vex_cli.pid_func._acquire_file_lock", side_effect=original)

    with pytest.raises(RuntimeError, match="already running") as raised:
        async with pid_file_check(server_info):
            pass

    assert raised.value.__cause__ is original


@pytest.mark.parametrize("lock_errno", [errno.EBADF, errno.EIO])
async def test_pid_file_check_propagates_unexpected_lock_error(
    pid_file: Path,
    server_info: VexServerInfo,
    mocker: MockerFixture,
    lock_errno: int,
):
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    original = OSError(lock_errno, os.strerror(lock_errno))
    mocker.patch("vex_cli.pid_func._acquire_file_lock", side_effect=original)

    with pytest.raises(OSError) as raised:
        async with pid_file_check(server_info):
            pass

    assert raised.value is original
