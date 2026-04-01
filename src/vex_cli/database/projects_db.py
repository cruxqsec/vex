from vex_cli.database.base_db import BaseDatabase
from vex_cli.models.orm import ProjectORM


class ProjectsDatabase(BaseDatabase):
    _orm_models = [ProjectORM]
    _wal_mode = False
