import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import ClassVar, TypeVar, cast
from uuid import UUID

from sqlalchemy import CursorResult, Table, func, select, text
from sqlalchemy import delete as sa_delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.asyncio.session import AsyncSession

from vex_cli.errors import (
    ConflictError,
    DatabaseError,
    NotFoundError,
)
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
    _orm_models: ClassVar[list[type[Base]]] = []
    # and if WAL will be used
    _wal_mode: ClassVar[bool] = False

    def __init__(self, db_path: Path):
        self.db_path: Path = db_path
        self._lock = asyncio.Lock()

        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    async def initialize(self) -> None:
        """Connect to database and create tables"""
        async with self._lock:
            if self._engine:
                return

            engine: AsyncEngine | None = None
            try:
                engine = create_async_engine(
                    f"sqlite+aiosqlite:///{self.db_path}",
                    connect_args={"timeout": 10},
                )

                await self._create_tables(engine)

                if self._wal_mode:
                    await self._enable_wal(engine)

            except SQLAlchemyError as e:
                if engine is not None:
                    try:
                        await engine.dispose()
                    except SQLAlchemyError:
                        pass
                raise DatabaseError("Error initializing database") from e

            self._engine = engine
            self._session_maker = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    async def _create_tables(self, engine: AsyncEngine) -> None:
        """Creates specific table based on ORM modles specified in subclass."""
        tables = [cast(Table, model.__table__) for model in self._orm_models]

        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables)
            )

    async def _enable_wal(self, engine: AsyncEngine) -> None:
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))

    @asynccontextmanager
    async def session(self, *, commit: bool = True) -> AsyncGenerator[AsyncSession]:
        """Get a database session."""

        if not self._session_maker:
            raise DatabaseError("Session not initialized")
        async with self._session_maker() as s:
            try:
                yield s
                if commit:
                    await s.commit()
            except IntegrityError as e:
                await s.rollback()
                if "unique" in str(e.orig).lower():
                    raise ConflictError("Record already exists") from e
                raise ConflictError("Database constraint violated") from e
            except SQLAlchemyError as e:
                await s.rollback()
                raise DatabaseError("Database operation failed") from e

    async def create(self, obj: T) -> T:
        async with self.session(commit=True) as s:
            s.add(obj)
            await s.flush()
            await s.refresh(obj)
            return obj

    # accepts both because some models have int and others UUID as PK!
    async def get(self, model: type[T], id: UUID | int) -> T:
        async with self.session(commit=False) as s:
            obj = await s.get(model, id)
            if not obj:
                raise NotFoundError(f"{model.__name__} with id {id} not found")
            return obj

    async def get_all(self, model: type[T], skip: int, size: int) -> list[T]:
        async with self.session(commit=False) as s:
            result = await s.execute(
                select(model).order_by(model.id).offset(skip).limit(size)  # type: ignore
            )
            return list(result.scalars().all())

    async def update(self, model: type[T], obj: T) -> None:
        async with self.session(commit=True) as s:
            existing_obj = await s.get(model, obj.id)  # type: ignore (all vex models have id)
            if not existing_obj:
                raise NotFoundError(
                    f"{model.__name__} with id {obj.id} could not be updated"  # type: ignore
                )
            await s.merge(obj)

    async def delete(self, model: type[T], id: UUID | int) -> None:
        async with self.session(commit=True) as s:
            result = cast(CursorResult, await s.execute( sa_delete(model).where(model.id == id))) # type: ignore
            if result.rowcount == 0:
                raise NotFoundError(f"{model.__name__} with id {id} could not be deleted")

    async def delete_all(self, model: type[T]) -> None:
        async with self.session(commit=True) as s:
            await s.execute(sa_delete(model))

    async def count(self, model: type[T]) -> int:
        async with self.session(commit=False) as s:
            result = await s.execute(select(func.count()).select_from(model))
            return result.scalar() or 0

    async def close(self) -> None:
        async with self._lock:
            if self._engine:
                try:
                    await self._engine.dispose()
                    self._engine = None
                    self._session_maker = None
                except SQLAlchemyError as e:
                    raise DatabaseError("Database failed to close") from e
