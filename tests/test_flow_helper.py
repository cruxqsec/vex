import pytest
from mitmproxy import http
from mitmproxy.test import tflow, tutils

from vex_cli.flow_helper import (
    calculate_response_time_ms,
    extract_extension,
    extract_http_title,
    extract_mime,
    extract_query,
    extract_url_path,
    flow_to_raw_request,
    flow_to_raw_response,
    get_status_text,
    has_cookies,
    request_total_size,
    response_total_size,
    uses_tls,
)


# --- Fixtures for Mock HTTPFlow ---
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


@pytest.fixture
def mock_flow_no_resp() -> http.HTTPFlow:
    req = tutils.treq(
        host="example.com",
        scheme="https",
        method="GET",
        path="/path/to/content.php?query=test&query2=test2",
        content=b"",
        timestamp_end=50,
    )

    flow = tflow.tflow(req=req, resp=False)

    return flow


def test_uses_tls(mock_flow: http.HTTPFlow):
    assert not uses_tls(mock_flow)


def test_extract_url_path(mock_flow: http.HTTPFlow):
    assert extract_url_path(mock_flow) == "/path/to/content.php"


def test_extract_extension_with_extension(mock_flow):
    assert extract_extension(mock_flow) == ".php"


def test_extract_mime_with_charset(mock_flow: http.HTTPFlow):
    assert extract_mime(mock_flow) == "text/html"


def test_extract_mime_no_content_type(mock_flow: http.HTTPFlow):
    mock_flow.response.headers = {}  # type: ignore
    assert extract_mime(mock_flow) is None


def test_extract_mime_no_response(mock_flow_no_resp: http.HTTPFlow):
    assert extract_mime(mock_flow_no_resp) is None


def test_request_total_size(mock_flow: http.HTTPFlow):
    assert request_total_size(mock_flow) == 96


def test_response_total_size(mock_flow: http.HTTPFlow):
    assert response_total_size(mock_flow) == 530


def test_response_total_size_no_response(mock_flow: http.HTTPFlow):
    mock_flow.response = None
    assert response_total_size(mock_flow) == 0


def test_extract_http_title_found(mock_flow: http.HTTPFlow):
    assert extract_http_title(mock_flow) == "Example title"


def test_extract_http_title_no_res(mock_flow_no_resp: http.HTTPFlow):
    assert extract_http_title(mock_flow_no_resp) is None


def test_extract_http_title_no_title(mock_flow: http.HTTPFlow):
    no_title_html = b"""<!doctype html>
    <html lang="en">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <body>
        <div>
            <h1>Example Domain</h1>
            <p><a href="https://iana.org/domains/example">Learn more</a>
        </div>
    </body>
    </html>"""

    mock_flow.response.content = no_title_html  # type: ignore
    assert extract_http_title(mock_flow) is None


def test_extract_query_found(mock_flow: http.HTTPFlow):
    assert extract_query(mock_flow) == "query=test&query2=test2"


def test_has_cookies_true(mock_flow: http.HTTPFlow):
    assert has_cookies(mock_flow)


def test_has_cookies_no_res(mock_flow_no_resp: http.HTTPFlow):
    assert not has_cookies(mock_flow_no_resp)


def test_calculate_response_time_ms(mock_flow: http.HTTPFlow):
    assert calculate_response_time_ms(mock_flow) == 50000


def test_calculate_response_time_ms_no_res(mock_flow_no_resp: http.HTTPFlow):
    assert calculate_response_time_ms(mock_flow_no_resp) == 0


def test_calculate_response_time_ms_no_end_time(mock_flow: http.HTTPFlow):
    mock_flow.request.timestamp_end = None
    assert calculate_response_time_ms(mock_flow) == 0


def test_get_status_text_known_code(mock_flow: http.HTTPFlow):
    assert get_status_text(200) == "OK"
    assert get_status_text(404) == "Not Found"
    assert get_status_text(500) == "Internal Server Error"


def test_get_status_text_unknown_code(mock_flow: http.HTTPFlow):
    assert get_status_text(999) == "Unknown"


def test_flow_to_raw_req(mock_flow: http.HTTPFlow):
    result = (
        b"GET /path/to/content.php?query=test&query2=test2 HTTP/1.1\r\n"
        b"header: qvalue\r\n"
        b"content-length: 7\r\n\r\n"
    )

    assert flow_to_raw_request(mock_flow) == result


def test_flow_to_raw_res(mock_flow: http.HTTPFlow):
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

    result = (
        b"HTTP/1.1 200 OK\r\n"
        b"Accept-Ranges: bytes\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"Vary: Accept-Encoding\r\n"
        b"Set-Cookie: test_token=random-test-cookie\r\n"
        b"Content-Length: 338\r\n"
        b"Connection: keep-alive\r\n\r\n" + html
    )
    raw_res = flow_to_raw_response(mock_flow)

    assert raw_res == result
