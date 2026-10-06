import asyncio
import logging
from pathlib import Path

from vex_cli.database.projects_db import ProjectsDatabase
from vex_cli.database.raw_db import RawDatabase
from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.errors import DatabaseError, NoProjectActiveError
from vex_cli.locations import vex_projects_db_path

logger = logging.getLogger(__name__)


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

    @property
    def projects_db(self) -> ProjectsDatabase:
        if not self._projects_db:
            raise DatabaseError("Error - projects database not initialized")

        return self._projects_db

    @property
    def summaries_db(self) -> SummariesDatabase:
        if not self._summaries_db:
            raise NoProjectActiveError()
        return self._summaries_db

    @property
    def raw_db(self) -> RawDatabase:
        if not self._raw_db:
            raise NoProjectActiveError()
        return self._raw_db

    @property
    def is_project_active(self) -> bool:
        return self._raw_db is not None and self._summaries_db is not None

    async def initialize(self):
        """Initializes the ProjectsDatabase and create tables if they don't exist."""
        await self._projects_db.initialize()

    async def close_project_databases(self):
        """Close project databases without opening new ones."""
        async with self._lock:
            if self._summaries_db:
                await self._summaries_db.close()
                self._summaries_db = None
            if self._raw_db:
                await self._raw_db.close()
                self._raw_db = None

    def active_databases(self) -> tuple[SummariesDatabase, RawDatabase] | None:
        """Both project databases as one atomic snapshot, or None if no project is active."""
        summaries, raw = self._summaries_db, self._raw_db
        if summaries is None or raw is None:
            return None
        return summaries, raw

    async def switch_project_databases(self, new_db_path: Path) -> None:
        """Switches to another project's databases."""
        async with self._lock:
            new_summaries = SummariesDatabase(new_db_path / "main.db")
            new_raw = RawDatabase(new_db_path / "raw.db")
            try:
                results = await asyncio.gather(
                    new_summaries.initialize(),
                    new_raw.initialize(),
                    return_exceptions=True,
                )
                failures = [r for r in results if isinstance(r, BaseException)]
                if failures:
                    raise failures[0]
            except Exception:
                await asyncio.gather(
                    new_summaries.close(), new_raw.close(), return_exceptions=True
                )
                raise

            old_summaries, old_raw = self._summaries_db, self._raw_db
            self._summaries_db = new_summaries
            self._raw_db = new_raw

            if old_summaries:
                await old_summaries.close()
            if old_raw:
                await old_raw.close()

    async def close(self) -> None:
        """Close all databases and reset project state."""
        async with self._lock:
            databases = [
                db
                for db in (self._projects_db, self._summaries_db, self._raw_db)
                if db
            ]
            results = await asyncio.gather(
                *(db.close() for db in databases), return_exceptions=True
            )
            self._summaries_db = None
            self._raw_db = None
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Failed to close database: {result}")
