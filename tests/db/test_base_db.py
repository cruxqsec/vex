import time
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Float, LargeBinary, String, Uuid, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from vex_cli.database.base_db import BaseDatabase, ConflictError
from vex_cli.errors import DatabaseError, NotFoundError
from vex_cli.models.orm import Base


# Minimal throwaway model
class TestModelORM(Base):
    __test__ = False # just to supress the warning and tell pytest this is not a test class
    __tablename__ = "test_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True)
    name: Mapped[str] = mapped_column(String)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    timestamp: Mapped[float] = mapped_column(Float)


class TestModelDB(BaseDatabase):
    __test__ = False
    _orm_models = [TestModelORM]
    _wal_mode = True


@pytest.fixture
def mock_test_model() -> TestModelORM:
    return TestModelORM(
        uuid=uuid4(),
        name="test_item",
        blob=b"randombytestring",
        timestamp=time.time(),
    )


@pytest.fixture
def make_test_model():
    def _factory(**kwargs):
        defaults = {
            "uuid": uuid4(),
            "name": "test_item",
            "blob": b"randombytestring",
            "timestamp": time.time(),
        }
        return TestModelORM(**{**defaults, **kwargs})

    return _factory


@pytest_asyncio.fixture
async def uninitialized_db(tmp_path: Path):
    database = TestModelDB(db_path=tmp_path / "test.db")
    yield database
    await database.close()


@pytest_asyncio.fixture
async def db(tmp_path: Path):
    database = TestModelDB(db_path=tmp_path / "test.db")
    await database.initialize()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_initialize_creates_engine(uninitialized_db):
    assert uninitialized_db._engine is None
    await uninitialized_db.initialize()
    assert uninitialized_db._engine is not None


@pytest.mark.asyncio
async def test_failed_initialize_disposes_engine(uninitialized_db, mocker):
    mocker.patch.object(
        Base.metadata, "create_all", side_effect=SQLAlchemyError("boom")
    )

    with pytest.raises(DatabaseError):
        await uninitialized_db.initialize()

    assert uninitialized_db._engine is None


@pytest.mark.asyncio
async def test_initialize_raises_database_error_on_engine_failure(uninitialized_db, mocker):
    mocker.patch(
        "vex_cli.database.base_db.create_async_engine",
        side_effect=SQLAlchemyError("connection failed"),
    )
    with pytest.raises(DatabaseError, match="Error initializing database"):
        await uninitialized_db.initialize()

@pytest.mark.asyncio
async def test_wal_enabled_correctly(uninitialized_db):
    await uninitialized_db.initialize()

    async with uninitialized_db._engine.connect() as conn:
        result = await conn.execute(
            text("PRAGMA journal_mode")
        )

    assert result.scalar() == "wal"

@pytest.mark.asyncio
async def test_initialize_twice(uninitialized_db):
    await uninitialized_db.initialize()
    engine_before = uninitialized_db._engine

    await uninitialized_db.initialize()  # second call
    assert uninitialized_db._engine is engine_before  # same engine, not recreated


@pytest.mark.asyncio
async def test_create_tables(uninitialized_db, mocker):
    spy = mocker.patch.object(uninitialized_db, "_create_tables", AsyncMock())

    await uninitialized_db.initialize()

    spy.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_tables_creates_expected_table(uninitialized_db):
    await uninitialized_db.initialize()

    async with uninitialized_db._engine.connect() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [r[0] for r in result]

    assert len(tables) == 1
    assert tables == ["test_items"]


@pytest.mark.asyncio
async def test_create_returns_object_with_id(db, mock_test_model):
    item = await db.create(mock_test_model)

    assert item.id is not None
    assert type(item.uuid) is UUID
    assert item.name == "test_item"
    assert item.blob == b"randombytestring"


@pytest.mark.asyncio
async def test_get_returns_correct_object(db, mock_test_model):
    created = await db.create(mock_test_model)

    fetched = await db.get(TestModelORM, created.id)

    assert type(fetched.id) is int
    assert fetched.id == created.id
    assert type(fetched.uuid) is UUID
    assert fetched.uuid == created.uuid
    assert fetched.name == created.name
    assert fetched.timestamp == created.timestamp
    assert fetched.blob == created.blob


@pytest.mark.asyncio
async def test_get_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await db.get(TestModelORM, 99999)

@pytest.mark.asyncio
async def test_get_wrong_primary_key_type(db):
    with pytest.raises(DatabaseError):
        await db.get(TestModelORM, uuid4())


@pytest.mark.asyncio
async def test_get_all_returns_all_items1(db, make_test_model):
    for i in range(3):
        await db.create(make_test_model())

    result = await db.get_all(TestModelORM, skip=0, size=10)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_all_skip_all(db, make_test_model):
    for i in range(8):
        await db.create(make_test_model())

    result = await db.get_all(TestModelORM, skip=9, size=1)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_all_too_many(db, make_test_model):
    for i in range(5):
        await db.create(make_test_model())

    result = await db.get_all(TestModelORM, skip=2, size=8)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_all_correct_pagination(db, make_test_model):
    for i in range(15):
        await db.create(make_test_model())

    page = await db.get_all(TestModelORM, skip=6, size=5)

    assert len(page) == 5


