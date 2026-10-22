import hashlib
import json
import random
import string
import time
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from mitmproxy import http
from mitmproxy.test import tflow, tutils

from vex_cli.app import create_app
from vex_cli.database.db_manager import DatabaseManager
from vex_cli.database.projects_db import ProjectsDatabase
from vex_cli.database.raw_db import RawDatabase
from vex_cli.database.summaries_db import SummariesDatabase
from vex_cli.dependencies import (
    get_projects_db,
    get_raw_db,
    get_summaries_db,
)
from vex_cli.flow_history import FlowHistory
from vex_cli.flow_scope import FlowScope
from vex_cli.models.orm import (
    ProjectORM,
    RawRequestORM,
    RawResponseORM,
    RequestSummaryORM,
    ResponseSummaryORM,
    ScopeORM,
)
from vex_cli.models.pydantic import (
    Project,
    ProjectCreate,
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
    Scope,
    ScopeCreate,
    ServerMetaData,
    VexServerInfo,
)
from vex_cli.state import VexState


def random_hash(length) -> str:
    word = "".join(random.choice(string.ascii_lowercase) for i in range(length))
    hash = hashlib.md5(word.encode())
    return hash.hexdigest()


@pytest.fixture
def req_res_flow() -> http.HTTPFlow:
    timestamp = time.time()
    req = tutils.treq(
        host="example.com",
        scheme="https",
        method="GET",
        path="/path/to/content.php?query=test&query2=test2",
        content=b"",
        timestamp_start=timestamp,
        timestamp_end=timestamp + 50,
    )

    html = b"""<!doctype html>
    <html lang="en">
    <head>
        <title>Example title</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <body>
        <div>
            <h1>Example Domain</h1>
            <p><a href="https://iana.org/domains/example">Learn more</a>
        </div>
    </body>
    </html>"""

    res_headers = [
        (b"Accept-Ranges", b"bytes"),
        (b"Content-Type", b"text/html; charset=utf-8"),
        (b"Vary", b"Accept-Encoding"),
        (b"Set-Cookie", b"test_token=random-test-cookie"),
        (b"Content-Length", str(len(html)).encode()),
        (b"Connection", b"keep-alive"),
    ]

    resp = tutils.tresp(
        status_code=200,
        headers=res_headers,
        content=html,
        timestamp_start=timestamp + 100,
        timestamp_end=timestamp + 150,
    )

    flow = tflow.tflow(req=req, resp=resp)

    return flow


@pytest.fixture
def req_no_resp_flow() -> http.HTTPFlow:
    timestamp = time.time()
    req = tutils.treq(
        host="example.com",
        scheme="https",
        method="GET",
        path="/path/to/content.php?query=test&query2=test2",
        content=b"",
        timestamp_start=timestamp,
        timestamp_end=timestamp,
    )

    flow = tflow.tflow(req=req, resp=False)

    return flow


@pytest.fixture
def binary_flow() -> http.HTTPFlow:
    timestamp = time.time()
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    resp_headers = [
        (b"Content-Type", b"image/png"),
        (b"Content-Length", str(len(png_bytes)).encode()),
    ]
    req = tutils.treq(
        host="cdn.example.com",
        scheme="https",
        method="GET",
        path="/img.png",
        content=b"",
        timestamp_start=timestamp,
        timestamp_end=timestamp,
    )
    resp = tutils.tresp(status_code=200, headers=resp_headers, content=png_bytes)
    return tflow.tflow(req=req, resp=resp)


@pytest.fixture
def server_info():
    return VexServerInfo(
        server_address="127.0.0.1",
        proxy_port=8080,
        api_port=8081,
    )


