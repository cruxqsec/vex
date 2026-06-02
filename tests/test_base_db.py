import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from pathlib import Path
from sqlalchemy import String, Uuid, LargeBinary, DateTime, inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4
from datetime import datetime

from vex_cli.models.orm import Base
from vex_cli.database.base_db import BaseDatabase
from vex_cli.errors import DatabaseError, NotFoundError, ValidationError


# Minimal throwaway model
class _TestModelORM(Base):
    __tablename__ = "test_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[UUID] = mapped_column(Uuid, unique=True)
    name: Mapped[str] = mapped_column(String)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    date_time: Mapped[datetime] = mapped_column(DateTime)


# Concrete subclass of BaseDatabase
class _TestModelDB(BaseDatabase):
    _orm_models = [_TestModelORM]
    _wal_mode = True


@pytest.fixture
def mock_test_model() -> _TestModelORM:
    return _TestModelORM(
        uuid=uuid4(),
        name="test_item",
        blob=b"randombytestring",
        date_time=datetime.now(),
    )


@pytest.fixture
def make_test_model():
    def _factory(**kwargs):
        defaults = {
            "uuid": uuid4(),
            "name": "test_item",
            "blob": b"randombytestring",
            "date_time": datetime.now(),
        }
        return _TestModelORM(**{**defaults, **kwargs})

    return _factory


@pytest_asyncio.fixture
async def db(tmp_path: Path):
    """Fresh in-memory DB per test."""
    database = _TestModelDB(db_path=tmp_path / "test.db")
    await database.initialize()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_initialize_creates_engine(tmp_path):
    database = _TestModelDB(db_path=tmp_path / "test.db")
    assert database._engine is None

    await database.initialize()

    assert database._engine is not None
    await database.close()


@pytest.mark.asyncio
async def test_catch_exception_create_tables(tmp_path):
    database = _TestModelDB(db_path=tmp_path / "test.db")
    assert database._engine is None

    with pytest.raises(DatabaseError):
        await database._create_tables()


@pytest.mark.asyncio
async def test_catch_exception_wal_mode(tmp_path):
    database = _TestModelDB(db_path=tmp_path / "test.db")
    assert database._engine is None

    with pytest.raises(DatabaseError):
        await database._enable_wal()


@pytest.mark.asyncio
async def test_initialize_raises_database_error_on_engine_failure(tmp_path, mocker):
    mocker.patch(
        "vex_cli.database.base_db.create_async_engine",
        side_effect=SQLAlchemyError("connection failed"),
    )

    db = _TestModelDB(db_path=tmp_path / "test.db")

    with pytest.raises(DatabaseError, match="Error initializing database"):
        await db.initialize()


@pytest.mark.asyncio
async def test_engine_is_none_after_failed_initialize(tmp_path, mocker):
    mocker.patch(
        "vex_cli.database.base_db.create_async_engine",
        side_effect=SQLAlchemyError("failed"),
    )

    db = _TestModelDB(db_path=tmp_path / "test.db")

    with pytest.raises(DatabaseError):
        await db.initialize()

    assert db._engine is None


@pytest.mark.asyncio
async def test_initialize_twice(tmp_path):
    """Calling initialize() twice should not raise or recreate the engine."""
    database = _TestModelDB(db_path=tmp_path / "test.db")
    await database.initialize()
    engine_before = database._engine

    await database.initialize()  # second call

    assert database._engine is engine_before  # same engine, not recreated
    await database.close()


@pytest.mark.asyncio
async def test_tables_are_created(db):
    async with db._engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )

    assert len(tables) == 1
    assert "test_items" in tables


@pytest.mark.asyncio
async def test_create_returns_object_with_id(db, mock_test_model):
    item = await db.create(mock_test_model)

    assert item.id is not None
    assert type(item.uuid) is UUID
    assert item.name == "test_item"


