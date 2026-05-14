from unittest.mock import MagicMock

import pytest

from vex_cli.dependencies import (
    get_db_manager,
    get_flow_history,
    get_projects_db,
    get_raw_db,
    get_state_object,
    get_summaries_db,
)


@pytest.fixture
def mock_request():
    request = MagicMock()
    return request


@pytest.fixture
def mock_websocket():
    websocket = MagicMock()
    return websocket


def test_get_state_object_returns_vex_state(mock_request):
    result = get_state_object(mock_request)

    assert result is mock_request.app.state.vex_state


def test_get_flow_history_returns_flow_history(mock_websocket):
    result = get_flow_history(mock_websocket)

    assert result is mock_websocket.app.state.vex_state.get_flow_history()


def test_get_db_manager_returns_db_manager(mock_request):
    result = get_db_manager(mock_request)

    assert result is mock_request.app.state.vex_state.get_db_manager()


def test_get_projects_db_returns_projects_db(mock_request):
    result = get_projects_db(mock_request)

    assert result is mock_request.app.state.vex_state.get_db_manager().projects_db


def test_get_summaries_db_returns_summaries_db(mock_request):
    result = get_summaries_db(mock_request)

    assert result is mock_request.app.state.vex_state.get_db_manager().summaries_db


def test_get_raw_db_returns_raw_db(mock_request):
    result = get_raw_db(mock_request)

    assert result is mock_request.app.state.vex_state.get_db_manager().raw_db
