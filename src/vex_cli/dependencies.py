from fastapi import Request, WebSocket

from vex_cli.database import (
    DatabaseManager, 
    RawDatabase, 
    SummariesDatabase, 
    ProjectsDatabase
)
from vex_cli.flow_history import FlowHistory
from vex_cli.state import VexState

"""
    Functions used for dependency injection in FastAPI routes.
"""

def get_state_object(request: Request) -> VexState:
    return request.app.state.vex_state

def get_flow_history(websocket: WebSocket) -> FlowHistory:
    return websocket.app.state.vex_state.get_flow_history()

def get_db_manager(request: Request) -> DatabaseManager:
    return request.app.state.vex_state.get_db_manager()

def get_projects_db(request: Request) -> ProjectsDatabase:
    return request.app.state.vex_state.get_db_manager().get_projects_db()

def get_summaries_db(request: Request) -> SummariesDatabase | None:
    return request.app.state.vex_state.get_db_manager().get_summaries_db()

def get_raw_db(request: Request) -> RawDatabase | None:
    return request.app.state.vex_state.get_db_manager().get_raw_db()
