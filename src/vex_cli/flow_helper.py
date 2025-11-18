import re
import os

from mitmproxy import http
from urllib.parse import urlparse
from typing import Optional

def uses_tls(flow: http.HTTPFlow) -> bool:
    return True if flow.request.scheme == "https" else False

def extract_url_path(flow: http.HTTPFlow) -> str:
    return "".join(urlparse(flow.request.pretty_url)[2])

def extract_extension(flow: http.HTTPFlow) -> str | None:
    return os.path.splitext(urlparse(flow.request.pretty_url).path)[1] or None

def extract_mime(flow: http.HTTPFlow) -> str | None:
    if flow.response is None:
        return None
    content_type = flow.response.headers.get("Content-Type")
    if content_type:
        return content_type.split(";")[0]
    return None

def request_total_size(flow: http.HTTPFlow) -> int:
    raw_req = flow_to_raw_request(flow)
    return len(raw_req) if raw_req is not None else 0

def response_total_size(flow: http.HTTPFlow) -> int:
    raw_res = flow_to_raw_response(flow)
    return len(raw_res) if raw_res is not None else 0

def extract_http_title(flow: http.HTTPFlow) -> str | None:
    match = re.search(r"<title>(.*?)</title>",
                      flow.response.get_text(), re.IGNORECASE | re.DOTALL) # type: ignore
    if match:
       return match.group(1).strip()
    return None

def extract_query(flow: http.HTTPFlow) -> str | None:
    query = urlparse(flow.request.pretty_url).query
    return query if query is not None else None

def has_cookies(flow: http.HTTPFlow) -> bool:
    if flow.response is None:
        return False
    return bool(flow.response.cookies)

def calculate_response_time_ms(flow: http.HTTPFlow) -> int:
    return int((flow.response.timestamp_start - flow.request.timestamp_end) * 1000) # type: ignore

def flow_to_raw_request(flow: http.HTTPFlow) -> bytes:
    lines = ""
    
    # Request line format: 
    # METHOD /path HTTP/1.1
    parsed = urlparse(flow.request.url)
    path_and_query = parsed.path or "/"
    if parsed.query:
        path_and_query += f"?{parsed.query}"
    
    http_version = flow.request.http_version
    request_line = f"{flow.request.method} {path_and_query} {http_version}\r\n"
    lines += request_line
    
    # Headers format
    # Header-name: Header-value\r\n
    for key, value in flow.request.headers.items():
        lines += f"{key}: {value}\r\n"
        
    # CRLF before body
    lines += "\r\n"
    
    # Body
    if flow.request.get_text():
        lines += (flow.request.get_text() or "")
    
    raw_bytes = lines.encode("utf-8")
    
    return raw_bytes


def flow_to_raw_response(flow: http.HTTPFlow) -> Optional[bytes]:
    if not flow.response:
        return None
    
    lines = ""
    
    # Status line format
    # HTTP/1.1 200 OK\r\n
    http_version = flow.response.http_version
    status_text = flow.response.reason or get_status_text(flow.response.status_code)
    status_line = f"{http_version} {flow.response.status_code} {status_text}\r\n"
    lines += status_line
    
    # Headers format
    # Header-name: Header-value\r\n
    for name, value in flow.response.headers.items():
        lines +=f"{name}: {value}\r\n"
        
    # CRLF before body
    lines += "\r\n"
    
    # Body
    if flow.response.get_text():
        lines += (flow.response.get_text() or "")

    # Combine headers + body
    raw_bytes = lines.encode("utf-8")
    
    return raw_bytes


def get_status_text(status_code: int) -> str:
    """Get standard HTTP status text"""
    status_texts = {
        100: "Continue", 101: "Switching Protocols",
        200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
        301: "Moved Permanently", 302: "Found", 304: "Not Modified",
        400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 
        404: "Not Found", 405: "Method Not Allowed",
        500: "Internal Server Error", 502: "Bad Gateway", 
        503: "Service Unavailable", 504: "Gateway Timeout"
    }
    return status_texts.get(status_code, "Unknown")

