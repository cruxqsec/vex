import pytest

from vex_cli.errors import DatabaseError, NoProjectActiveError
from vex_cli.models.orm import ProjectORM, RawRequestORM, RequestSummaryORM


async def test_new_manager_has_no_active_project(bare_manager):
    assert bare_manager.is_project_active is False
    assert bare_manager.active_databases() is None
    with pytest.raises(NoProjectActiveError):
        bare_manager.summaries_db
    with pytest.raises(NoProjectActiveError):
        bare_manager.raw_db


async def test_initialize_makes_projects_db_usable(bare_manager):
    await bare_manager.initialize()

    assert await bare_manager.projects_db.count(ProjectORM) == 0


async def test_switch_activates_project_databases(bare_manager, folder_a):
    await bare_manager.switch_project_databases(folder_a)

    summaries, raw = bare_manager.active_databases()
    assert bare_manager.is_project_active
    assert summaries is bare_manager.summaries_db
    assert raw is bare_manager.raw_db
    assert (folder_a / "main.db").exists()
    assert (folder_a / "raw.db").exists()
    assert await summaries.count(RequestSummaryORM) == 0
    assert await raw.count(RawRequestORM) == 0


async def test_switch_replaces_and_closes_old_databases(
    bare_manager, folder_a, folder_b
):
    await bare_manager.switch_project_databases(folder_a)
    old_summaries, old_raw = bare_manager.active_databases()

    await bare_manager.switch_project_databases(folder_b)

    new_summaries, new_raw = bare_manager.active_databases()
    assert new_summaries is not old_summaries
    assert new_raw is not old_raw
    with pytest.raises(DatabaseError):
        await old_summaries.count(RequestSummaryORM)
    with pytest.raises(DatabaseError):
        await old_raw.count(RawRequestORM)
    assert await new_summaries.count(RequestSummaryORM) == 0


async def test_each_project_keeps_its_own_data(
    bare_manager, folder_a, folder_b, request_summary_orm
):
    await bare_manager.switch_project_databases(folder_a)
    await bare_manager.summaries_db.create(request_summary_orm())

    await bare_manager.switch_project_databases(folder_b)
    assert await bare_manager.summaries_db.count(RequestSummaryORM) == 0

    await bare_manager.switch_project_databases(folder_a)
    assert await bare_manager.summaries_db.count(RequestSummaryORM) == 1


async def test_failed_switch_keeps_current_project(
    bare_manager, folder_a, folder_b, tmp_path
):
    await bare_manager.switch_project_databases(folder_a)
    summaries, raw = bare_manager.active_databases()

    with pytest.raises(DatabaseError):
        await bare_manager.switch_project_databases(tmp_path / "missing")

    assert bare_manager.active_databases() == (summaries, raw)
    assert await summaries.count(RequestSummaryORM) == 0
    await bare_manager.switch_project_databases(folder_b)
    assert bare_manager.is_project_active


async def test_close_project_databases_keeps_projects_db(db_manager):
    await db_manager.close_project_databases()

    assert not db_manager.is_project_active
    assert db_manager.active_databases() is None
    with pytest.raises(NoProjectActiveError):
        db_manager.raw_db
    assert await db_manager.projects_db.count(ProjectORM) == 0


async def test_close_project_databases_without_project_does_nothing(bare_manager):
    await bare_manager.close_project_databases()

    assert not bare_manager.is_project_active


async def test_close_closes_every_database(db_manager):
    await db_manager.close()

    assert not db_manager.is_project_active
    with pytest.raises(DatabaseError):
        await db_manager.projects_db.count(ProjectORM)


async def test_close_failure_raises_but_still_closes_the_rest(
    db_manager, summary_db, mocker
):
    mocker.patch.object(
        db_manager.projects_db, "close", side_effect=RuntimeError("boom")
    )

    with pytest.raises(DatabaseError) as exc_info:
        await db_manager.close()

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert not db_manager.is_project_active
    with pytest.raises(DatabaseError):
        await summary_db.count(RequestSummaryORM)
