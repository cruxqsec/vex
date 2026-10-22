import errno
import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from vex_cli.models.pydantic import VexServerInfo
from vex_cli.pid_func import lock_file_check, read_metadata_file


@pytest.fixture
def server_files(tmp_path: Path, mocker: MockerFixture) -> tuple[Path, Path]:
    lock_file = tmp_path / "vex.lock"
    metadata_file = tmp_path / "vex-server.json"
    mocker.patch("vex_cli.pid_func.vex_lock_file", return_value=lock_file)
    mocker.patch("vex_cli.pid_func.vex_server_metadata_file", return_value=metadata_file)
    return lock_file, metadata_file


async def test_lock_file_check_writes_metadata(
    server_files: tuple[Path, Path], server_info: VexServerInfo
):
    lock_file, metadata_file = server_files
    async with lock_file_check(server_info):
        assert lock_file.exists()
        assert metadata_file.exists()
        data = read_metadata_file()
        assert data.pid == os.getpid()
        assert data.create_time > 0
        assert data.host == "127.0.0.1"
        assert data.proxy_port == 8080
        assert data.api_port == 8081


async def test_metadata_file_replaces_stale_content(
    server_files: tuple[Path, Path], server_info: VexServerInfo
):
    _, metadata_file = server_files
    metadata_file.write_text("this is not valid json {{{{")

    async with lock_file_check(server_info):
        data = read_metadata_file()
        assert data.pid == os.getpid()
        assert metadata_file.exists()


async def test_lock_file_second_start_raises_while_held(
    server_files: tuple[Path, Path], server_info: VexServerInfo
):
    async with lock_file_check(server_info):
        with pytest.raises(RuntimeError, match="already running"):
            async with lock_file_check(server_info):
                pass


async def test_lock_file_check_lock_released_after_exit(
    server_files: tuple[Path, Path], server_info: VexServerInfo
):
    lock_file, metadata_file = server_files
    async with lock_file_check(server_info):
        pass

    assert lock_file.exists()
    assert metadata_file.exists()
    async with lock_file_check(server_info):
        assert read_metadata_file().pid == os.getpid()


@pytest.mark.parametrize("lock_errno", [errno.EACCES, errno.EAGAIN])
async def test_lock_file_check_raises_if_lock_contended(
    server_files: tuple[Path, Path],
    server_info: VexServerInfo,
    mocker: MockerFixture,
    lock_errno: int,
):
    original = OSError(lock_errno, os.strerror(lock_errno))
    mocker.patch("vex_cli.pid_func._acquire_file_lock", side_effect=original)

    with pytest.raises(RuntimeError, match="already running") as raised:
        async with lock_file_check(server_info):
            pass

    assert raised.value.__cause__ is original
    assert not server_files[1].exists()


@pytest.mark.parametrize("lock_errno", [errno.EBADF, errno.EIO])
async def test_lock_file_check_propagates_unexpected_lock_error(
    server_files: tuple[Path, Path],
    server_info: VexServerInfo,
    mocker: MockerFixture,
    lock_errno: int,
):
    original = OSError(lock_errno, os.strerror(lock_errno))
    mocker.patch("vex_cli.pid_func._acquire_file_lock", side_effect=original)

    with pytest.raises(OSError) as raised:
        async with lock_file_check(server_info):
            pass

    assert raised.value is original
    assert not server_files[1].exists()
