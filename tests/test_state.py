import pytest

from vex_cli.errors import AppException
from vex_cli.models.orm import ProjectORM
from vex_cli.state import VexState


@pytest.fixture
def bare_state(server_info):
    return VexState(server_info)


def test_new_state_has_no_active_project(bare_state):
    assert bare_state.get_active_project() is None


def test_get_db_manager_before_initialize_raises(bare_state):
    with pytest.raises(AppException):
        bare_state.get_db_manager()


async def test_initialize_db_manager_creates_usable_projects_db(
    bare_state, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "vex_cli.database.db_manager.vex_projects_db_path",
        lambda: tmp_path / "projects.db",
    )

    await bare_state.initialize_db_manager()

    assert await bare_state.get_db_manager().projects_db.count(ProjectORM) == 0
    await bare_state.shutdown()


async def test_active_project_can_be_set_replaced_and_cleared(state, project):
    first, second = project(), project()

    await state.set_active_project(first)
    assert state.get_active_project() == first

    await state.set_active_project(second)
    assert state.get_active_project() == second

    await state.set_active_project(None)
    assert state.get_active_project() is None


def test_is_project_active_false_without_project(state):
    assert state.is_project_active is False


async def test_is_project_active_true_with_project_and_databases(state, project):
    await state.set_active_project(project())

    assert state.is_project_active is True


async def test_is_project_active_false_when_databases_closed(
    state, db_manager, project
):
    await state.set_active_project(project())
    await db_manager.close_project_databases()

    assert state.is_project_active is False


async def test_is_project_active_false_without_db_manager(bare_state, project):
    await bare_state.set_active_project(project())

    assert bare_state.is_project_active is False


async def test_shutdown_closes_project_databases(state, db_manager):
    assert db_manager.is_project_active

    await state.shutdown()

    assert not db_manager.is_project_active


async def test_shutdown_without_db_manager_does_not_raise(bare_state):
    await bare_state.shutdown()
