# Vex the web security toolkit that lives in your termianl

## Description
Vex is a security toolkit like Burp, Caido or Zap proxy that integrates all the main features in the terminal. It is keyboard driven tool that utilizes vim keybindings and enables security researchers to speed up their research. This tool is still under development and many things may change.

## Structure
1. vex - client terminal app built with Textual

2. vex-cli - backend server that extends mitmproxy with the addon system adding database support for summaries and raw requests/responses, a scope system and a replay/intercept system with API endpoints and websockets to query/recieve the data and control it with commands

# TODO

## vex (client)

### General widgets

- [ ] Implement custom footer
- [ ] VexTextArea vim like status bar
- [ ] Add help screens

### History screen

- [ ] Add a search bar
- [ ] Add copy helper
- [ ] Sorting for History table
- [x] Syntax highlighting for History table
- [x] Implement some sort of caching
- [ ] Improve responsivness
- [ ] Add resizable columns

### Projects screen

- [ ] Improve layout (add buttons, search bar)
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
- [ ] improve naming API scheme
- [ ] add functionality (delete all,...)



