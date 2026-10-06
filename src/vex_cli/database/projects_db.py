from vex_cli.database.base_db import BaseDatabase
from vex_cli.errors import NotFoundError
from vex_cli.models.orm import ProjectORM
from uuid import UUID


class ProjectsDatabase(BaseDatabase):
    _orm_models = [ProjectORM]
    _wal_mode = False

    async def update_name(self, project_id: UUID, name: str) -> None:
        """Update only the project name; DB-managed timestamps stay untouched."""
        async with self.session() as s:
            obj = await s.get(ProjectORM, project_id)
            if not obj:
                raise NotFoundError("Project could not be updated")
            obj.name = name
