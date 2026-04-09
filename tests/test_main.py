from unittest.mock import AsyncMock, MagicMock

import pytest
from click.testing import CliRunner

from vex_cli.__main__ import _run_vex_tasks, cli, main
from vex_cli.models.pydantic import VexServerInfo


@pytest.fixture
def server_info():
    return VexServerInfo(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=9000,
    )


def make_pid_lock_mock(raise_exc=None):
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = (
        AsyncMock(return_value=False)
        if not raise_exc
        else AsyncMock(side_effect=raise_exc)
    )
    return cm


@pytest.mark.asyncio
async def test_main_returns_0_on_success(server_info, mocker):
    mocker.patch("vex_cli.__main__.pid_file_lock", return_value=make_pid_lock_mock())
    mocker.patch("vex_cli.__main__._run_vex_tasks", new_callable=AsyncMock)

    assert await main(server_info) == 0


@pytest.mark.asyncio
async def test_main_returns_1_on_runtime_error(server_info, mocker):
    mocker.patch("vex_cli.__main__.pid_file_lock", return_value=make_pid_lock_mock())
    mocker.patch(
        "vex_cli.__main__._run_vex_tasks",
        new_callable=AsyncMock,
        side_effect=RuntimeError("already running"),
    )

    assert await main(server_info) == 1


@pytest.mark.asyncio
async def test_main_returns_1_on_unexpected_exception(server_info, mocker):
    mocker.patch("vex_cli.__main__.pid_file_lock", return_value=make_pid_lock_mock())
    mocker.patch(
        "vex_cli.__main__._run_vex_tasks",
        new_callable=AsyncMock,
        side_effect=Exception("unexpected"),
    )

    assert await main(server_info) == 1


@pytest.mark.asyncio
async def test_run_vex_tasks_initializes_db_and_shuts_down(server_info, mocker):
    mock_state = MagicMock()
    mock_state.initialize_db_manager = AsyncMock()
    mock_state.shutdown = AsyncMock()
    mocker.patch("vex_cli.__main__.VexState", return_value=mock_state)
    mocker.patch("vex_cli.__main__.start_proxy", new_callable=AsyncMock)
    mocker.patch("vex_cli.__main__.start_fastapi", new_callable=AsyncMock)

    await _run_vex_tasks(server_info)

    mock_state.initialize_db_manager.assert_called_once()
    mock_state.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_run_vex_tasks_shutdown_called_even_on_crash(server_info, mocker):
    mock_state = MagicMock()
    mock_state.initialize_db_manager = AsyncMock()
    mock_state.shutdown = AsyncMock()
    mocker.patch("vex_cli.__main__.VexState", return_value=mock_state)
    mocker.patch(
        "vex_cli.__main__.start_proxy",
        new_callable=AsyncMock,
        side_effect=RuntimeError("crash"),
    )
    mocker.patch("vex_cli.__main__.start_fastapi", new_callable=AsyncMock)

    with pytest.raises(RuntimeError):
        await _run_vex_tasks(server_info)

    mock_state.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_run_vex_tasks_raises_if_server_crashes(server_info, mocker):
    mock_state = MagicMock()
    mock_state.initialize_db_manager = AsyncMock()
    mock_state.shutdown = AsyncMock()
    mocker.patch("vex_cli.__main__.VexState", return_value=mock_state)
    mocker.patch(
        "vex_cli.__main__.start_proxy",
        new_callable=AsyncMock,
        side_effect=RuntimeError("proxy died"),
    )
    mocker.patch("vex_cli.__main__.start_fastapi", new_callable=AsyncMock)

    with pytest.raises(RuntimeError, match="proxy died"):
        await _run_vex_tasks(server_info)


def test_start_command_exits_if_port_in_use(mocker):
    mocker.patch("vex_cli.__main__.try_bind_ports", return_value=(False, 8080))
    runner = CliRunner()
    result = runner.invoke(cli, ["start"])

    assert result.exit_code == 1
    assert "already in use" in result.output


def test_start_command_passes_correct_defaults(mocker):
    mocker.patch("vex_cli.__main__.try_bind_ports", return_value=(True, None))
    mocker.patch("vex_cli.__main__.asyncio.run", return_value=0)
    mock_server_info = mocker.patch("vex_cli.__main__.VexServerInfo")
    runner = CliRunner()

    runner.invoke(cli, ["start"])

    mock_server_info.assert_called_once_with(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=9000,
    )
