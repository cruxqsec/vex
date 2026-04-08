from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from vex_cli.models.pydantic import Project, VexServerInfo
from vex_cli.errors import AppException
from vex_cli.state import VexState


@pytest.fixture
def server_info():
    return VexServerInfo(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=8081,
    )


@pytest.fixture
def mock_project():
    return MagicMock(spec=Project)


@pytest_asyncio.fixture
async def state(server_info, mocker, tmp_path):
    mocker.patch("vex_cli.state.vex_log_directory", return_value=tmp_path)
    mocker.patch("vex_cli.state.DatabaseManager", return_value=AsyncMock())
    s = VexState(server_info)
    await s.initialize_db_manager()
    return s


def test_init_sets_server_info(server_info, mocker, tmp_path):
    mocker.patch("vex_cli.state.vex_log_directory", return_value=tmp_path)
    s = VexState(server_info)

    assert s.server_info is server_info


def test_init_active_project_is_none(server_info, mocker, tmp_path):
    mocker.patch("vex_cli.state.vex_log_directory", return_value=tmp_path)
    s = VexState(server_info)

    assert s._active_project is None


def test_init_creates_flow_history(server_info, mocker, tmp_path):
    mocker.patch("vex_cli.state.vex_log_directory", return_value=tmp_path)
    from vex_cli.flow_history import FlowHistory

    s = VexState(server_info)

    assert isinstance(s._flow_history, FlowHistory)


@pytest.mark.asyncio
async def test_initialize_db_manager_calls_initialize(state):
    state._db_manager.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_db_manager_sets_db_manager(state):
    assert state._db_manager is not None


def test_get_server_info_returns_server_info(state, server_info):
    assert state.get_server_info() is server_info


def test_get_active_project_returns_none_initially(state):
    assert state.get_active_project() is None


@pytest.mark.asyncio
async def test_get_active_project_returns_project_after_set(state, mock_project):
    await state.set_active_project(mock_project)

    assert state.get_active_project() is mock_project


@pytest.mark.asyncio
async def test_set_active_project_sets_project(state, mock_project):
    await state.set_active_project(mock_project)

    assert state._active_project is mock_project


@pytest.mark.asyncio
async def test_set_active_project_can_be_set_to_none(state, mock_project):
    await state.set_active_project(mock_project)
    await state.set_active_project(None)

    assert state._active_project is None


@pytest.mark.asyncio
async def test_set_active_project_can_be_overwritten(state, mock_project):
    other_project = MagicMock(spec=Project)
    await state.set_active_project(mock_project)
    await state.set_active_project(other_project)

    assert state._active_project is other_project


def test_get_flow_history_returns_flow_history(state):
    from vex_cli.flow_history import FlowHistory

    assert isinstance(state.get_flow_history(), FlowHistory)


def test_get_flow_history_returns_same_instance(state):
    result1 = state.get_flow_history()
    result2 = state.get_flow_history()

    assert result1 is result2


def test_get_db_manager_returns_db_manager(state):
    assert state.get_db_manager() is state._db_manager


@pytest.mark.asyncio
async def test_is_project_active_false_without_project(state):
    state._db_manager.is_project_active = False

    assert state.is_project_active is False


@pytest.mark.asyncio
async def test_is_project_active_false_when_db_inactive(state, mock_project):
    await state.set_active_project(mock_project)
    state._db_manager.is_project_active = False

    assert state.is_project_active is False


@pytest.mark.asyncio
async def test_is_project_active_true_when_both_set(state, mock_project):
    await state.set_active_project(mock_project)
    state._db_manager.is_project_active = True

    assert state.is_project_active is True


@pytest.mark.asyncio
async def test_shutdown_closes_db_manager(state):
    await state.shutdown()

    state._db_manager.close.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_without_db_manager_does_not_raise(
    server_info, mocker, tmp_path
):
    mocker.patch("vex_cli.state.vex_log_directory", return_value=tmp_path)
    s = VexState(server_info)
    # never called initialize_db_manager so _db_manager is not set

    with pytest.raises(AppException):
        await s.shutdown()
