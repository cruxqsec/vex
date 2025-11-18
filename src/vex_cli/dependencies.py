from fastapi import Request, WebSocket

from vex_cli.database import (
    DatabaseManager, 
    RawDatabase, 
    SummariesDatabase, 
    ProjectsDatabase
)
from vex_cli.flow_history import FlowHistory
from vex_cli.state import VexState
from vex_cli.errors import AppException

"""
    Functions used for dependency injection in FastAPI routes.
"""

def get_state_object(request: Request) -> VexState:
    return request.app.state.vex_state

def get_db_manager(request: Request) -> DatabaseManager:
    return request.app.state.vex_state.get_db_manager()

def get_flow_history(websocket: WebSocket) -> FlowHistory:
    return websocket.app.state.vex_state.get_flow_history()

def get_projects_db(request: Request) -> ProjectsDatabase:
    db = request.app.state.vex_state.get_db_manager().get_projects_db()
    if db is None:
        raise AppException("Not connected to projects database.", 400)
    return db

def get_summaries_db(request: Request) -> SummariesDatabase | None:
    db = request.app.state.vex_state.get_db_manager().get_summaries_db()
    if db is None:
        raise AppException("No project selected. Please select a project first.", 400)
    return db

def get_raw_db(request: Request) -> RawDatabase | None:
    db = request.app.state.vex_state.get_db_manager().get_raw_db()
    if db is None:
        raise AppException("No project selected. Please select a project first.", 400)
    return db
