# Vex the web security toolkit that lives in your termianl

## Description
Vex is a security toolkit like Burp, Caido or Zap proxy that integrates all the main features in the terminal.
It is keyboard driven tool that utilizes vim keybindings and enables security researchers to speed up their research.
This tool is still under development and many things may change.

## Structure
1. vex - client Terminal app built with Textual

2. vex-cli - backend component that builds uppon mitmproxy and adds API endpoints and websockets to it

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
- [ ] Implement some sort of caching
- [ ] Improve responsivness
- [ ] Add resizable columns

### Projects screen

- [ ] Improve layout (add buttons, search bar)
- [ ] Sorting for Projects table

### Intercept screen

- [ ] Implement Request/Response intercept tables
- [ ] Button to forward,drop
- [ ] Wire with the global intercept button

### Replay screen

### Scope screen

## vex-cli

### Scope functionality
- [ ] implement scope functionality
- [ ] ability to add simple scopes (domains, ips, ipv6)
- [ ] ability to toggle scopes on and off
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