@pytest.fixture
def project():
    def _factory(**kwargs):
        defaults = {
            "id": uuid4(),
            "name": random_hash(10),
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        return Project(**(defaults | kwargs))

    return _factory


@pytest.fixture
def request_summary():
    def _factory(**kwargs):
        defaults = {
            "id": None,
            "flow_id": uuid4(),
            "host": "example.com",
            "method": "GET",
            "path": "/example/to/resource",
            "is_tls": True,
            "request_size": 100,
            "query": "?test=1",
            "file_extension": None,
            "timestamp": time.time(),
        }
        return RequestSummary(**(defaults | kwargs))

    return _factory


@pytest.fixture
def response_summary():

    def _factory(**kwargs):
        defaults = {
            "id": None,
            "flow_id": uuid4(),
            "status_code": 200,
            "response_size": 500,
            "mime": "text/html",
            "http_title": "Example site",
            "cookie": "",
            "duration_ms": 50,
            "timestamp": time.time(),
        }
        return ResponseSummary(**(defaults | kwargs))

    return _factory


@pytest.fixture
def raw_request():
    return RawRequest(
        id=uuid4(),
        data=b"POST /upload HTTP/1.1\r\nHost: example.com\r\n\r\n\x89PNG\r\n\x1a\n",
    )


@pytest.fixture
def raw_response():
    return RawResponse(
        id=uuid4(),
        data=b"HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n\x89PNG\r\n\x1a\n",
    )


@pytest.fixture
def scope():
    return Scope(
        id=42,
        name="Production Scope",
        allow_endpoints=["192.168.1.1"],
        deny_endpoints=["10.0.0.1", "evil.com"],
    )


@pytest.fixture
def empty_scope():
    return Scope(id=1, name="Empty Scope", allow_endpoints=[], deny_endpoints=[])


@pytest.fixture
def allow_only_scope():
    return Scope(
        id=2,
        name="Allow Only",
        allow_endpoints=["example.com", "127.0.0.1"],
        deny_endpoints=[],
    )


@pytest.fixture
def deny_only_scope():
    return Scope(
        id=3,
        name="Deny Only",
        allow_endpoints=[],
        deny_endpoints=["malicious.com", "192.168.1.1"],
    )


@pytest.fixture
def scope_create():
    return ScopeCreate(
        name="New Scope",
        allow_endpoints=["192.168.1.1"],
        deny_endpoints=["evil.com"],
    )


@pytest.fixture
def project_orm():
    def _factory(**kwargs):
        defaults = {
            "id": uuid4(),
            "name": random_hash(10),
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        return ProjectORM(**(defaults | kwargs))

    return _factory


@pytest.fixture
def request_summary_orm():
    def _factory(**kwargs):
        defaults = {
            "flow_id": uuid4(),
            "host": "example.com",
            "method": "GET",
            "path": "/test/path",
            "request_size": 123,
            "is_tls": True,
            "query": "?test=queryparam",
            "file_extension": ".php",
            "timestamp": 5034566.34,
        }
        return RequestSummaryORM(**(defaults | kwargs))

    return _factory


@pytest.fixture
def response_summary_orm():
    def _factory(**kwargs):
        defaults = {
            "flow_id": uuid4(),
            "status_code": 200,
            "response_size": 2134,
            "mime": "html/text",
            "http_title": "Example title",
            "cookie": "test_cookie=value",
            "duration_ms": 345,
            "timestamp": 324569.43,
        }
        return ResponseSummaryORM(**(defaults | kwargs))

    return _factory


@pytest.fixture
def raw_request_orm():
    def _factory(**kwargs):
        defaults = {
            "id": uuid4(),
            "data": b"POST /upload HTTP/1.1\r\nHost: example.com\r\n\r\n\x89PNG\r\n\x1a\n",
        }
        return RawRequestORM(**(defaults | kwargs))

    return _factory


@pytest.fixture
def raw_response_orm():
    def _factory(**kwargs):
        defaults = {
            "id": uuid4(),
            "data": b"HTTP/1.1 200 OK\r\nContent-Type: image/png\r\n\r\n\x89PNG\r\n\x1a\n",
        }
        return RawResponseORM(**(defaults | kwargs))

    return _factory


@pytest.fixture
def scope_orm():
    def _factory(**kwargs):
        defaults = {
            "name": random_hash(10),
            "definitions": json.dumps(
                {
                    "allow": [],
                    "deny": [],
                }
            ),
        }
        return ScopeORM(**(defaults | kwargs))

    return _factory


@pytest_asyncio.fixture
async def projects_db(tmp_path: Path):
    database = ProjectsDatabase(db_path=tmp_path / "projects.db")
    await database.initialize()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def summary_db(tmp_path: Path):
    database = SummariesDatabase(db_path=tmp_path / "summaries.db")
    await database.initialize()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def raw_db(tmp_path: Path):
    database = RawDatabase(db_path=tmp_path / "raw.db")
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def pid_file(tmp_path) -> Path:
    return tmp_path / "vex.pid"


@pytest.fixture
def flow_history():
    return FlowHistory()


@pytest.fixture
def flow_scope():
    return FlowScope()


@pytest_asyncio.fixture
async def bare_manager(tmp_path, mocker):
    mocker.patch(
        "vex_cli.database.db_manager.vex_projects_db_path",
        return_value=tmp_path / "projects.db",
    )
    manager = DatabaseManager()
    yield manager
    await manager.close()


@pytest.fixture
def folder_a(tmp_path):
    path = tmp_path / "project-a"
    path.mkdir()
    return path


@pytest.fixture
def folder_b(tmp_path):
    path = tmp_path / "project-b"
    path.mkdir()
    return path


@pytest.fixture
def db_manager(monkeypatch, tmp_path, projects_db, summary_db, raw_db):
    monkeypatch.setattr(
        "vex_cli.database.db_manager.vex_projects_db_path",
        lambda: tmp_path / "projects.db",
    )
    manager = DatabaseManager()
    manager._projects_db = projects_db
    manager._summaries_db = summary_db
    manager._raw_db = raw_db
    return manager


@pytest.fixture
def state(server_info, db_manager, flow_history, flow_scope):
    state = VexState(server_info)
    state._db_manager = db_manager
    state._flow_scope = flow_scope
    state._flow_history = flow_history
    return state


@pytest.fixture
def app(state):
    app = create_app()
    app.state.vex_state = state
    return app


@pytest.fixture
def projects_dir(tmp_path, monkeypatch):
    path = tmp_path / "projects"
    path.mkdir()
    monkeypatch.setattr(
        "vex_cli.api.projects_routes.vex_projects_directory", lambda: path
    )
    return path


@pytest_asyncio.fixture
async def client(app, projects_dir):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


from contextlib import asynccontextmanager


@pytest.fixture
def ws_connect(app):
    @asynccontextmanager
    async def _connect(path):
        async with AsyncClient(
            transport=ASGIWebSocketTransport(app), base_url="http://test"
        ) as c:
            async with aconnect_ws(f"http://test/ws{path}", c) as ws:
                yield ws

    return _connect
