# Vex the web security toolkit that lives in your termianl

## Description
Vex is a security toolkit like Burp, Caido or Zap proxy that integrates all the main features in the terminal. It is keyboard driven tool that utilizes vim keybindings and enables security researchers to speed up their research.

## Structure
1. vex - client terminal app built with Textual

2. vex-cli - backend server that extends mitmproxy with the addon system adding database support for summaries and raw requests/responses, a scope system and a replay/intercept system with API endpoints and websockets to query/recieve the data and control it with commands

# TODO

## vex (client)

### General widgets

- [x] Implement custom footer
- [x] VexTextArea vim like status bar
- [ ] Add help screens

### History screen

- [x] Add a search bar
- [ ] Add copy helper
- [ ] Sorting for History table
- [x] Syntax highlighting for History table
- [x] Implement some sort of caching
- [ ] Improve responsivness
- [x] Add resizable columns

### Projects screen

- [x] Improve layout (add buttons, search bar)
- [ ] Sorting for Projects table
- [ ] Importing/backuping projects

### Intercept screen

- [ ] Implement Request/Response intercept tables
- [ ] Button to forward,drop
- [ ] Wire with the global intercept button

### Replay screen

- [ ] Add request/response text areas
- [ ] Allow requests to be forwarded to replay screen
- [ ] Add numerical buttons for each replay we send

### Scope screen

- [ ] Improve layout
- [ ] Add the ability to add/remove/update scopes
- [ ] Wire with global scope dropdown menu

## vex-cli (server)

### Scope functionality
- [x] implement scope functionality
- [x] ability to add simple scopes (domains, ips, ipv6)
- [x] ability to toggle scopes on and off
- [ ] add regex support and wildcard domains (*.google.com)

### Replay functionality
- [ ] add the ability to replay a request
- [ ] save the new replays into a database and track changes

### Intercept functionality
- [ ] implement the ability to pause requests
- [ ] implement the ability for any client to forward/drop
- [ ] implement the ability to pause recieved responses

### Improve performance
- [ ] deleting the cached responses from mitmproxy
- [ ] better database optimizations (indexing)

### improve API
- [x] improve naming API scheme
- [ ] add functionality (delete all,...)


# Complex problems

## Raw HTTP request/response handling & display analysis

### Capture layer (`vex-cli/flow_helper.py`)

`flow_to_raw_request` and `flow_to_raw_response` construct the raw HTTP message that is
stored in the database and later displayed to the user. The message must be byte-accurate
so it can be replayed (like in Burp/Caido).

**Fixed (2026-06-02):** Previously these functions used `get_text()` + `.encode("utf-8")` to
build the body, which caused a lossy decode→re-encode roundtrip and crashed on binary
content (images, PDFs, etc.). Now they split construction into two parts:

```
header_bytes = "".join(header_lines).encode("utf-8")   # text headers → UTF-8 bytes
body_bytes   = flow.request.get_content() or b""       # raw decompressed body bytes
return header_bytes + body_bytes                       # valid raw HTTP message
```

`get_content()` returns the decompressed body bytes (handles `Content-Encoding: gzip`
transparently), matching what Burp/Caido display in their Raw tabs. For wire-accurate
replay the headers are preserved as-is, so `Content-Encoding` remains in the header.

`extract_http_title` uses `get_text(strict=False)` so binary responses return `None`
instead of raising `UnicodeDecodeError`.

### Display layer (`vex_client/history/screen.py`)

Currently the client always does `raw.data.decode("utf-8")` regardless of MIME type,
which will crash when rendering binary responses (images, PDFs, executables).

There is zero MIME-type-aware rendering — the `mime` field from `FlowSummary` is
populated but never consulted for display decisions.

**To fix (future):**
- At minimum, use `data.decode("utf-8", errors="replace")` to avoid crashes
- Ideally, check the MIME type and render accordingly:
  - `text/*`, `application/json`, `application/xml` → display as text with syntax highlighting
  - `image/*`, `application/pdf`, binary types → show a hex dump or just the MIME/Content-Type label
- The `VexTextArea` widget already has tree-sitter HTTP syntax highlighting for the
  header portion; body rendering needs to be MIME-aware



