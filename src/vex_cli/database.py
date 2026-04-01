import asyncio
from uuid import UUID
from pathlib import Path
from typing import TypeVar, cast
from contextlib import asynccontextmanager

from sqlalchemy import Table, select, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker

from vex_cli.locations import vex_projects_db_path
from vex_cli.errors import DatabaseError, ValidationError, NotFoundError
from vex_cli.models.orm import (
    Base,
    RequestSummaryORM,
    ResponseSummaryORM,
    ProjectORM,
    RawRequestORM,
    RawResponseORM,
)

import logging

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

        self.engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker | None = None

    async def initialize(self) -> None:
        """Connect to database and create tables"""
        async with self._lock:
            try:
                if self.engine:
                    return

                self.engine = create_async_engine(f"sqlite+aiosqlite:///{self.db_path}")

                self.session_maker = async_sessionmaker(
                    bind=self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                await self._create_tables()

                if self._wal_mode:
                    self._enable_wal

            except SQLAlchemyError as e:
                logger.error(f"Database error: {e}")
                raise DatabaseError("Error initializing database")

    async def _create_tables(self) -> None:
        """Creates specific table based on ORM modles specified in subclass."""
        if not self.engine:
            raise DatabaseError("Engine not initialized")

        tables = [cast(Table, model.__table__) for model in self._orm_models]

        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    async def _enable_wal(self) -> None:
        if not self.engine:
            raise DatabaseError("Engine not initialized")

        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;")) 

    @asynccontextmanager
    async def session(self):
        """Get a database session"""

        if not self.session_maker:
            raise DatabaseError("Session not initialized")
        async with self.session_maker() as s:
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

    async def get(self, model: type[T], id: UUID | int) -> T | None:
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
            if self.engine:
                try:
                    await self.engine.dispose()
                except SQLAlchemyError as e:
                    logger.error(f"Database error: {e}")
                    raise DatabaseError("Database failed to close")


class ProjectsDatabase(BaseDatabase):
    _orm_models = [ProjectORM]
    _wal_mode = False


class SummariesDatabase(BaseDatabase):
    _orm_models = [RequestSummaryORM, ResponseSummaryORM]
    _wal_mode = True

    def __init__(self, db_path: Path):
        super().__init__(db_path)
        _exclude = {"id", "flow_id", "timestamp"}
        self._req_cols = [
            getattr(RequestSummaryORM, c.name) for c in RequestSummaryORM.__table__.columns
        ]
        self._res_cols = [
            getattr(ResponseSummaryORM, c.name) 
            for c in ResponseSummaryORM.__table__.columns if c.name not in _exclude
        ]

    async def get_full_summaries(self, skip: int, size: int) -> list:
        """List of full summaries (Request/ResponseSummary)"""
        async with self.session() as s:
            statement = (
                select(*self._req_cols, *self._res_cols)
                .outerjoin(
                    ResponseSummaryORM, RequestSummaryORM.flow_id == ResponseSummaryORM.flow_id
                )
                .offset(skip)
                .limit(size)
            )
            result = await s.execute(statement)
            return list(result.mappings().all())

    async def get_full_summary_by_id(self, flow_id: UUID) -> dict:
        """Get a single summary (Request/ResponseSummary). TODO: Improve return type!"""
        async with self.session() as s:
            statement = (
                select(*self._req_cols, *self._res_cols)
                .outerjoin(
                    ResponseSummaryORM, RequestSummaryORM.flow_id == ResponseSummaryORM.flow_id
                )
                .where(RequestSummaryORM.flow_id == flow_id)
            )
            result = await s.execute(statement)
            return result.mappings().first() # type: ignore


class RawDatabase(BaseDatabase):
    _orm_models = [RawRequestORM, RawResponseORM]
    _wal_mode = True
        

class DatabaseManager:
    """
    Manages SQLite databases with SQLAlchemy:
    Global app:
    - projects.db : Lives in the root directories and stores projects
    Per project:
    - summaries.db: Request and response summaries (separate tables)
    - raw_flows.db: Full request/response data (WAL mode)
    """

    def __init__(self):
        self._lock = asyncio.Lock()

        self._projects_db: ProjectsDatabase = ProjectsDatabase(vex_projects_db_path())
        self._summaries_db: SummariesDatabase | None = None
        self._raw_db: RawDatabase | None = None

    def get_projects_db(self) -> ProjectsDatabase:
        if self._summaries_db is None:
            raise DatabaseError("No projects database — projects database not initialized")
        return self._projects_db 

    def get_summaries_db(self) -> SummariesDatabase:
        if self._summaries_db is None:
            raise DatabaseError("No active project — summaries database not initialized")
        return self._summaries_db
 
    def get_raw_db(self) -> RawDatabase:
        if self._raw_db is None:
            raise DatabaseError("No active project — raw database not initialized")
        return self._raw_db
 
    async def initialize(self):
        """Initializes the projects databases and create tables if they don't exist."""
        await self._projects_db.initialize()

    async def switch_project_databases(self, new_db_path: Path):
        """
        Switches and initializes another project database.
        """
        async with self._lock:
            if self._summaries_db:
                await self._summaries_db.close()
            if self._raw_db:
                await self._raw_db.close()

            self._summaries_db = SummariesDatabase(new_db_path / "main.db")
            self._raw_db = RawDatabase(new_db_path / "raw.db")

            await self._summaries_db.initialize()
            await self._raw_db.initialize()

    async def close(self) -> None:
        """Close all databases."""
        tasks = []
        for db in [self._projects_db, self._raw_db, self._summaries_db]:
            if db:
                tasks.append(db.close())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
