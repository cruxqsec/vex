from fastapi import Request, WebSocket

from vex_cli.database.db_manager import DatabaseManager
from vex_cli.database.projects_db import ProjectsDatabase
from vex_cli.database.raw_db import RawDatabase
from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.flow_history import FlowHistory
from vex_cli.flow_scope import FlowScope
from vex_cli.state import VexState

"""
    Functions used for dependency injection in FastAPI routes.
"""


def get_state_object(request: Request) -> VexState:
    return request.app.state.vex_state


def get_flow_history(websocket: WebSocket) -> FlowHistory:
    return websocket.app.state.vex_state.get_flow_history()


def get_flow_scope(request: Request) -> FlowScope:
    return request.app.state.vex_state.get_flow_scope()


def get_db_manager(request: Request) -> DatabaseManager:
    return request.app.state.vex_state.get_db_manager()


def get_projects_db(request: Request) -> ProjectsDatabase:
    return request.app.state.vex_state.get_db_manager().projects_db


def get_summaries_db(request: Request) -> SummariesDatabase | None:
    return request.app.state.vex_state.get_db_manager().summaries_db


def get_raw_db(request: Request) -> RawDatabase | None:
    return request.app.state.vex_state.get_db_manager().raw_db
