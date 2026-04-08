# tests/test_db_manager.py
import pytest
from unittest.mock import AsyncMock

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.errors import DatabaseError


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
    with pytest.raises(DatabaseError, match="summaries database not initialized"):
        manager.summaries_db

@pytest.mark.asyncio
async def test_get_summaries_db_returns_db_after_switch(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)

    result = manager.summaries_db

    assert result is manager._summaries_db


@pytest.mark.asyncio
async def test_get_raw_db_raises_before_switch(manager):
    with pytest.raises(DatabaseError, match="raw database not initialized"):
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

    await manager.close()

    manager._projects_db.close.assert_called_once()
    manager._summaries_db.close.assert_called_once()
    manager._raw_db.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_without_project_databases(manager):
    await manager.close()

    manager._projects_db.close.assert_called_once()

@pytest.mark.asyncio
async def test_close_continues_if_one_db_fails(manager, tmp_path):
    await manager.switch_project_databases(tmp_path)
    manager._summaries_db.close.side_effect = DatabaseError("failed")

    await manager.close()  # should not raise

    manager._raw_db.close.assert_called_once()