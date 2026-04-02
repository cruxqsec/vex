import asyncio
from pathlib import Path

from vex_cli.database.projects_db import ProjectsDatabase
from vex_cli.database.raw_db import RawDatabase
from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.errors import DatabaseError
from vex_cli.locations import vex_projects_db_path


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
        if self._projects_db is None:
            raise DatabaseError(
                "No projects database — projects database not initialized"
            )
        return self._projects_db

    def get_summaries_db(self) -> SummariesDatabase:
        if self._summaries_db is None:
            raise DatabaseError(
                "No active project — summaries database not initialized"
            )
        return self._summaries_db

    def get_raw_db(self) -> RawDatabase:
        if self._raw_db is None:
            raise DatabaseError("No active project — raw database not initialized")
        return self._raw_db

    async def initialize(self):
        """Initializes the projects databases and create tables if they don't exist."""
        await self._projects_db.initialize()

    async def switch_project_databases(self, new_db_path: Path):
        """Switches and initializes another project database."""
        async with self._lock:
            if self._summaries_db:
                await self._summaries_db.close()
                self._summaries_db = None
            if self._raw_db:
                await self._raw_db.close()
                self._raw_db = None

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
