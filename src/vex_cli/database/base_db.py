import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypeVar, cast
from uuid import UUID

from sqlalchemy import Table, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vex_cli.errors import DatabaseError, NotFoundError, ValidationError
from vex_cli.models.orm import (
    Base,
)

logger = logging.getLogger(__name__)

# Generic
T = TypeVar("T", bound=Base)


class BaseDatabase:
    """
    Generic database class with CRUD operations
    """

    # where we declare which models will be used for which database
    _orm_models: list[type[Base]] = []
    _wal_mode: bool = False

    def __init__(self, db_path: Path):
        self.db_path: Path = db_path
        self._lock = asyncio.Lock()

        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    async def initialize(self) -> None:
        """Connect to database and create tables"""
        async with self._lock:
            try:
                if self._engine:
                    return

                self._engine = create_async_engine(
                    f"sqlite+aiosqlite:///{self.db_path}"
                )

                self._session_maker = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                await self._create_tables()

                if self._wal_mode:
                    await self._enable_wal()

            except SQLAlchemyError as e:
                logger.error(f"Database error: {e}")
                raise DatabaseError("Error initializing database")

    async def _create_tables(self) -> None:
        """Creates specific table based on ORM modles specified in subclass."""
        if not self._engine:
            raise DatabaseError("Engine not initialized")

        tables = [cast(Table, model.__table__) for model in self._orm_models]

        async with self._engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables)
            )

    async def _enable_wal(self) -> None:
        if not self._engine:
            raise DatabaseError("Engine not initialized")

        async with self._engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))

    @asynccontextmanager
    async def session(self):
        """Get a database session"""

        if not self._session_maker:
            raise DatabaseError("Session not initialized")
        async with self._session_maker() as s:
            try:
                yield s
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                logger.error(f"Integrity error: {e}")
                error_msg = str(e.orig).lower()
                if "unique" in error_msg or "duplicate" in error_msg:
                    raise ValidationError("Record already exists")
                elif "foreign key" in error_msg:
                    raise ValidationError("Invalid reference")
                else:
                    raise ValidationError("Constraint violation")
            except SQLAlchemyError as e:
                await s.rollback()
                logger.error(f"Database error: {e}")
                raise DatabaseError("Database operation failed")

    async def create(self, obj: T) -> T:
        async with self.session() as s:
            s.add(obj)
            await s.flush()
            await s.refresh(obj)
            return obj

    # accepts both because some models have int and others UUID as PK!
    async def get(self, model: type[T], id: UUID | int) -> T:
        async with self.session() as s:
            obj = await s.get(model, id)
            if not obj:
                raise NotFoundError("Object not found")
            return obj

    async def get_all(self, model: type[T], skip: int, size: int) -> list[T]:
        async with self.session() as s:
            result = await s.execute(select(model).offset(skip).limit(size))
            return list(result.scalars().all())

    async def update(self, model: type[T], obj: T) -> None:
        async with self.session() as s:
            existing_obj = await s.get(model, obj.id)  # type: ignore (all vex models have id)
            if not existing_obj:
                raise NotFoundError("Object could not be updated")
            await s.merge(obj)

    async def delete(self, model: type[T], id: UUID | int) -> None:
        async with self.session() as s:
            obj = await s.get(model, id)
            if not obj:
                raise NotFoundError("Object could not be deleted")
            await s.delete(obj)

    async def close(self) -> None:
        async with self._lock:
            if self._engine:
                try:
                    await self._engine.dispose()
                    self._engine = None
                    self._session_maker = None
                except SQLAlchemyError as e:
                    logger.error(f"Database error: {e}")
                    raise DatabaseError("Database failed to close")
