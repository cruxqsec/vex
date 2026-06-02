import pytest
from uuid import UUID
from datetime import datetime
from mitmproxy import http
from mitmproxy.test import tflow, tutils

from vex_cli.models.pydantic import (
    RequestSummary,
    ResponseSummary,
    RawRequest,
    RawResponse,
    Scope,
)


@pytest.fixture
def mock_flow() -> http.HTTPFlow:
    req = tutils.treq(
        host="example.com",
        scheme="http",
        method="GET",
        path="/path/to/content.php?query=test&query2=test2",
        content=b"",
        timestamp_end=50,
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
        timestamp_start=100,
    )

    flow = tflow.tflow(req=req, resp=resp)

    return flow


def test_request_summary(mock_flow: http.HTTPFlow):
    summary = RequestSummary.from_flow(mock_flow)
    now = datetime.timestamp(datetime.now())

    assert type(summary.flow_id) is UUID
    assert summary.host == "example.com"
    assert summary.method == "GET"
    assert summary.path == "/path/to/content.php"
    assert summary.request_size == 96
    assert not summary.is_tls
    assert summary.query == "query=test&query2=test2"
    assert summary.file_extension == ".php"

    # we round the timestamp to an int
    # because there is a few fractions of a ms difference
    assert int(summary.timestamp) == int(now)


def test_response_summary(mock_flow: http.HTTPFlow):
    summary = ResponseSummary.from_flow(mock_flow)
    now = datetime.timestamp(datetime.now())

    print("-----------")
    print(summary.cookie)
    print("-----------")

    assert type(summary.flow_id) is UUID
    assert summary.status_code == 200
    assert summary.response_size == 530
    assert summary.mime == "text/html"
    assert summary.http_title == "Example title"
    assert summary.cookie == "test_token=random-test-cookie"
    assert summary.duration_ms == 50000

    # we round the timestamp to an int
    # because there is a few fractions of a ms difference
    assert int(summary.timestamp) == int(now)


def test_req_summary_serialize(mock_flow: http.HTTPFlow):
    """Problematic test because of the problems of SQLModel"""
    summary = RequestSummary.from_flow(mock_flow)
    json_str = summary.model_dump_json()

    # then the summary is sent over the network and recieved
    recieved_summary = RequestSummary.model_validate_json(json_str)

    assert type(recieved_summary.flow_id) is UUID


def test_res_summary_serialize(mock_flow: http.HTTPFlow):
    """Problematic test because of the problems of SQLModel"""
    summary = ResponseSummary.from_flow(mock_flow)
    json_str = summary.model_dump_json()

    # then the summary is sent over the network and recieved
    recieved_summary = ResponseSummary.model_validate_json(json_str)

    assert summary == recieved_summary


def test_raw_request(mock_flow: http.HTTPFlow):
    raw_req = RawRequest.from_flow(mock_flow)
    raw_result = (
        b"GET /path/to/content.php?query=test&query2=test2 HTTP/1.1\r\n"
        b"header: qvalue\r\n"
        b"content-length: 7\r\n\r\n"
    )

    assert type(raw_req.id) is UUID
    assert raw_req.data == raw_result


def test_raw_response(mock_flow: http.HTTPFlow):
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

    raw_res = RawResponse.from_flow(mock_flow)

    assert type(raw_res.id) is UUID
    assert raw_res.data == raw_result


def test_raw_req_serialize():
    pass


def test_raw_res_serialize():
    pass


def test_scope_to_orm_and_back_roundtrip():
    scope = Scope(
        id=42,
        allow_endpoints=["192.168.1.1"],
        deny_endpoints=["10.0.0.1", "evil.com"],
    )

    orm = scope.to_orm()
    assert orm.id == 42

    back = Scope.from_orm(orm)
    assert back.id == 42
    assert back.allow_endpoints == ["192.168.1.1"]
    assert back.deny_endpoints == ["10.0.0.1", "evil.com"]


def test_scope_to_orm_and_back_roundtrip_empty():
    scope = Scope(id=1, allow_endpoints=[], deny_endpoints=[])

    orm = scope.to_orm()
    assert orm.id == 1

    back = Scope.from_orm(orm)
    assert back.id == 1
    assert back.allow_endpoints == []
    assert back.deny_endpoints == []
