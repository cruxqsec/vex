from mitmproxy import http

from vex_cli.flow_helper import (
    calculate_response_time_ms,
    extract_cookies,
    extract_extension,
    extract_http_title,
    extract_mime,
    extract_query,
    extract_url_path,
    flow_to_raw_request,
    flow_to_raw_response,
    get_status_text,
    has_cookies,
    uses_tls,
)


def test_uses_tls(req_res_flow: http.HTTPFlow):
    assert uses_tls(req_res_flow)


def test_uses_tls_no_tls(req_res_flow: http.HTTPFlow):
    req_res_flow.request.scheme = "http"
    assert not uses_tls(req_res_flow)


def test_extract_url_path(req_res_flow: http.HTTPFlow):
    assert extract_url_path(req_res_flow) == "/path/to/content.php"


def test_extract_extension(req_res_flow: http.HTTPFlow):
    assert extract_extension(req_res_flow) == ".php"


def test_extract_extension_no_extension(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/path/to/index"
    assert extract_extension(req_res_flow) is None


def test_extract_extension_dotfile(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/.gitignore"
    assert extract_extension(req_res_flow) is None


def test_extract_extension_dot_at_end(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/file."
    assert extract_extension(req_res_flow) == "."


def test_extract_extension_multiple_dots(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/archive.tar.gz"
    assert extract_extension(req_res_flow) == ".gz"


def test_extract_extension_query_string_ignored(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/file.php?x=1"
    assert extract_extension(req_res_flow) == ".php"


def test_extract_mime_with_charset(req_res_flow: http.HTTPFlow):
    assert extract_mime(req_res_flow) == "text/html"


def test_extract_mime_no_content_type(req_res_flow: http.HTTPFlow):
    req_res_flow.response.headers = {}  # type: ignore
    assert extract_mime(req_res_flow) is None


def test_extract_mime_no_response(req_no_resp_flow: http.HTTPFlow):
    assert extract_mime(req_no_resp_flow) is None


def test_extract_http_title_found(req_res_flow: http.HTTPFlow):
    assert extract_http_title(req_res_flow) == "Example title"


def test_extract_http_title_no_res(req_no_resp_flow: http.HTTPFlow):
    assert extract_http_title(req_no_resp_flow) is None


def test_extract_http_title_no_title(req_res_flow: http.HTTPFlow):
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

    req_res_flow.response.content = no_title_html  # type: ignore
    assert extract_http_title(req_res_flow) is None


def test_extract_http_title_binary_response(binary_flow: http.HTTPFlow):
    assert extract_http_title(binary_flow) is None


def test_extract_http_title_binary_response_safe(binary_flow: http.HTTPFlow):
    # no <title> in PNG binary
    title = extract_http_title(binary_flow)
    assert title is None


def test_extract_query_found(req_res_flow: http.HTTPFlow):
    assert extract_query(req_res_flow) == "query=test&query2=test2"


def test_extract_query_empty_returns_none(req_res_flow: http.HTTPFlow):
    req_res_flow.request.path = "/path/no/query"
    assert extract_query(req_res_flow) is None


def test_has_cookies(req_res_flow: http.HTTPFlow):
    assert has_cookies(req_res_flow)


def test_has_no_cookies(req_res_flow: http.HTTPFlow):
    req_res_flow.response.headers.pop(b"Set-Cookie")  # type: ignore
    assert not has_cookies(req_res_flow)


def test_has_cookies_no_res(req_no_resp_flow: http.HTTPFlow):
    assert not has_cookies(req_no_resp_flow)


def test_extract_cookies(req_res_flow: http.HTTPFlow):
    assert extract_cookies(req_res_flow) == "test_token=random-test-cookie"


def test_extract_cookies_no_cookies(req_res_flow: http.HTTPFlow):
    req_res_flow.response.headers.pop(b"Set-Cookie")  # type: ignore
    assert extract_cookies(req_res_flow) == ""


def test_calculate_response_time_ms(req_res_flow: http.HTTPFlow):
    assert calculate_response_time_ms(req_res_flow) == 50000


def test_calculate_response_time_ms_no_res(req_no_resp_flow: http.HTTPFlow):
    assert calculate_response_time_ms(req_no_resp_flow) == 0


def test_calculate_response_time_ms_no_end_time(req_res_flow: http.HTTPFlow):
    req_res_flow.request.timestamp_end = None
    assert calculate_response_time_ms(req_res_flow) == 0


def test_get_status_text_unknown_code(req_res_flow: http.HTTPFlow):
    assert get_status_text(999) == "Unknown"


def test_flow_to_raw_req(req_res_flow: http.HTTPFlow):
    result = (
        b"GET /path/to/content.php?query=test&query2=test2 HTTP/1.1\r\n"
        b"header: qvalue\r\n"
        b"content-length: 0\r\n\r\n"
    )

    assert flow_to_raw_request(req_res_flow) == result


def test_flow_to_raw_res(req_res_flow: http.HTTPFlow):
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
    raw_res = flow_to_raw_response(req_res_flow)

    assert raw_res == result


# Binary content tests


def test_flow_to_raw_response_binary_body(binary_flow: http.HTTPFlow):
    raw = flow_to_raw_response(binary_flow)
    assert raw is not None
    assert b"HTTP/1.1 200 OK\r\n" in raw
    assert b"Content-Type: image/png\r\n" in raw
    assert b"\x89PNG" in raw


def test_flow_to_raw_request_binary_body(binary_flow: http.HTTPFlow):
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    binary_flow.request.content = png_bytes
    raw = flow_to_raw_request(binary_flow)
    assert b"GET /img.png HTTP/1.1\r\n" in raw
    assert b"\x89PNG" in raw


def test_flow_to_raw_response_strips_content_encoding(req_res_flow: http.HTTPFlow):
    """Verify Content-Encoding and Transfer-Encoding are stripped from response."""
    raw = flow_to_raw_response(req_res_flow)

    assert raw is not None
    assert b"Content-Encoding" not in raw
    assert b"Transfer-Encoding" not in raw


def test_flow_to_raw_response_binary_with_non_ascii_headers(
    req_res_flow: http.HTTPFlow,
):
    """Verify latin-1 encoding handles non-ASCII header values correctly."""
    # UTF-8 for "café" - tests latin-1 encoding
    req_res_flow.response.headers.add(b"X-Custom", b"caf\xc3\xa9")  # type: ignore
    raw = flow_to_raw_response(req_res_flow)

    assert raw is not None
    # mitmproxy decodes UTF-8 bytes to "café" string (U+00E9), we encode to latin-1 (0xE9)
    assert b"X-Custom: caf\xe9\r\n" in raw
