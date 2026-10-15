import json
import time
from uuid import UUID

from mitmproxy import http
from pytest import approx

from vex_cli.flow_helper import flow_to_raw_request, flow_to_raw_response
from vex_cli.models.pydantic import (
    RawRequest,
    RawResponse,
    RequestSummary,
    ResponseSummary,
    Scope,
    ScopeCreate,
)


def test_request_summary(req_res_flow: http.HTTPFlow):
    now = time.time()
    raw = flow_to_raw_request(req_res_flow)
    summary = RequestSummary.from_flow(req_res_flow, raw)

    assert type(summary.flow_id) is UUID
    assert summary.host == "example.com"
    assert summary.method == "GET"
    assert summary.path == "/path/to/content.php"
    assert summary.request_size == 96
    assert summary.timestamp == approx(now, abs=10)
    assert summary.is_tls
    assert summary.query == "query=test&query2=test2"
    assert summary.file_extension == ".php"


def test_response_summary(req_res_flow: http.HTTPFlow):
    now = time.time()
    raw = flow_to_raw_response(req_res_flow)
    summary = ResponseSummary.from_flow(req_res_flow, raw)

    assert type(summary.flow_id) is UUID
    assert summary.status_code == 200
    assert summary.response_size == 530
    assert summary.mime == "text/html"
    assert summary.timestamp == approx(now, abs=100)
    assert summary.http_title == "Example title"
    assert summary.cookie == "test_token=random-test-cookie"
    assert summary.duration_ms == 50000


def test_req_summary_serialize(req_res_flow: http.HTTPFlow):
    summary = RequestSummary.from_flow(req_res_flow, flow_to_raw_request(req_res_flow))
    json_str = summary.model_dump_json()

    # then the summary is sent over the network and recieved
    recieved_summary = RequestSummary.model_validate_json(json_str)

    assert summary == recieved_summary
    assert type(recieved_summary.flow_id) is UUID


def test_raw_request(req_res_flow: http.HTTPFlow):
    raw_req = RawRequest.from_flow(req_res_flow)
    raw_result = (
        b"GET /path/to/content.php?query=test&query2=test2 HTTP/1.1\r\n"
        b"header: qvalue\r\n"
        b"content-length: 0\r\n\r\n"
    )

    assert type(raw_req.id) is UUID
    assert raw_req.data == raw_result


def test_raw_response(req_res_flow: http.HTTPFlow):
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

    raw_result = (
        b"HTTP/1.1 200 OK\r\n"
        b"Accept-Ranges: bytes\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"Vary: Accept-Encoding\r\n"
        b"Set-Cookie: test_token=random-test-cookie\r\n"
        b"Content-Length: 338\r\n"
        b"Connection: keep-alive\r\n\r\n" + html
    )

    raw_res = RawResponse.from_flow(req_res_flow)

    assert type(raw_res.id) is UUID
    assert raw_res.data == raw_result


def test_raw_req_serialize(raw_request: RawRequest):
    json_bytes = raw_request.model_dump_json()
    parsed = RawRequest.model_validate_json(json_bytes)
    assert parsed.id == raw_request.id


def test_raw_res_serialize(raw_response: RawResponse):
    json_bytes = raw_response.model_dump_json()
    parsed = RawResponse.model_validate_json(json_bytes)
    assert parsed.id == raw_response.id


def test_raw_res_serialize_none(raw_response: RawResponse):
    raw_response.data = None
    json_bytes = raw_response.model_dump_json()
    parsed = RawResponse.model_validate_json(json_bytes)
    assert parsed.data is None


def test_raw_request_to_orm_preserves_bytes(raw_request: RawRequest):
    raw_request.data = b"\xff\xfe\x00\x01"
    orm = raw_request.to_orm()
    assert orm.data == b"\xff\xfe\x00\x01"


def test_raw_response_to_orm_preserves_bytes(raw_response: RawResponse):
    raw_response.data = b"\x89PNG\r\n\x1a\n"
    orm = raw_response.to_orm()
    assert orm.data == b"\x89PNG\r\n\x1a\n"


def test_scope_to_orm_and_back_roundtrip(scope: Scope):
    orm = scope.to_orm()
    assert orm.id == 42
    assert orm.name == "Production Scope"

    back = Scope.from_orm(orm)
    assert back.id == 42
    assert back.name == "Production Scope"
    assert back.allow_endpoints == ["192.168.1.1"]
    assert back.deny_endpoints == ["10.0.0.1", "evil.com"]


def test_scope_to_orm_and_back_roundtrip_empty(empty_scope: Scope):
    orm = empty_scope.to_orm()
    assert orm.id == 1
    assert orm.name == "Empty Scope"

    back = Scope.from_orm(orm)
    assert back.id == 1
    assert back.name == "Empty Scope"
    assert back.allow_endpoints == []
    assert back.deny_endpoints == []


def test_scope_create_to_orm(scope_create: ScopeCreate):
    orm = scope_create.to_orm()
    assert orm.name == "New Scope"
    assert orm.id is None
    assert json.loads(orm.definitions) == {
        "allow": ["192.168.1.1"],
        "deny": ["evil.com"],
    }