@pytest.mark.asyncio
async def test_get_all_empty(db):
    result = await db.get_all(TestModelORM, skip=0, size=10)

    assert result == []


@pytest.mark.asyncio
async def test_update_changes_value(db, mock_test_model):
    item = await db.create(mock_test_model)
    item.name = "new_name"
    new_uuid = uuid4()
    item.uuid = new_uuid

    await db.update(TestModelORM, item)
    fetched = await db.get(TestModelORM, item.id)

    assert fetched.name == "new_name"
    assert fetched.uuid == new_uuid


@pytest.mark.asyncio
async def test_update_raises_not_found(db, mock_test_model):
    non_existent = mock_test_model
    non_existent.id = 99999
    non_existent.uuid = uuid4()

    with pytest.raises(NotFoundError):
        await db.update(TestModelORM, non_existent)


@pytest.mark.asyncio
async def test_delete_removes_object(db, mock_test_model):
    item = await db.create(mock_test_model)

    await db.delete(TestModelORM, item.id)

    with pytest.raises(NotFoundError):
        await db.get(TestModelORM, item.id)


@pytest.mark.asyncio
async def test_delete_all_removes_everything(db, make_test_model):
    for _ in range(5):
        await db.create(make_test_model())

    await db.delete_all(TestModelORM)

    result = await db.get_all(TestModelORM, skip=0, size=100)
    assert result == []


@pytest.mark.asyncio
async def test_delete_all_empty_table_does_not_raise(db):
    await db.delete_all(TestModelORM)


@pytest.mark.asyncio
async def test_count_returns_total_rows(db, make_test_model):
    for _ in range(5):
        await db.create(make_test_model())

    assert await db.count(TestModelORM) == 5


@pytest.mark.asyncio
async def test_count_empty_table_returns_zero(db):
    assert await db.count(TestModelORM) == 0


@pytest.mark.asyncio
async def test_count_after_delete_all_returns_zero(db, make_test_model):
    for _ in range(3):
        await db.create(make_test_model())

    await db.delete_all(TestModelORM)

    assert await db.count(TestModelORM) == 0


@pytest.mark.asyncio
async def test_delete_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await db.delete(TestModelORM, 99999)


@pytest.mark.asyncio
async def test_close_disposes_engine(db, mocker):
    mock_dispose = mocker.patch.object(AsyncEngine, "dispose", new_callable=AsyncMock)

    await db.close()

    mock_dispose.assert_called_once()


@pytest.mark.asyncio
async def test_close_without_initialize_does_nothing(uninitialized_db):
    assert uninitialized_db._engine is None

    await uninitialized_db.close()  # should not raise


@pytest.mark.asyncio
async def test_engine_pool_closed_after_close(db):
    engine = db._engine

    await db.close()

    # disposed engine has no active connections in the pool
    assert engine.pool.checkedin() == 0
    assert engine.pool.checkedout() == 0


@pytest.mark.asyncio
async def test_operations_fail_after_close(db, mock_test_model):
    await db.close()

    with pytest.raises(DatabaseError):
        await db.create(mock_test_model)


@pytest.mark.asyncio
async def test_session_raises_validation_error_on_duplicate(db, make_test_model):
    shared_uuid = uuid4()
    await db.create(make_test_model(uuid=shared_uuid))

    with pytest.raises(ConflictError, match="Record already exists"):
        await db.create(make_test_model(uuid=shared_uuid))


@pytest.mark.asyncio
async def test_get_all_pages_are_ordered_and_complete(db, make_test_model):
    for _ in range(5):
        await db.create(make_test_model())

    page1 = await db.get_all(TestModelORM, skip=0, size=2)
    page2 = await db.get_all(TestModelORM, skip=2, size=2)
    page3 = await db.get_all(TestModelORM, skip=4, size=2)

    ids = [item.id for item in page1 + page2 + page3]

    assert ids == sorted(ids)
    assert len(set(ids)) == 5


@pytest.mark.asyncio
async def test_read_sessions_do_not_commit(db, mocker, make_test_model):
    """get/get_all/count pass commit=False; a read must not issue a COMMIT."""
    await db.create(make_test_model())

    commit_spy = mocker.patch.object(AsyncSession, "commit", new_callable=AsyncMock)

    await db.get(TestModelORM, 1)
    await db.get_all(TestModelORM, skip=0, size=10)
    await db.count(TestModelORM)

    assert commit_spy.await_count == 0

    # writes still commit
    await db.create(make_test_model())
    assert commit_spy.await_count == 1
