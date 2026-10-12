import os
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import (
    delete_pid_file,
    pid_file_check,
    read_pid_file,
    write_pid_file,
)


def test_write_and_read_pid_file(pid_file: Path):
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)

    assert pid_file.exists()
    data = read_pid_file(pid_file)
    assert data.pid == os.getpid()
    assert data.host == "127.0.0.1"
    assert data.proxy_port == 8080
    assert data.api_port == 8081


def test_write_pid_file_creates_valid_json(pid_file: Path):
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)
    content = pid_file.read_text()
    assert "pid" in content
    assert "host" in content


def test_delete_pid_file_removes_file(pid_file: Path):
    write_pid_file("127.0.0.1", 8080, 8081, pid_file)
    delete_pid_file(pid_file)
    assert not pid_file.exists()


def test_delete_pid_file_does_not_raise_if_missing(pid_file: Path):
    delete_pid_file(pid_file)
    # should not raise
    delete_pid_file(pid_file)


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


async def test_pid_file_check_raises_if_lock_contended(
    pid_file: Path, server_info: VexServerInfo, mocker: MockerFixture
):
    """BlockingIOError/OSError from the lock attempt maps to RuntimeError."""
    mocker.patch("vex_cli.pid_func.vex_pid_file", return_value=pid_file)
    mocker.patch(
        "vex_cli.pid_func._acquire_file_lock",
        side_effect=BlockingIOError,
    )

    with pytest.raises(RuntimeError, match="already running"):
        async with pid_file_check(server_info):
            pass
