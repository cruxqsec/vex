"""
API routes for the application.

- websockets: Websocket routes, used for bidirectional communication
- rest: Classical CRUD API for projects, raw requests/response, summary requests/response,...
"""

from . import websockets
from . import projects_routes
from . import raw_request_routes
from . import raw_response_routes
from . import request_summary_routes
from . import response_summary_routes

__all__ = ["websockets", "projects_routes", "raw_request_routes",
           "raw_response_routes", "request_summary_routes", "response_summary_routes"]
