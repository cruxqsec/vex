from mitmproxy.test import tflow, tutils
from mitmproxy import http
from urllib.parse import urlparse

# Add project root to path
from pathlib import Path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flow_helper import request_total_size, response_total_size,extract_query


req = tutils.treq(
    host="example.com",
    scheme="http",
    method="GET",
    path="/path/to/content.php?query=value-of-query",
    content=b"",
    timestamp_end=50,
)

html = b"""<!doctype html>
<html lang="en">
<head>
    <title>Example Domain</title>
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
    (b"Content-Type", b"text/html"),
    (b"Vary", b"Accept-Encoding"),
    (b"Set-Cookie", b"test=random-test-cookie"),
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

print(flow.response.cookies)

