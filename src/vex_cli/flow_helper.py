import os
import re
from urllib.parse import urlparse

from mitmproxy import http


def uses_tls(flow: http.HTTPFlow) -> bool:
    return flow.request.scheme == "https"


def extract_url_path(flow: http.HTTPFlow) -> str:
    return urlparse(flow.request.pretty_url).path


def extract_extension(flow: http.HTTPFlow) -> str | None:
    return os.path.splitext(urlparse(flow.request.pretty_url).path)[1] or None


def extract_mime(flow: http.HTTPFlow) -> str | None:
    if flow.response is None:
        return None
    content_type = flow.response.headers.get("Content-Type")
    if content_type:
        return content_type.split(";")[0]
    return None


def extract_http_title(flow: http.HTTPFlow) -> str | None:
    if flow.response is None:
        return None

    match = re.search(
        rb"<title>(.*?)</title>",
        flow.response.content or b"",
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1).decode("latin-1", errors="ignore").strip()
    return None


def extract_query(flow: http.HTTPFlow) -> str | None:
    query = urlparse(flow.request.pretty_url).query
    return query or None


def extract_cookies(flow: http.HTTPFlow) -> str:
    if flow.response is None:
        return ""
    if flow.response.cookies:
        return "; ".join(f"{k}={v[0]}" for k, v in flow.response.cookies.items())
    return ""


def has_cookies(flow: http.HTTPFlow) -> bool:
    if flow.response is None:
        return False
    return bool(flow.response.cookies)


def calculate_response_time_ms(flow: http.HTTPFlow) -> int:
    if flow.response is None or flow.request.timestamp_end is None:
        return 0
    return int((flow.response.timestamp_start - flow.request.timestamp_end) * 1000)


def flow_to_raw_request(flow: http.HTTPFlow) -> bytes:
    parsed = urlparse(flow.request.url)
    path_and_query = parsed.path or "/"
    if parsed.query:
        path_and_query += f"?{parsed.query}"

    # Request line format:
    # METHOD /path HTTP/1.1
    request_line = (
        f"{flow.request.method} {path_and_query} {flow.request.http_version}\r\n"
    )

    # Strip encoding artifacts from request headers (rare but possible)
    headers = flow.request.headers.copy()
    headers.pop("Content-Encoding", None)
    headers.pop("Transfer-Encoding", None)

    body = flow.request.get_content(strict=False) or b""

    # Recalculate to have a more correct Content-Length
    if "Content-Length" in headers:
        headers["Content-Length"] = str(len(body))

    # Headers format
    # Header-name: Header-value\r\n
    header_lines = "".join(f"{header}: {value}\r\n" for header, value in headers.items())
    header_bytes = (request_line + header_lines + "\r\n").encode("latin-1")

    return header_bytes + body


def flow_to_raw_response(flow: http.HTTPFlow) -> bytes | None:
    if not flow.response:
        return None

    # Status line format
    # HTTP/1.1 200 OK\r\n
    http_version = flow.response.http_version
    status_text = flow.response.reason or get_status_text(flow.response.status_code)
    status_line = f"{http_version} {flow.response.status_code} {status_text}\r\n"

    # Strip encoding artifacts mitmproxy has already decoded
    headers = flow.response.headers.copy()
    headers.pop("Content-Encoding", None)
    headers.pop("Transfer-Encoding", None)

    # Use strict=False to gracefully handle encoding mismatches
    body = flow.response.get_content(strict=False) or b""

    # Recalculate to have a more correct Content-Length
    if "Content-Length" in headers:
        headers["Content-Length"] = str(len(body))

    # Headers format
    # Header-name: Header-value\r\n
    header_lines = "".join(f"{header}: {value}\r\n" for header, value in headers.items())
    header_bytes = (status_line + header_lines + "\r\n").encode("latin-1")

    return header_bytes + body


def get_status_text(status_code: int) -> str:
    """Get standard HTTP status text"""
    status_texts = {
        100: "Continue",
        101: "Switching Protocols",
        200: "OK",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
    }
    return status_texts.get(status_code, "Unknown")
