from vex_cli.database.base_db import BaseDatabase
from vex_cli.models.orm import RawRequestORM, RawResponseORM


class RawDatabase(BaseDatabase):
    _orm_models = [RawRequestORM, RawResponseORM]
    _wal_mode = True
