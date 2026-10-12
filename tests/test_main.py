import asyncio
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from vex_cli.__main__ import _run_vex_tasks, cli, main


@asynccontextmanager
async def fake_pid_check(server_info):
    yield


@pytest.fixture(autouse=True)
def isolate(mocker, tmp_path):
    mocker.patch("vex_cli.__main__._configure_logging")
    mocker.patch("vex_cli.__main__.vex_log_directory", return_value=tmp_path)
    mocker.patch("vex_cli.__main__.pid_file_check", fake_pid_check)
    mocker.patch(
        "vex_cli.database.db_manager.vex_projects_db_path",
        return_value=tmp_path / "projects.db",
    )


def test_start_exits_1_when_port_is_in_use(mocker):
    mocker.patch("vex_cli.__main__.try_bind_ports", return_value=(False, 8080))

    result = CliRunner().invoke(cli, ["start"])

    assert result.exit_code == 1
    assert "Port 8080 is already in use!" in result.output


def test_start_passes_options_and_exits_with_main_code(mocker):
    mocker.patch("vex_cli.__main__.try_bind_ports", return_value=(True, None))
    main_mock = mocker.patch("vex_cli.__main__.main", return_value=3)

    result = CliRunner().invoke(
        cli,
        ["start", "--address", "0.0.0.0", "--proxy-port", "8181", "--api-port", "9191"],
    )

    server_info = main_mock.await_args.args[0]
    assert result.exit_code == 3
    assert server_info.server_address == "0.0.0.0"
    assert (server_info.proxy_port, server_info.api_port) == (8181, 9191)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (None, 0),
        (RuntimeError("port taken"), 1),
        (ExceptionGroup("many", [ValueError("a"), ValueError("b")]), 1),
        (KeyError("surprise"), 1),
    ],
)
async def test_main_returns_exit_code(mocker, server_info, error, code):
    mocker.patch("vex_cli.__main__._run_vex_tasks", side_effect=error)

    assert await main(server_info) == code


async def test_crashing_server_stops_the_other_and_shuts_down(mocker, server_info):
    master, uvicorn_server, cancelled = MagicMock(), MagicMock(), []

    async def crashing_proxy(state):
        state.mitmproxy_master = master
        raise RuntimeError("proxy died")

    async def hanging_api(state):
        state.uvicorn_server = uvicorn_server
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append("api")
            raise

    mocker.patch("vex_cli.__main__.start_proxy", crashing_proxy)
    mocker.patch("vex_cli.__main__.start_fastapi", hanging_api)

    with pytest.raises(RuntimeError, match="proxy died"):
        await _run_vex_tasks(server_info)

    assert cancelled == ["api"]
    assert uvicorn_server.force_exit is True
    master.shutdown.assert_called_once()


async def test_clean_server_exit_stops_the_other_without_error(mocker, server_info):
    cancelled = []

    async def finishing_proxy(state):
        return

    async def hanging_api(state):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.append("api")
            raise

    mocker.patch("vex_cli.__main__.start_proxy", finishing_proxy)
    mocker.patch("vex_cli.__main__.start_fastapi", hanging_api)

    await _run_vex_tasks(server_info)

    assert cancelled == ["api"]
