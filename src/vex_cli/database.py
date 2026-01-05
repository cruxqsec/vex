import asyncio
from uuid import UUID
from pathlib import Path
from typing import List, Type, TypeVar, Type
from contextlib import asynccontextmanager

from sqlmodel import SQLModel, select, text
from sqlalchemy import select, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from vex_cli.models import (
    RequestSummary, 
    ResponseSummary, 
    Project, 
    RawRequest, 
    RawResponse
)
from vex_cli.locations import vex_projects_db_path
from vex_cli.errors import DatabaseError, ValidationError, NotFoundError

import logging
logger = logging.getLogger(__name__)

# Generic
T = TypeVar('T', bound=SQLModel)

class BaseDatabase:
    """
    Simple database class with generic CRUD operations
    All the model tables are passed in subclasses
    """
    
    def __init__(self, db_path: Path, models: List[Type[SQLModel]]):
        self.db_path: Path = db_path
        self.models: List[Type[SQLModel]] = models
        self.engine: AsyncEngine | None = None
        self.session_maker: sessionmaker | None = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Connect to database and create tables"""
        async with self._lock:
            try:
                if self.engine:
                    return
                
                self.engine = create_async_engine(f"sqlite+aiosqlite:///{str(self.db_path)}")
                
                self.session_maker = sessionmaker(
                    self.engine,  # type: ignore
                    class_=AsyncSession, 
                    expire_on_commit=False
                ) # type: ignore
                await self.create_tables_if_not_created()
            except SQLAlchemyError as e:
                logger.error(f"Database error: {e}")
                raise DatabaseError("Error initializing database")

                            
    async def create_tables_if_not_created(self) -> None:
        metadata = MetaData()
        for model in self.models:
            table = getattr(model, "__table__", None)
            if table is not None:
                table.tometadata(metadata)

        if not self.engine:
            raise DatabaseError("Engine not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

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
                if 'unique' in error_msg or 'duplicate' in error_msg:
                    raise ValidationError("Record already exists")
                elif 'foreign key' in error_msg:
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
    
    async def get(self, model: Type[T], id: UUID | int) -> T | None:
        async with self.session() as s:
            obj = await s.get(model, id)
            if not obj:
                raise NotFoundError("Object not found")
            return obj
    
    async def get_all(self, model: Type[T]) -> List[T]:
        async with self.session() as s:
            result = await s.execute(select(model))
            return list(result.scalars().all())
    
    async def update(self, model: Type[T], obj: T) -> None:
        async with self.session() as s:
            existing_obj = await s.get(model, obj.id) # type: ignore (all vex models have id)
            if not existing_obj:
                raise NotFoundError("Object could not be updated")
            await s.merge(obj)
    
    async def delete(self, model: Type[T], id: UUID | int) -> None:
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
    def __init__(self, db_path: Path):
        super().__init__(db_path, [Project])
        
class SummariesDatabase(BaseDatabase):
    def __init__(self, db_path: Path):
        super().__init__(db_path, [RequestSummary, ResponseSummary])

    async def initialize(self):
        await super().initialize()
        
        if not self.engine:
            raise DatabaseError("Engine not initialized")

        # Enable WAL (Write after logging)
        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
        
    async def get_by_flow_id(self, model: RequestSummary | ResponseSummary, id: UUID):
        pass

class RawDatabase(BaseDatabase):
    def __init__(self, db_path: Path):
        super().__init__(db_path, [RawRequest, RawResponse])

    async def initialize(self):
        await super().initialize()
        
        if not self.engine:
            raise DatabaseError("Engine not initialized")

        # Enable WAL (Write after logging)
        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))

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
        self._projectsDB : ProjectsDatabase = ProjectsDatabase(vex_projects_db_path())
        self._summariesDB : SummariesDatabase | None = None
        self._rawDB : RawDatabase | None = None
        self._lock = asyncio.Lock()
        
    def get_raw_db(self) -> RawDatabase | None:
        return self._rawDB
                
    def get_summaries_db(self) -> SummariesDatabase | None:
        return self._summariesDB

    def get_projects_db(self) -> ProjectsDatabase | None:
        return self._projectsDB

    async def initialize(self):
        """Initializes the projects databases and create tables if they don't exist."""
        await self._projectsDB.initialize()
        
    async def switch_project_databases(self, new_db_path: Path):
        """
        Switches and initializes another project database.
        """
        async with self._lock:
            if self._summariesDB:
                await self._summariesDB.close()
            if self._rawDB:
                await self._rawDB.close()

            self._summariesDB = SummariesDatabase(new_db_path/"main.db")
            self._rawDB = RawDatabase(new_db_path/"raw.db")
            
            await self._summariesDB.initialize()
            await self._rawDB.initialize()

    async def close(self) -> None:
        tasks = []
        for db in [self._projectsDB, self._rawDB, self._summariesDB]:
            if db:
                tasks.append(db.close())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
