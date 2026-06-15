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
- [x] VexTextArea vim normal/visual mode (read only first)
- [ ] VexTextArea vim insert mode
- [ ] VexTextArea search mode
- [ ] Add help screens (per screen and per widget)
- [ ] Muted buttons for functionality that can't be used at the moment

### History screen

- [x] Add a search bar
- [x] Add copy helper (command palette like)
- [ ] Search bar with basic query capabilities + custom filed queries
- [x] When scope set we apply scope rules
- [x] Sorting for all columns of History table
- [x] Syntax highlighting for History table
- [x] Implement some sort of caching
- [x] Improve responsivness
- [x] Add resizable columns
- [x] Delete one and all summaries

### Projects screen

- [x] Improve layout (add buttons, search bar)
- [x] Sorting for all columns of Projects table
- [ ] Update project time when selected
- [ ] Delete all projects
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

- [x] Redesign layout
- [x] Add the ability to add/save(update)/duplicate/delete scopes
- [x] Wire with global scope select menu


### Proxy screen

- [ ] Implement a continual check if instance is available

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
- [x] add functionality (delete all, count for statistic...)