@pytest.mark.asyncio
async def test_get_returns_correct_object(db, mock_test_model):
    created = await db.create(mock_test_model)

    fetched = await db.get(_TestModelORM, created.id)

    assert type(fetched.id) is int
    assert fetched.id == created.id
    assert type(fetched.uuid) is UUID
    assert fetched.uuid == created.uuid
    assert fetched.name == created.name
    assert fetched.date_time == created.date_time
    assert fetched.blob == created.blob


@pytest.mark.asyncio
async def test_get_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await db.get(_TestModelORM, 99999)


@pytest.mark.asyncio
async def test_get_all_returns_all_items1(db, make_test_model):
    for i in range(3):
        await db.create(make_test_model())

    result = await db.get_all(_TestModelORM, skip=0, size=10)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_all_skip_all(db, make_test_model):
    for i in range(8):
        await db.create(make_test_model())

    result = await db.get_all(_TestModelORM, skip=9, size=1)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_get_all_too_many(db, make_test_model):
    for i in range(5):
        await db.create(make_test_model())

    result = await db.get_all(_TestModelORM, skip=2, size=8)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_all_correct_pagination(db, make_test_model):
    for i in range(15):
        await db.create(make_test_model())

    page = await db.get_all(_TestModelORM, skip=6, size=5)

    assert len(page) == 5


@pytest.mark.asyncio
async def test_get_all_empty(db):
    result = await db.get_all(_TestModelORM, skip=0, size=10)

    assert result == []


@pytest.mark.asyncio
async def test_update_changes_value(db, mock_test_model):
    item = await db.create(mock_test_model)
    item.name = "new_name"
    new_uuid = uuid4()
    item.uuid = new_uuid

    await db.update(_TestModelORM, item)
    fetched = await db.get(_TestModelORM, item.id)

    assert fetched.name == "new_name"
    assert fetched.uuid == new_uuid


@pytest.mark.asyncio
async def test_update_raises_not_found(db, mock_test_model):
    non_existent = mock_test_model
    non_existent.id = 99999
    non_existent.uuid = uuid4()

    with pytest.raises(NotFoundError):
        await db.update(_TestModelORM, non_existent)


@pytest.mark.asyncio
async def test_delete_removes_object(db, mock_test_model):
    item = await db.create(mock_test_model)

    await db.delete(_TestModelORM, item.id)

    with pytest.raises(NotFoundError):
        await db.get(_TestModelORM, item.id)


@pytest.mark.asyncio
async def test_delete_all_removes_everything(db, make_test_model):
    for _ in range(5):
        await db.create(make_test_model())

    await db.delete_all(_TestModelORM)

    result = await db.get_all(_TestModelORM, skip=0, size=100)
    assert result == []


@pytest.mark.asyncio
async def test_delete_all_empty_table_does_not_raise(db):
    await db.delete_all(_TestModelORM)


@pytest.mark.asyncio
async def test_delete_raises_not_found(db):
    with pytest.raises(NotFoundError):
        await db.delete(_TestModelORM, 99999)


@pytest.mark.asyncio
async def test_close_disposes_engine(db, mocker):
    mock_dispose = mocker.patch.object(AsyncEngine, "dispose", new_callable=AsyncMock)

    await db.close()

    mock_dispose.assert_called_once()


@pytest.mark.asyncio
async def test_close_without_initialize_does_nothing(tmp_path):
    db = _TestModelDB(db_path=tmp_path / "test.db")
    assert db._engine is None

    await db.close()  # should not raise


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

    with pytest.raises(ValidationError, match="Record already exists"):
        await db.create(make_test_model(uuid=shared_uuid))


@pytest.mark.asyncio
async def test_wal_enabled_after_initialize(tmp_path):
    database = _TestModelDB(db_path=tmp_path / "test.db")  # _wal_mode = True
    await database.initialize()

    if database._engine is None:
        return

    async with database._engine.connect() as conn:
        result = await conn.execute(text("PRAGMA journal_mode;"))
        mode = result.scalar()

    await database.close()
    assert mode == "wal"
