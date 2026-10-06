import asyncio

import pytest
from unittest.mock import AsyncMock

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.errors import DatabaseError, NoProjectActiveError
from vex_cli.models.orm import RequestSummaryORM


@pytest.fixture
def manager(mocker):
    """DatabaseManager with all child databases mocked out."""
    mocker.patch(
        "vex_cli.database.db_manager.ProjectsDatabase",
        side_effect=lambda *args, **kwargs: AsyncMock(),
        return_value=AsyncMock()
    )
    mocker.patch(
        "vex_cli.database.db_manager.SummariesDatabase",
        side_effect=lambda *args, **kwargs: AsyncMock(),
        return_value=AsyncMock()
    )
    mocker.patch(
        "vex_cli.database.db_manager.RawDatabase",
        side_effect=lambda *args, **kwargs: AsyncMock(),
        return_value=AsyncMock()
    )
    return DatabaseManager()


@pytest.mark.asyncio
async def test_initialize_calls_projects_db(manager):
    await manager.initialize()

    manager._projects_db.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_initialize_does_not_initialize_project_dbs(manager):
    await manager.initialize()

    assert manager._summaries_db is None
    assert manager._raw_db is None


@pytest.mark.asyncio
async def test_get_projects_db_returns_db(manager):
    await manager.initialize()

    result = manager.projects_db

    assert result is manager._projects_db

@pytest.mark.asyncio
async def test_get_projects_db_raises_before_initialize(mocker):
    mocker.patch(
        "vex_cli.database.db_manager.ProjectsDatabase",
        return_value=AsyncMock()
    )
    manager = DatabaseManager()
    manager._projects_db = None  # pyright: ignore force uninitialized state

    with pytest.raises(DatabaseError):
        manager.projects_db


@pytest.mark.asyncio
async def test_get_summaries_db_raises_before_switch(manager):
    with pytest.raises(NoProjectActiveError):
        manager.summaries_db

@pytest.mark.asyncio
async def test_get_summaries_db_returns_db_after_switch(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    result = manager.summaries_db

    assert result is manager._summaries_db


@pytest.mark.asyncio
async def test_get_raw_db_raises_before_switch(manager):
    with pytest.raises(NoProjectActiveError):
        manager.raw_db

@pytest.mark.asyncio
async def test_get_raw_db_returns_db_after_switch(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    result = manager.raw_db

    assert result is manager._raw_db


@pytest.mark.asyncio
async def test_switch_initializes_new_databases(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    manager._summaries_db.initialize.assert_called_once()
    manager._raw_db.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_switch_closes_previous_databases(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    first_summaries = manager._summaries_db
    first_raw = manager._raw_db

    await manager.switch_project_databases(tmp_path / "project2")

    first_summaries.close.assert_called_once()
    first_raw.close.assert_called_once()

@pytest.mark.asyncio
async def test_switch_replaces_database_instances(manager, tmp_path):
    await manager.switch_project_databases(tmp_path / "project1")
    tmp_summaries = manager._summaries_db
    tmp_raw = manager._raw_db

    await manager.switch_project_databases(tmp_path / "project2")

    assert manager._raw_db is not tmp_raw
    assert manager._summaries_db is not tmp_summaries

@pytest.mark.asyncio
async def test_switch_does_not_close_if_no_previous(manager, tmp_path):
    await manager.switch_project_databases(tmp_path) 

@pytest.mark.asyncio
async def test_close_closes_all_databases(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)
    summaries = manager._summaries_db
    raw = manager._raw_db

    await manager.close()

    manager._projects_db.close.assert_called_once()
    summaries.close.assert_called_once()
    raw.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_without_project_databases(manager):
    await manager.close()

    manager._projects_db.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_continues_if_one_db_fails(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)
    summaries = manager._summaries_db
    raw = manager._raw_db
    summaries.close.side_effect = DatabaseError("failed")

    await manager.close()  # should not raise

    raw.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_resets_project_database_state(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    await manager.close()

    assert manager._summaries_db is None
    assert manager._raw_db is None
    assert not manager.is_project_active


# ==================== active_databases snapshot ====================


@pytest.mark.asyncio
async def test_active_databases_returns_none_before_switch(manager):
    assert manager.active_databases() is None


@pytest.mark.asyncio
async def test_active_databases_returns_matching_pair(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    snapshot = manager.active_databases()

    assert snapshot == (manager._summaries_db, manager._raw_db)


@pytest.mark.asyncio
async def test_active_databases_returns_none_after_close(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    await manager.close()

    assert manager.active_databases() is None


# ==================== switch failure / atomicity ====================


@pytest.mark.asyncio
async def test_switch_failure_keeps_previous_databases(manager, tmp_path, mocker):
    await manager.switch_project_databases(tmp_path)
    old_summaries = manager._summaries_db
    old_raw = manager._raw_db

    failing_db = AsyncMock()
    failing_db.initialize.side_effect = DatabaseError("unable to open database file")
    mocker.patch(
        "vex_cli.database.db_manager.SummariesDatabase", return_value=failing_db
    )

    with pytest.raises(DatabaseError):
        await manager.switch_project_databases(tmp_path / "missing")

    assert manager._summaries_db is old_summaries
    assert manager._raw_db is old_raw
    assert manager.is_project_active
    failing_db.close.assert_called_once()


@pytest.mark.asyncio
async def test_switch_failure_keeps_old_project_usable(tmp_path):
    manager = DatabaseManager()
    good_project = tmp_path / "good"
    good_project.mkdir()
    await manager.switch_project_databases(good_project)

    with pytest.raises(DatabaseError):
        await manager.switch_project_databases(tmp_path / "missing-dir")

    assert manager._summaries_db.db_path.parent == good_project
    assert manager.is_project_active
    assert await manager.summaries_db.count(RequestSummaryORM) == 0

    await manager.close()


@pytest.mark.asyncio
async def test_switch_failure_closes_both_candidates(manager, tmp_path, mocker):
    failing_db = AsyncMock()
    failing_db.initialize.side_effect = DatabaseError("init failed")
    mocker.patch(
        "vex_cli.database.db_manager.SummariesDatabase", return_value=failing_db
    )
    raw_db = AsyncMock()
    mocker.patch("vex_cli.database.db_manager.RawDatabase", return_value=raw_db)

    with pytest.raises(DatabaseError):
        await manager.switch_project_databases(tmp_path)

    failing_db.close.assert_called_once()
    raw_db.close.assert_called_once()
    assert not manager.is_project_active


@pytest.mark.asyncio
async def test_concurrent_switches_keep_database_pair_consistent(tmp_path):
    manager = DatabaseManager()
    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    project_a.mkdir()
    project_b.mkdir()

    await asyncio.gather(
        manager.switch_project_databases(project_a),
        manager.switch_project_databases(project_b),
    )

    assert manager.is_project_active
    assert manager._summaries_db.db_path.parent == manager._raw_db.db_path.parent

    await manager.close()